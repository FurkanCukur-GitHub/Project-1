# process_operations/video_processor.py
import cv2
import threading
import time
import numpy as np
import torch
import logging
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import QTimer
from object_tracking.object_tracker import ObjectTracker
from queue import Queue, Full, Empty

class FPSCounter:
    def __init__(self):
        self.last_time = time.time()

    def get_fps(self):
        now = time.time()
        fps = 1.0 / (now - self.last_time) if now != self.last_time else 0
        self.last_time = now
        return int(fps)


class VideoProcessor:
    def __init__(self, app, display_width, display_height):
        self.app = app
        self.object_detector = app.object_detector
        self.object_tracker = ObjectTracker()

        # Kuyruklar daha sonra start_processing_on_selection'da frame sayısına göre yeniden oluşturulacak
        self.frames_queue = None
        self.processed_frames_queue = None

        self.current_tracked_objects = []
        self.frame = None
        self.stop_processing = False

        self.batch_size = 4

        self.fps_counter = FPSCounter()

        # Stream A: Veri kopyalama ve preprocess
        self.stream_a = torch.cuda.Stream()
        # Stream B: Model inference
        self.stream_b = torch.cuda.Stream()
        # Stream C: CPU'ya al / parse
        self.stream_c = torch.cuda.Stream()


        # input tensor’ı sadece bir kere oluştur (optimizasyon için)
        self.input_h = display_height
        self.input_w = display_width
        self.input_tensor = torch.empty(
            (self.batch_size, 3, self.input_h, self.input_w),
            device=self.object_detector.human_detector.device,
            dtype=torch.half
        )


        self.frame_reading_thread = None
        self.inference_thread = None

        # GUI timer (Qt ana-thread’inde çalışır)
        self.timer = QTimer()
        self.timer.timeout.connect(self.play_video)

    # ------------------------------------------------------------------ #
    # 1 – Başlat / durdur
    # ------------------------------------------------------------------ #
    def start_processing_on_selection(self, video_path, display_width, display_height):
        self.stop_processing_frames()
        self.stop_processing = False

        # --- Video toplam frame sayısını al ve kuyrukları yeniden oluştur ---
        cap_info = cv2.VideoCapture(video_path, cv2.CAP_FFMPEG)
        total_frames = int(cap_info.get(cv2.CAP_PROP_FRAME_COUNT))
        cap_info.release()
        self.frames_queue = Queue(maxsize=total_frames)
        self.processed_frames_queue = Queue(maxsize=total_frames)
        # batch_size'ı da videonun uzunluğuna göre ayarla
        self.batch_size = min(self.batch_size, total_frames)

        # Frame okuma
        self.frame_reading_thread = threading.Thread(
            target=self.read_frames,
            args=(video_path, display_width, display_height),
            daemon=True,
            name="FrameReadingThread"
        )

        # Inference + tracking
        self.inference_thread = threading.Thread(
            target=self.process_frames,
            daemon=True,
            name="InferenceThread"
        )

        self.frame_reading_thread.start()
        self.inference_thread.start()

    def stop_processing_frames(self):
        self.stop_processing = True

        for thread in [self.frame_reading_thread, self.inference_thread]:
            if thread is not None and thread.is_alive():
                thread.join(timeout=5)

        # Kuyrukları temizle (bloklanmayı önler)
        if self.frames_queue:
            with self.frames_queue.mutex:
                self.frames_queue.queue.clear()
        if self.processed_frames_queue:
            with self.processed_frames_queue.mutex:
                self.processed_frames_queue.queue.clear()

    # ------------------------------------------------------------------ #
    # 2 – Frame okuma
    # ------------------------------------------------------------------ #
    def read_frames(self, video_path, display_width, display_height):
        cap = cv2.VideoCapture(video_path, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)
        frame_number = 0

        while not self.stop_processing:
            ret, frame = cap.read()
            if not ret:
                break

            frame = cv2.resize(frame, (display_width, display_height))
            data = {"frame_number": frame_number, "frame": frame}

            while not self.stop_processing:
                try:
                    self.frames_queue.put(data, timeout=0.05)
                    break
                except Full:
                    time.sleep(0.005)

            frame_number += 1

        cap.release()

    # ------------------------------------------------------------------ #
    # 3 – Inference + tracking
    # ------------------------------------------------------------------ #
    def process_frames(self):
        batch = []
        last_time = time.time()

        while not self.stop_processing:
            try:
                data = self.frames_queue.get(timeout=0.05)
                batch.append(data)

                if len(batch) >= self.batch_size:
                    print(f"[DEBUG] Processing full batch of {len(batch)} frames.")
                    self.process_batch(batch)
                    batch = []
                    last_time = time.time()

            except Empty:
                # 0.2 saniye içinde yeni frame gelmediyse kalan batch'i işle
                if batch and (time.time() - last_time > 0.2):
                    print(f"[DEBUG] Processing partial batch of {len(batch)} frames (timeout).")
                    self.process_batch(batch)
                    batch = []
                    last_time = time.time()

        if batch:
            print(f"[DEBUG] Processing remaining batch of {len(batch)} frames (end of stream).")
            self.process_batch(batch)


    def process_batch(self, frames_batch):
        valid = [d for d in frames_batch if isinstance(d["frame"], np.ndarray)]
        if not valid:
            return

        batch_len = len(valid)

        # --- STREAM A: Normalize ve kopyala --- #
        with torch.cuda.stream(self.stream_a):
            frames = [
                cv2.cvtColor(d["frame"], cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
                for d in valid
            ]
            frames_np = np.stack(frames).transpose(0, 3, 1, 2)  # NHWC → NCHW
            temp_tensor = torch.from_numpy(frames_np).to(dtype=torch.half, non_blocking=True)
            self.input_tensor[:batch_len].copy_(temp_tensor.to(self.input_tensor.device))

        # --- STREAM B: Model inference --- #
        with torch.cuda.stream(self.stream_b):
            with torch.inference_mode():
                input_tensor = self.input_tensor[:batch_len]
                print(f"[DEBUG] Tensor shape to model: {input_tensor.shape}")
                # DOĞRUDAN nn.Module forward fonksiyonu çağırıyoruz
                human_res = self.object_detector.human_detector.model.predict(input_tensor, stream=False)
                vehicle_res = self.object_detector.vehicle_detector.model.predict(input_tensor, stream=False)
                
        # --- STREAM C: Parsing işlemi --- #
        with torch.cuda.stream(self.stream_c):
            detections_batch = []
            for hr, vr in zip(human_res, vehicle_res):
                dets = []
                dets.extend(self.object_detector._parse(hr, self.object_detector.human_names, threshold=0.1))
                dets.extend(self.object_detector._parse(vr, self.object_detector.vehicle_names, threshold=0.1))
                detections_batch.append(dets)


        # --- GPU işlemleri tamamlandığından emin ol --- #
        torch.cuda.synchronize()

        # --- Takip ve kuyruk işlemleri --- #
        for data, detections in zip(valid, detections_batch):
            frame = data["frame"]
            frame_number = data["frame_number"]
            tracked_objects = self.object_tracker.update_tracks(detections, frame)
            

            processed = {
                "frame_number": frame_number,
                "frame": frame,
                "tracked_objects": tracked_objects
            }

            while not self.stop_processing:
                try:
                    self.processed_frames_queue.put(processed, timeout=0.05)
                    break
                except Full:
                    time.sleep(0.005)

        # Bu batch sonunda bölgelere göre statüleri güncelle
        if hasattr(self.app, "assign_status_based_on_zones"):
            self.app.assign_status_based_on_zones()





    # ------------------------------------------------------------------ #
    # 4 – GUI tarafı (Qt ana thread)
    # ------------------------------------------------------------------ #
    def play_video(self):
        if self.app.cap is None or not self.app.playing:
            return
        try:
            processed = self.processed_frames_queue.get_nowait()
        except Empty:
            delay = int(1000 / max(1, self.app.fps))
            self.timer.start(delay)
            return

        self.app.current_frame = processed["frame_number"]
        self.frame = processed["frame"]
        self.current_tracked_objects = processed["tracked_objects"]

        display_frame = self.draw_boxes(self.frame.copy(), self.current_tracked_objects)

        fps = self.fps_counter.get_fps()
        self.app.video_info_label.setText(
            f"Video Name: {self.app.video_path.split('/')[-1]} | "
            f"Resolution: {self.app.display_width}x{self.app.display_height} | FPS: {fps}"
        )

        rgb = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        bytes_per_line = ch * w
        q_img = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(q_img)
        self.app.video_label.setPixmap(pixmap)

        delay = int(1000 / max(1, self.app.fps))
        self.timer.start(delay)

    # ------------------------------------------------------------------ #
    # 5 – Box çizimi (değişmedi)
    # ------------------------------------------------------------------ #
    def draw_boxes(self, frame, tracked_objects):
        for obj in tracked_objects:
            tid = str(obj["track_id"])
            x1, y1, x2, y2 = map(int, obj["bbox"])

            status_info = self.app.object_statuses.get(
                tid, {"status": "Unknown", "selected": False, "threat_level": None}
            )
            status = status_info["status"]
            selected = status_info["selected"]
            threat = status_info["threat_level"]

            if selected:
                color = (0, 165, 255)
            elif status == "friend":
                color = (0, 255, 0)
            elif status == "foe":
                color = (0, 0, 255)
            else:
                color = (175, 175, 0)

            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 1)

            threat_txt = f"Threat:{int(threat)}" if threat is not None else "Threat:N/A"
            lines = [threat_txt, f"{obj['cls']}", f"ID:{tid}"]
            box_w = x2 - x1
            line_h = 20

            for i, txt in enumerate(lines):
                size = cv2.getTextSize(txt, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
                tx = x1 + (box_w - size[0]) // 2
                ty = y1 - 10 - i * line_h
                if ty < 10:
                    ty = y1 + 10 + i * line_h
                cv2.putText(frame, txt, (tx, ty),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

        # Bölge çizimleri (Friendly ve Enemy)
        for x1, y1, x2, y2 in self.app.friendly_zones:
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

        for x1, y1, x2, y2 in self.app.enemy_zones:
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)

        return frame

    # -------------------------------------------------------------- #
    # 6 – GUI’den elle yeniden çizim (seçim / statü güncellemesi vb.)
    # -------------------------------------------------------------- #
    def refresh_video_display(self):
        if self.frame is None:
            return

        display_frame = self.draw_boxes(self.frame.copy(), self.current_tracked_objects)

        rgb = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        bytes_per_line = ch * w
        q_img = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(q_img)
        self.app.video_label.setPixmap(pixmap)

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

from project_utils.config import BATCH_SIZE


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

        self.frames_queue = None
        self.processed_frames_queue = None

        self.current_tracked_objects = []
        self.frame = None
        self.stop_processing = False
        self.batch_size = BATCH_SIZE

        self.fps_counter = FPSCounter()

        # CUDA stream’ler
        self.stream_a = torch.cuda.Stream()
        self.stream_b = torch.cuda.Stream()
        self.stream_c = torch.cuda.Stream()

        self.input_h = display_height
        self.input_w = display_width
        self.input_tensor = torch.empty(
            (self.batch_size, 3, self.input_h, self.input_w),
            device=self.object_detector.human_detector.device,
            dtype=torch.half
        )

        self.frame_reading_thread = None
        self.inference_thread = None

        # ---<EKLENDİ>---  Başlangıç nesne filtresi
        self.initial_object_ids = set()
        self.initialization_done = False
        self.initialization_frame_count = 10          # ilk N kare
        # ---<EKLENDİ>---

        self.timer = QTimer()
        self.timer.timeout.connect(self.play_video)

    # ------------------------------------------------------------------ #
    # 1 – Başlat / durdur
    # ------------------------------------------------------------------ #
    def start_processing_on_selection(self, video_path, display_width, display_height):
        self.stop_processing_frames()
        self.stop_processing = False

        # ---<EKLENDİ>---  filtreyi sıfırla
        self.initial_object_ids.clear()
        self.initialization_done = False
        # ---<EKLENDİ>---

        cap_info = cv2.VideoCapture(video_path, cv2.CAP_FFMPEG)
        total_frames = int(cap_info.get(cv2.CAP_PROP_FRAME_COUNT))
        cap_info.release()

        self.frames_queue = Queue(maxsize=total_frames)
        self.processed_frames_queue = Queue(maxsize=total_frames)
        self.batch_size = min(self.batch_size, total_frames)

        self.frame_reading_thread = threading.Thread(
            target=self.read_frames,
            args=(video_path, display_width, display_height),
            daemon=True,
            name="FrameReadingThread"
        )

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
                    self.process_batch(batch)
                    batch = []
                    last_time = time.time()

            except Empty:
                if batch and (time.time() - last_time > 0.2):
                    self.process_batch(batch)
                    batch = []
                    last_time = time.time()

        if batch:
            self.process_batch(batch)

    def process_batch(self, frames_batch):
        valid = [d for d in frames_batch if isinstance(d["frame"], np.ndarray)]
        if not valid:
            return

        batch_len = len(valid)

        # --- STREAM A --- #
        with torch.cuda.stream(self.stream_a):
            frames = [
                cv2.cvtColor(d["frame"], cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
                for d in valid
            ]
            frames_np = np.stack(frames).transpose(0, 3, 1, 2)
            temp_tensor = torch.from_numpy(frames_np).to(dtype=torch.half, non_blocking=True)
            self.input_tensor[:batch_len].copy_(temp_tensor.to(self.input_tensor.device))

        # --- STREAM B --- #
        with torch.cuda.stream(self.stream_b):
            with torch.inference_mode():
                input_tensor = self.input_tensor[:batch_len]
                human_res = self.object_detector.human_detector.model.predict(
                    input_tensor, stream=False, verbose=False
                )
                vehicle_res = self.object_detector.vehicle_detector.model.predict(
                    input_tensor, stream=False, verbose=False
                )

        # --- STREAM C --- #
        with torch.cuda.stream(self.stream_c):
            detections_batch = []
            for hr, vr in zip(human_res, vehicle_res):
                dets = []
                dets.extend(self.object_detector._parse(hr, self.object_detector.human_names, 0.1))
                dets.extend(self.object_detector._parse(vr, self.object_detector.vehicle_names, 0.1))
                detections_batch.append(dets)

        torch.cuda.synchronize()

        # --- Takip & Filtre --- #
        for data, detections in zip(valid, detections_batch):
            frame = data["frame"]
            fnum = data["frame_number"]
            tracked_objects = self.object_tracker.update_tracks(detections, frame)

            # ---<EKLENDİ 1>---  İlk N karede görülen ID’leri topla
            if not self.initialization_done:
                for obj in tracked_objects:
                    self.initial_object_ids.add(obj["track_id"])
                if fnum + 1 >= self.initialization_frame_count:
                    self.initialization_done = True
            # ---<EKLENDİ 1>---

            # ---<EKLENDİ 2>---  Yeni nesneleri tamamen yok say
            if self.initialization_done:
                tracked_objects = [
                    obj for obj in tracked_objects
                    if obj["track_id"] in self.initial_object_ids
                ]
            # ---<EKLENDİ 2>---

            processed = {
                "frame_number": fnum,
                "frame": frame,
                "tracked_objects": tracked_objects
            }

            while not self.stop_processing:
                try:
                    self.processed_frames_queue.put(processed, timeout=0.05)
                    break
                except Full:
                    time.sleep(0.005)

    # ------------------------------------------------------------------ #
    # 4 – GUI (Qt ana thread)
    # ------------------------------------------------------------------ #
    def play_video(self):
        if self.app.cap is None or not self.app.playing:
            return
        try:
            processed = self.processed_frames_queue.get_nowait()
        except Empty:
            self.timer.start(int(1000 / max(1, self.app.fps)))
            return

        self.app.current_frame = processed["frame_number"]
        self.frame = processed["frame"]
        self.current_tracked_objects = processed["tracked_objects"]

        self.app.threat_assessment.perform_threat_assessment(self.app)

        display_frame = self.draw_boxes(self.frame.copy(), self.current_tracked_objects)

        rgb = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        q_img = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
        self.app.video_label.setPixmap(QPixmap.fromImage(q_img))

        self.timer.start(int(1000 / max(1, self.app.fps)))

    # ------------------------------------------------------------------ #
    # 5 – Box çizimi
    # ------------------------------------------------------------------ #
    def draw_boxes(self, frame, tracked_objects):
        for obj in tracked_objects:
            tid_num = obj["track_id"]

            # ---<EKLENDİ 3>---  Güvenlik: çizimden önce de filtrele
            if self.initialization_done and tid_num not in self.initial_object_ids:
                continue
            # ---<EKLENDİ 3>---

            tid = str(tid_num)
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
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        for x1, y1, x2, y2 in self.app.friendly_zones:
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        for x1, y1, x2, y2 in self.app.enemy_zones:
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)

        return frame

    # -------------------------------------------------------------- #
    # 6 – Elle yeniden çizim (GUI tetiklemeli)
    # -------------------------------------------------------------- #
    def refresh_video_display(self):
        if self.frame is None:
            return

        display_frame = self.draw_boxes(self.frame.copy(), self.current_tracked_objects)
        rgb = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        q_img = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
        self.app.video_label.setPixmap(QPixmap.fromImage(q_img))

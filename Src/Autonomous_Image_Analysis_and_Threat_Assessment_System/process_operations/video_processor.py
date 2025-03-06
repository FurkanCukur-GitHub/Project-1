# process_operations/video_processor.py
import cv2
import threading
import time
import numpy as np
import torch
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import QTimer
from object_tracking.object_tracker import ObjectTracker
from queue import Queue, Full, Empty
from utils.config import BATCH_SIZE

class FPSCounter:
    def __init__(self):
        self.last_time = time.time()

    def get_fps(self):
        current_time = time.time()
        fps = 1 / (current_time - self.last_time)
        self.last_time = current_time
        return int(fps)

class VideoProcessor:
    def __init__(self, app):
        self.app = app
        self.object_detector = app.object_detector
        self.object_tracker = ObjectTracker()
        
        self.frames_queue = Queue(maxsize=BATCH_SIZE * 2)
        self.processed_frames_queue = Queue(maxsize=BATCH_SIZE * 2)

        self.current_tracked_objects = []
        self.frame = None
        self.stop_processing = False
        self.batch_size = BATCH_SIZE

        self.fps_counter = FPSCounter()

        self.frame_reading_thread = None
        self.inference_thread = None
        self.display_thread = None

        self.timer = QTimer()
        self.timer.timeout.connect(self.play_video)

    def start_processing_on_selection(self, video_path, display_width, display_height):
        self.stop_processing_frames()

        self.stop_processing = False

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

        self.display_thread = threading.Thread(
            target=self.play_video,
            daemon=True,
            name="DisplayThread"
        )

        self.frame_reading_thread.start()
        self.inference_thread.start()
        self.display_thread.start()

    def read_frames(self, video_path, display_width, display_height):
        cap = cv2.VideoCapture(video_path)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)

        frame_number = 0

        while not self.stop_processing:
            ret, frame = cap.read()
            if not ret:
                break
            frame = cv2.resize(frame, (display_width, display_height))

            data = {
                'frame_number': frame_number,
                'frame': frame
            }

            while not self.stop_processing:
                try:
                    self.frames_queue.put(data, timeout=0.1)
                    break
                except Full:
                    time.sleep(0.01)
            
            frame_number += 1

        cap.release()

    def process_frames(self):
        batch = []
        while not self.stop_processing:
            try:
                data = self.frames_queue.get(timeout=0.1)
                batch.append(data)
                if len(batch) >= self.batch_size:
                    self.process_batch(batch)
                    batch = []
            except Empty:
                if batch:
                    self.process_batch(batch)
                    batch = []
                time.sleep(0.01)
        if batch:
            self.process_batch(batch)

    def process_batch(self, frames_batch):
        valid_frames = [item['frame'] for item in frames_batch if isinstance(item['frame'], np.ndarray)]
        valid_frame_numbers = [item['frame_number'] for item in frames_batch if isinstance(item['frame'], np.ndarray)]

        if not valid_frames:
            return

        with torch.inference_mode():
            detections_batch = self.object_detector.detect_objects(valid_frames)

        for data, detections in zip(frames_batch, detections_batch):
            frame_number = data['frame_number']
            frame = data['frame']

            tracked_objects = self.object_tracker.update_tracks(detections, frame)
            processed_data = {
                'frame_number': frame_number,
                'frame': frame,
                'tracked_objects': tracked_objects
            }

            while not self.stop_processing:
                try:
                    self.processed_frames_queue.put(processed_data, timeout=0.1)
                    break
                except Full:
                    time.sleep(0.01)

    def play_video(self):
        if self.app.cap is not None:
            if self.app.playing:
                frame_number = self.app.current_frame

                total_frames = int(self.app.cap.get(cv2.CAP_PROP_FRAME_COUNT))
                if frame_number >= total_frames:
                    self.app.playing = False
                    self.app.current_frame = frame_number
                    print("Video reached the last frame. Stopping playback.")
                    self.timer.stop()
                    return

                try:
                    while True:
                        processed_data = self.processed_frames_queue.get(timeout=0.01)
                        if processed_data['frame_number'] == frame_number:
                            break
                        else:
                            self.processed_frames_queue.put(processed_data)
                            time.sleep(0.01)
                except Empty:
                    time.sleep(0.01)
                    delay = int(1000 / self.app.fps)
                    self.timer.start(delay)
                    return

                frame = processed_data['frame']
                tracked_objects = processed_data['tracked_objects']
                self.frame = frame
                self.current_tracked_objects = tracked_objects
                frame = self.draw_boxes(frame.copy(), tracked_objects)

                fps = self.fps_counter.get_fps()
                self.app.video_info_label.setText(
                    f"Video Name: {self.app.video_path.split('/')[-1]} | Resolution: 1280x720 | FPS: {fps}"
                )

                rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                height, width, channel = rgb_image.shape
                bytes_per_line = channel * width
                q_image = QImage(rgb_image.data, width, height, bytes_per_line, QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(q_image)
                self.app.video_label.setPixmap(pixmap)

                self.app.current_frame += 1
                delay = int(1000 / self.app.fps)
                self.timer.start(delay)
            else:
                if self.frame is not None:
                    frame = self.draw_boxes(self.frame.copy(), self.current_tracked_objects)
                    rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    height, width, channel = rgb_image.shape
                    bytes_per_line = channel * width
                    q_image = QImage(rgb_image.data, width, height, bytes_per_line, QImage.Format_RGB888)
                    pixmap = QPixmap.fromImage(q_image)
                    self.app.video_label.setPixmap(pixmap)
        else:
            pass

    def stop_processing_frames(self):
        self.stop_processing = True

        for thread in [self.frame_reading_thread, self.inference_thread, self.display_thread]:
            if thread is not None:
                thread.join(timeout=5)
                if thread.is_alive():
                    print(f"{thread.name} did not stop in time.")
        
        with self.frames_queue.mutex:
            self.frames_queue.queue.clear()
        with self.processed_frames_queue.mutex:
            self.processed_frames_queue.queue.clear()

    def refresh_video_display(self):
        if self.frame is not None and self.current_tracked_objects:
            frame = self.draw_boxes(self.frame.copy(), self.current_tracked_objects)
            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            height, width, channel = rgb_image.shape
            bytes_per_line = channel * width
            q_image = QImage(rgb_image.data, width, height, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(q_image)
            self.app.video_label.setPixmap(pixmap)

    def draw_boxes(self, frame, tracked_objects):
        for obj in tracked_objects:
            track_id_str = str(obj['track_id'])

            x1, y1, x2, y2 = map(int, obj['bbox'])

            status_info = self.app.object_statuses.get(
                track_id_str,
                {'status': 'Unknown', 'selected': False, 'threat_level': None}
            )

            status = status_info.get('status', 'Unknown')
            selected = status_info.get('selected', False)
            threat_level = status_info.get('threat_level', None)

            if selected:
                color = (0, 165, 255)       
            elif status == 'friend':
                color = (0, 255, 0)        
            elif status == 'foe':
                color = (0, 0, 255)        
            else:
                color = (175, 175, 0)      


            if threat_level is not None:
                threat_text = f"Threat:{int(threat_level)}"
            else:
                threat_text = "Threat: N/A"

            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

            text_lines = [
                threat_text,
                f"{obj['cls']}",
                f"ID:{track_id_str}"
            ]

            box_width = x2 - x1
            line_height = 20

            for i, line in enumerate(text_lines):
                text_size = cv2.getTextSize(line, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
                text_width = text_size[0]

                text_x = x1 + (box_width - text_width) // 2
                text_y = y1 - 10 - (i * line_height)

                if text_y < 10:
                    text_y = y1 + 10 + (i * line_height)

                cv2.putText(
                    frame, line, (text_x, text_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1
                )

        return frame
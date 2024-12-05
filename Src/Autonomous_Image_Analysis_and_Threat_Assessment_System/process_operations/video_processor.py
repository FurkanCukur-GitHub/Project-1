# process_operations/video_processor.py
import cv2
import threading
import time
import torch
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import QTimer
from object_tracking.object_tracker import ObjectTracker
from queue import Queue, Full
from utils.config import BATCH_SIZE

class VideoProcessor:
    def __init__(self, app):
        self.app = app
        self.object_detector = app.object_detector
        self.object_tracker = ObjectTracker()
        self.processed_frames_queue = Queue(maxsize=500)
        self.current_tracked_objects = []
        self.frame = None
        self.processing_thread = None
        self.stop_processing = False
        self.batch_size = BATCH_SIZE
        cv2.setNumThreads(4)

        self.timer = QTimer()
        self.timer.timeout.connect(self.play_video)

    def start_processing_on_selection(self, video_path, display_width, display_height):
        if self.processing_thread is None or not self.processing_thread.is_alive():
            self.stop_processing = False
            self.processing_thread = threading.Thread(
                target=self.process_frames_on_selection,
                args=(video_path, display_width, display_height),
                daemon=True
            )
            self.processing_thread.start()

    def process_frames_on_selection(self, video_path, display_width, display_height):
        frame_number = 0
        frames_batch = []
        cap = cv2.VideoCapture(video_path)
        while not self.stop_processing:
            ret, frame = cap.read()
            if not ret:
                break
            frame = cv2.resize(frame, (display_width, display_height))
            frames_batch.append((frame_number, frame))
            frame_number += 1

            if len(frames_batch) == self.batch_size:
                self.process_batch(frames_batch)
                frames_batch = []

        if frames_batch:
            self.process_batch(frames_batch)

        cap.release()
        self.stop_processing = True
        print("Frame processing completed.")

    def process_batch(self, frames_batch):
        frames = [frame for _, frame in frames_batch]
        detections_batch = self.object_detector.detect_objects(frames)

        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        for (frame_number, frame), detections in zip(frames_batch, detections_batch):
            tracked_objects = self.object_tracker.update_tracks(detections, frame)
            processed_data = {
                'frame_number': frame_number,
                'frame': frame,
                'tracked_objects': tracked_objects
            }

            while True:
                try:
                    self.processed_frames_queue.put(processed_data, timeout=0.1)
                    break
                except Full:
                    time.sleep(0.01)

    def play_video(self):
        if self.app.cap is not None:
            if not self.processing_thread or not self.processing_thread.is_alive():
                self.start_processing_on_selection(
                    video_path=self.app.video_path,
                    display_width=self.app.display_width,
                    display_height=self.app.display_height
                )
                self.app.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                self.app.current_frame = 0

            if self.app.playing:
                frame_number = self.app.current_frame

                if frame_number >= int(self.app.cap.get(cv2.CAP_PROP_FRAME_COUNT)):
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
                except:
                    time.sleep(0.01)
                    delay = int(1000 / self.app.fps)
                    self.timer.start(delay)
                    return

                frame = processed_data['frame']
                tracked_objects = processed_data['tracked_objects']
                self.frame = frame
                self.current_tracked_objects = tracked_objects
                frame = self.draw_boxes(frame.copy(), tracked_objects)

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
                    frame = self.frame.copy()
                    tracked_objects = self.current_tracked_objects
                    frame = self.draw_boxes(frame, tracked_objects)

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
        if self.processing_thread is not None:
            self.processing_thread.join(timeout=5)
            if self.processing_thread.is_alive():
                print("Processing thread did not stop in time.")
            self.processing_thread = None
        with self.processed_frames_queue.mutex:
            self.processed_frames_queue.queue.clear()
        print("Stopped frame processing and cleared the queue.")

    def draw_boxes(self, frame, tracked_objects):
        for obj in tracked_objects:
            x1, y1, x2, y2 = map(int, obj['bbox'])
            track_id = obj['track_id']
            cls = obj['cls']
            conf = obj['conf']

            status_info = self.app.object_statuses.get(track_id, {'status': None, 'selected': False})
            status = status_info['status']
            selected = status_info['selected']

            if selected:
                color = (0, 165, 255)  # Turuncu
            elif status == 'friend':
                color = (0, 255, 0)  # Yeşil
            elif status == 'adversary':
                color = (0, 0, 255)  # Kırmızı
            else:
                color = (175, 175, 0)  # Varsayılan renk

            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            label = f"{cls} {track_id}"
            cv2.putText(frame, label, (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        return frame


    def refresh_video_display(self):
        if self.frame is not None and self.current_tracked_objects:
            frame = self.draw_boxes(self.frame.copy(), self.current_tracked_objects)
            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            height, width, channel = rgb_image.shape
            bytes_per_line = channel * width
            q_image = QImage(rgb_image.data, width, height, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(q_image)
            self.app.video_label.setPixmap(pixmap)
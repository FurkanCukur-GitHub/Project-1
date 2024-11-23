# process_operations/video_processor.py
import cv2
from PIL import Image, ImageTk
from object_tracking.object_tracker import ObjectTracker

class VideoProcessor:
    def __init__(self, app):
        self.app = app
        self.object_detector = app.object_detector
        self.object_tracker = ObjectTracker()
        self.current_tracked_objects = []
        self.frame = None  # Store current frame

    def play_video(self):
        if self.app.cap is not None:
            if self.app.playing:
                ret, frame = self.app.cap.read()
                if not ret:
                    print("Reached the end of the video.")
                    self.app.playing = False
                    self.app.cap.release()
                    return

                # Resize frame to fit display
                frame = cv2.resize(frame, (self.app.display_width, self.app.display_height))

                # Detect objects
                detections = self.object_detector.detect_objects(frame)

                # Update tracker
                tracked_objects = self.object_tracker.update_tracks(detections, frame)
                self.current_tracked_objects = tracked_objects  # Store for access in click event

                # Store the frame
                self.frame = frame
            else:
                # If paused, use the last frame
                frame = self.frame
                tracked_objects = self.current_tracked_objects

            # Draw bounding boxes and IDs
            frame = self.draw_boxes(frame, tracked_objects)

            # Convert frame to ImageTk format
            image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(image)
            imgtk = ImageTk.PhotoImage(image=image)

            # Update video label
            self.app.video_label.imgtk = imgtk
            self.app.video_label.configure(image=imgtk)

            # Schedule next frame
            delay = int(1000 / self.app.fps)
            self.app.root.after(delay, self.play_video)
        else:
            # Video is not loaded
            pass

    def draw_boxes(self, frame, tracked_objects):
        for obj in tracked_objects:
            x1, y1, x2, y2 = obj['bbox']
            track_id = obj['track_id']
            cls = obj['cls']  # Sınıf adı olarak doğrudan string kullanıyoruz

            x1 = int(x1)
            y1 = int(y1)
            x2 = int(x2)
            y2 = int(y2)

            # Determine the color based on object status
            status = self.app.object_statuses.get(track_id, None)
            if status == 'selected':
                color = (0, 165, 255)  # Orange
            elif status == 'friend':
                color = (0, 255, 0)    # Green
            elif status == 'adversary':
                color = (0, 0, 255)    # Red
            else:
                color = (175, 175, 0)  # Default color (yellowish)

            # Draw rectangle
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            
            label = f"{cls}"
            
            # Put label above the bounding box
            cv2.putText(frame, label, (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

        return frame

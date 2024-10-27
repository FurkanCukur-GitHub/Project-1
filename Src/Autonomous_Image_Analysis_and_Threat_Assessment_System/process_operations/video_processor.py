import time
import cv2
from PIL import Image, ImageTk

class VideoProcessor:
    def __init__(self, app):
        self.app = app

    def play_video(self):
        while self.app.playing and self.app.cap.isOpened():
            start_time = time.time()

            if self.app.direction == 1:
                ret, frame = self.app.cap.read()
                if not ret:
                    # End of video reached, reset to start
                    self.app.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, frame = self.app.cap.read()
                    if not ret:
                        break
            elif self.app.direction == -1:
                # Reverse playback: go back two frames and read one
                current_frame = int(self.app.cap.get(cv2.CAP_PROP_POS_FRAMES))
                new_frame = current_frame - 2  # Go back two frames
                if new_frame < 0:
                    # Start of video reached, move to end
                    frame_count = int(self.app.cap.get(cv2.CAP_PROP_FRAME_COUNT))
                    self.app.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_count - 1)
                else:
                    self.app.cap.set(cv2.CAP_PROP_POS_FRAMES, new_frame)
                ret, frame = self.app.cap.read()
                if not ret:
                    self.app.event_handlers.stop_video()
                    break

            self.app.current_frame += 1
            if self.app.current_frame % self.app.frame_skip != 0:
                continue  # Skip frame if frame skipping is enabled

            # Resize frame to fit video display area
            frame = cv2.resize(frame, (self.app.display_width, self.app.display_height))

            # Convert frame to RGB format
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Perform object detection
            try:
                results = self.app.object_detector.detect_objects(frame_rgb)
                # Manually draw annotations
                annotated_frame = self.draw_annotations(frame_rgb, results)
            except Exception as e:
                print(f"Error during model inference: {e}")
                self.app.event_handlers.stop_video()
                break

            # Convert to PIL Image
            img = Image.fromarray(annotated_frame)
            imgtk = ImageTk.PhotoImage(image=img)

            # Update video label in the main thread
            self.app.video_label.after(0, self.update_video_label, imgtk)

            # Calculate elapsed time and determine sleep duration
            elapsed_time = time.time() - start_time
            time.sleep(max(0, (1 / self.app.fps) - elapsed_time))

        # Reset thread running flag when loop ends
        self.app.video_thread_running = False

    def update_video_label(self, imgtk):
        self.app.video_label.imgtk = imgtk
        self.app.video_label.configure(image=imgtk)

    def draw_annotations(self, frame, results):
        # Iterate over each detection result
        for result in results:
            for box in result.boxes:
                # Get bounding box coordinates
                xyxy = box.xyxy[0].cpu().numpy()  # [x1, y1, x2, y2]
                x1, y1, x2, y2 = map(int, xyxy)
                
                # Get class name
                class_id = int(box.cls[0].cpu().numpy())
                class_name = self.app.object_detector.model.names[class_id]  # Adjust based on how your model stores class names

                # Draw bounding box
                cv2.rectangle(frame, (x1, y1), (x2, y2), color=(0, 255, 0), thickness=3)

                # Put class name text
                cv2.putText(frame, class_name, (x1, y1 - 10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (36,255,12), 2)

        return frame

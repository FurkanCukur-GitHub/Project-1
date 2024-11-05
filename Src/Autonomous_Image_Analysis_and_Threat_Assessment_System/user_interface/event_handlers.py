# user_interface/event_handlers.py
import threading
import cv2
from tkinter import filedialog, messagebox

class EventHandlers:
    def __init__(self, app):
        self.app = app

    # Action button functions (no message boxes)
    def select_object(self):
        # Implement object selection logic here
        print("Select Object button clicked.")

    def select_region(self):
        # Implement region selection logic here
        print("Select Region button clicked.")

    def track_object(self):
        # Implement object tracking logic here
        print("Track Object button clicked.")

    def untrack_object(self):
        # Implement untracking logic here
        print("Untrack Object button clicked.")

    def mark_adversary(self):
        # Implement adversary marking logic here
        print("Mark as Adversary button clicked.")

    def mark_friend(self):
        # Implement friend marking logic here
        print("Mark as Friend button clicked.")

    def perform_threat_assessment(self):
        # Implement threat assessment logic here
        print("Perform Threat Assessment button clicked.")

    # Video control functions
    def open_video(self):
        if self.app.playing:
            self.stop_video()

        self.app.video_path = filedialog.askopenfilename(
            title="Select Video",
            filetypes=[("Video Files", "*.mp4 *.avi *.mov")]
        )

        if self.app.video_path:
            self.app.cap = cv2.VideoCapture(self.app.video_path)
            if not self.app.cap.isOpened():
                messagebox.showerror("Error", "Failed to open the video.")
                return

            self.app.fps = self.app.cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(self.app.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(self.app.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.app.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            # Update video info label
            self.app.video_info_label.config(
                text=f"Video: {self.app.video_path.split('/')[-1]} | Resolution: {width}x{height} | Frames: {frame_count} | FPS: {self.app.fps:.2f}"
            )

            # Scale video to fit within the fixed video frame while maintaining aspect ratio
            display_width = self.app.video_frame_width
            display_height = self.app.video_frame_height

            # Calculate scaling factor while maintaining aspect ratio
            scale_w = display_width / width
            scale_h = display_height / height
            scale = min(scale_w, scale_h)

            self.app.display_width = int(width * scale)
            self.app.display_height = int(height * scale)

            # Resize video frame to fixed size
            self.app.video_frame.config(width=self.app.video_frame_width, height=self.app.video_frame_height)
            self.app.video_frame.pack_propagate(0)  # Prevent frame from resizing to content

            # Reset frame counter
            self.app.current_frame = 0

            self.app.direction = 1  # Set to forward playback
            self.app.playing = True

            # Start video playback in a separate thread
            if not self.app.video_thread_running:
                self.app.video_thread = threading.Thread(target=self.app.video_processor.play_video, daemon=True)
                self.app.video_thread.start()
                self.app.video_thread_running = True

    def pause_video(self):
        if self.app.playing:
            self.app.playing = False
            print("Video paused.")
        else:
            print("Video is already paused.")

    def stop_video(self):
        if self.app.cap is not None:
            self.app.playing = False
            self.app.cap.release()
            self.app.cap = None
            self.app.video_label.config(image='')  # Clear video display
            self.app.video_info_label.config(text="No video selected.")
            print("Video stopped.")

    def resume_video(self):
        if self.app.video_path:
            if not self.app.playing:
                self.app.direction = 1  # Forward playback
                self.app.playing = True

                # Start video playback in a separate thread
                if not self.app.video_thread_running:
                    self.app.video_thread = threading.Thread(target=self.app.video_processor.play_video, daemon=True)
                    self.app.video_thread.start()
                    self.app.video_thread_running = True
                print("Video resumed.")
            else:
                print("Video is already playing.")
        else:
            messagebox.showwarning("Warning", "No video selected to resume.")

    def rewind_video(self):
        if self.app.cap is not None:
            self.app.direction = -1  # Set to reverse playback
            if not self.app.playing:
                self.app.playing = True

                # Start video playback in a separate thread
                if not self.app.video_thread_running:
                    self.app.video_thread = threading.Thread(target=self.app.video_processor.play_video, daemon=True)
                    self.app.video_thread.start()
                    self.app.video_thread_running = True
            print("Video rewinding.")
        else:
            messagebox.showwarning("Warning", "Please select a video first to rewind.")

    def quit_app(self):
        self.stop_video()
        self.app.root.quit()
        print("Application exited.")

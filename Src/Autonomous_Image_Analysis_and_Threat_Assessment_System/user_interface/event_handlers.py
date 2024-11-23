# user_interface/event_handlers.py
import cv2
from tkinter import filedialog, messagebox

class EventHandlers:
    def __init__(self, app):
        self.app = app

    # --- Action Button Functions ---
    def select_object(self):
        if self.app.playing:
            self.pause_video()
        self.app.selecting_object = True

        # Deselect any previously selected object
        if self.app.selected_object_id is not None:
            self.app.object_statuses[self.app.selected_object_id] = None
            self.app.selected_object_id = None

        # Disable 'Mark as Friend' and 'Mark as Adversary' buttons until an object is selected
        if hasattr(self.app, 'mark_friend_button') and hasattr(self.app, 'mark_adversary_button'):
            self.app.mark_friend_button.config(state='disabled')
            self.app.mark_adversary_button.config(state='disabled')

        print("Select Object mode activated. Click on an object in the video.")

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
        if self.app.selected_object_id is not None:
            self.app.object_statuses[self.app.selected_object_id] = 'adversary'
            print(f"Object {self.app.selected_object_id} marked as Adversary.")

            # Reset selection
            self.app.selected_object_id = None
            self.app.selecting_object = False

            # Disable buttons after marking
            self.app.mark_friend_button.config(state='disabled')
            self.app.mark_adversary_button.config(state='disabled')

            # Resume video playback
            self.resume_video()
        else:
            print("No object selected to mark as Adversary.")

    def mark_friend(self):
        if self.app.selected_object_id is not None:
            self.app.object_statuses[self.app.selected_object_id] = 'friend'
            print(f"Object {self.app.selected_object_id} marked as Friend.")

            # Reset selection
            self.app.selected_object_id = None
            self.app.selecting_object = False

            # Disable buttons after marking
            self.app.mark_friend_button.config(state='disabled')
            self.app.mark_adversary_button.config(state='disabled')

            # Resume video playback
            self.resume_video()
        else:
            print("No object selected to mark as Friend.")

    def perform_threat_assessment(self):
        # Implement threat assessment logic here
        print("Perform Threat Assessment button clicked.")

    # --- Video Control Functions ---
    def open_video(self):
        # If a video is playing, stop it
        if self.app.playing:
            self.stop_video()

        # Open file dialog to select a new video
        video_path = filedialog.askopenfilename(
            title="Select Video",
            filetypes=[("Video Files", "*.mp4 *.avi *.mov")]
        )

        if video_path:
            # If a video is selected, open and start playing
            self.app.video_path = video_path
            self.app.cap = cv2.VideoCapture(self.app.video_path)
            if not self.app.cap.isOpened():
                messagebox.showerror("Error", "An error occurred while opening the video.")
                self.app.cap = None
                self.app.video_path = None
                return

            # Get video information
            self.app.fps = self.app.cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(self.app.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(self.app.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.app.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            # Update video info label
            video_name = self.app.video_path.split('/')[-1]
            self.app.video_info_label.config(
                text=f"Video: {video_name} | Resolution: {width}x{height} | Frame Count: {frame_count} | FPS: {self.app.fps:.2f}"
            )

            # Resize video for display
            self.app.display_width = self.app.video_frame_width
            self.app.display_height = self.app.video_frame_height

            # Reset frame counter
            self.app.current_frame = 0

            # Clear object statuses
            self.app.object_statuses.clear()

            self.app.playing = True

            # Start video playback
            self.app.video_processor.play_video()

            # Update button states
            if hasattr(self.app, 'play_button') and hasattr(self.app, 'pause_button'):
                self.app.play_button.config(state='disabled')
                self.app.pause_button.config(state='normal')
        else:
            # If the user cancels the file selection
            self.app.video_label.config(image='')
            self.app.video_info_label.config(text="No video selected.")
            self.app.video_path = None
            print("No video selected.")

    def stop_video(self):
        try:
            if self.app.cap is not None:
                self.app.playing = False
                self.app.cap.release()
                self.app.cap = None
                self.app.video_label.config(image='')  # Clear the video display
                self.app.video_info_label.config(text="No video selected.")
                print("Video stopped.")

                # Update button states
                if hasattr(self.app, 'play_button') and hasattr(self.app, 'pause_button'):
                    self.app.play_button.config(state='normal')
                    self.app.pause_button.config(state='disabled')
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred while stopping the video: {e}")
            print(f"Error stopping video: {e}")

    def pause_video(self):
        if self.app.playing:
            self.app.playing = False
            print("Video paused.")
            if hasattr(self.app, 'play_button') and hasattr(self.app, 'pause_button'):
                self.app.play_button.config(state='normal')
                self.app.pause_button.config(state='disabled')
        else:
            print("Video is already paused.")

    def resume_video(self):
        if self.app.video_path:
            if not self.app.playing:
                # Deselect any selected object
                if self.app.selected_object_id is not None:
                    # Remove 'selected' status from the object
                    self.app.object_statuses[self.app.selected_object_id] = None
                    self.app.selected_object_id = None
                    self.app.selecting_object = False

                    # Disable 'Mark as Friend' and 'Mark as Adversary' buttons
                    if hasattr(self.app, 'mark_friend_button') and hasattr(self.app, 'mark_adversary_button'):
                        self.app.mark_friend_button.config(state='disabled')
                        self.app.mark_adversary_button.config(state='disabled')

                self.app.playing = True
                print("Resuming video.")
                if hasattr(self.app, 'play_button') and hasattr(self.app, 'pause_button'):
                    self.app.play_button.config(state='disabled')
                    self.app.pause_button.config(state='normal')
            else:
                print("Video is already playing.")
        else:
            messagebox.showwarning("Warning", "No video selected to resume.")

    def quit_app(self):
        # Stop the video when exiting the application
        self.stop_video()
        self.app.root.quit()
        print("Application closed.")
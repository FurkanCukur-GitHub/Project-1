# user_interface/event_handlers.py
import cv2
from PyQt5.QtWidgets import QFileDialog, QMessageBox

class EventHandlers:
    def __init__(self, app):
        self.app = app

    # --- Action Button Functions ---
    def select_object(self):
        if self.app.playing:
            self.pause_video()
        self.app.selecting_object = True
        self.app.selecting_region = False

        # Mevcut seçimi temizle
        for track_id in list(self.app.object_statuses.keys()):
            if self.app.object_statuses[track_id] == 'selected':
                self.app.object_statuses[track_id] = None

        self.app.selected_object_ids = []

        if hasattr(self.app, 'mark_friend_button') and hasattr(self.app, 'mark_adversary_button'):
            self.app.mark_friend_button.setEnabled(False)
            self.app.mark_adversary_button.setEnabled(False)

        print("Select Object mode activated. Click on an object in the video.")

    def select_region(self):
        if self.app.playing:
            self.pause_video()

        # Select Region modunu aktif tut
        self.app.selecting_region = True
        self.app.selecting_object = False

        # Mevcut seçimi temizle
        for track_id in list(self.app.object_statuses.keys()):
            if self.app.object_statuses[track_id] == 'selected':
                self.app.object_statuses[track_id] = None

        self.app.selected_object_ids = []

        if hasattr(self.app, 'mark_friend_button') and hasattr(self.app, 'mark_adversary_button'):
            self.app.mark_friend_button.setEnabled(False)
            self.app.mark_adversary_button.setEnabled(False)

        print("Select Region mode activated. You can select multiple regions until you mark, play, or switch modes.")

    def track_object(self):
        print("Track Object button clicked.")

    def untrack_object(self):
        print("Untrack Object button clicked.")

    def mark_friend(self):
        if self.app.selected_object_ids:
            for track_id in self.app.selected_object_ids:
                if track_id not in self.app.object_statuses:
                    self.app.object_statuses[track_id] = {'status': None, 'selected': False}
                self.app.object_statuses[track_id]['status'] = 'friend'
                print(f"Object {track_id} marked as Friend.")
            # Seçimleri temizle
            self.app.selected_object_ids = []
            for track_id in self.app.object_statuses.keys():
                self.app.object_statuses[track_id]['selected'] = False
            self.app.selecting_region = False
            self.app.selecting_object = False

            if hasattr(self.app, 'mark_friend_button') and hasattr(self.app, 'mark_adversary_button'):
                self.app.mark_friend_button.setEnabled(False)
                self.app.mark_adversary_button.setEnabled(False)
            self.app.video_processor.refresh_video_display()
            self.resume_video()
        else:
            print("No objects selected to mark as Friend.")

    def mark_adversary(self):
        if self.app.selected_object_ids:
            for track_id in self.app.selected_object_ids:
                if track_id not in self.app.object_statuses:
                    self.app.object_statuses[track_id] = {'status': None, 'selected': False}
                self.app.object_statuses[track_id]['status'] = 'adversary'
                print(f"Object {track_id} marked as Adversary.")
            # Seçimleri temizle
            self.app.selected_object_ids = []
            for track_id in self.app.object_statuses.keys():
                self.app.object_statuses[track_id]['selected'] = False
            self.app.selecting_region = False
            self.app.selecting_object = False

            if hasattr(self.app, 'mark_friend_button') and hasattr(self.app, 'mark_adversary_button'):
                self.app.mark_friend_button.setEnabled(False)
                self.app.mark_adversary_button.setEnabled(False)
            self.app.video_processor.refresh_video_display()
            self.resume_video()
        else:
            print("No objects selected to mark as Adversary.")

    def perform_threat_assessment(self):
        print("Perform Threat Assessment button clicked.")

    # --- Video Control Functions ---
    def open_video(self):
        self.stop_video()

        # File selection dialog
        options = QFileDialog.Options()
        video_path, _ = QFileDialog.getOpenFileName(
            self.app,
            "Select Video",
            "",
            "Video Files (*.mp4 *.avi *.mov)",
            options=options
        )

        if video_path:
            self.app.video_path = video_path
            self.app.cap = cv2.VideoCapture(self.app.video_path)
            if not self.app.cap.isOpened():
                QMessageBox.critical(self.app, "Error", "An error occurred while opening the video.")
                self.app.cap = None
                self.app.video_path = None
                return

            self.app.fps = self.app.cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(self.app.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(self.app.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.app.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            video_name = self.app.video_path.split('/')[-1]
            self.app.video_info_label.setText(
                f"Video: {video_name} | Resolution: {width}x{height} | Frame Count: {frame_count} | FPS: {self.app.fps:.2f}"
            )

            self.app.display_width = self.app.video_frame_width
            self.app.display_height = self.app.video_frame_height
            self.app.current_frame = 0

            self.app.video_processor.stop_processing_frames()
            self.app.video_processor.start_processing_on_selection(
                video_path=self.app.video_path,
                display_width=self.app.display_width,
                display_height=self.app.display_height
            )

            self.resume_video()

            if hasattr(self.app, 'play_button') and hasattr(self.app, 'pause_button'):
                self.app.play_button.setEnabled(False)
                self.app.pause_button.setEnabled(True)
        else:
            self.app.video_label.clear()
            self.app.video_info_label.setText("No video selected.")
            self.app.video_path = None
            print("No video selected.")

    def stop_video(self):
        try:
            if self.app.cap is not None:
                self.app.playing = False
                self.app.cap.release()
                self.app.cap = None
                self.app.video_label.clear()
                self.app.video_info_label.setText("No video selected.")
                print("Video stopped.")

                self.app.video_processor.stop_processing_frames()

                if hasattr(self.app, 'play_button') and hasattr(self.app, 'pause_button'):
                    self.app.play_button.setEnabled(True)
                    self.app.pause_button.setEnabled(False)
        except Exception as e:
            QMessageBox.critical(self.app, "Error", f"An error occurred while stopping the video: {e}")
            print(f"Error stopping video: {e}")

    def pause_video(self):
        if self.app.playing:
            self.app.playing = False
            self.app.video_processor.timer.stop()
            print("Video paused.")
            if hasattr(self.app, 'play_button') and hasattr(self.app, 'pause_button'):
                self.app.play_button.setEnabled(True)
                self.app.pause_button.setEnabled(False)
        else:
            print("Video is already paused.")

    def resume_video(self):
        if self.app.video_path:
            if not self.app.playing:
                # 'selected' durumunu temizle, 'status' korunur
                for track_id in self.app.object_statuses.keys():
                    self.app.object_statuses[track_id]['selected'] = False

                self.app.selected_object_ids = []
                self.app.selecting_region = False
                self.app.selecting_object = False

                self.app.playing = True
                print("Resuming video.")

                if hasattr(self.app, 'play_button') and hasattr(self.app, 'pause_button'):
                    self.app.play_button.setEnabled(False)
                    self.app.pause_button.setEnabled(True)

                self.app.video_processor.refresh_video_display()
                self.app.video_processor.play_video()
            else:
                print("Video is already playing.")
        else:
            QMessageBox.warning(self.app, "Warning", "No video selected to resume.")

    def quit_app(self):
        try:
            self.stop_video()
            if hasattr(self.app, 'video_processor'):
                self.app.video_processor.stop_processing_frames()

            if self.app.cap is not None:
                self.app.cap.release()
                self.app.cap = None

            self.app.close()
            print("Application closed successfully.")

        except Exception as e:
            print(f"Error during application exit: {e}")
            self.app.close()
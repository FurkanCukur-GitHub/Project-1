# user_interface/ui.py
from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QFrame, QVBoxLayout, QHBoxLayout, QGridLayout,
    QFileDialog, QMessageBox, QApplication, QSpacerItem, QSizePolicy
)

from PyQt5.QtGui import QFont, QPixmap, QImage, QMouseEvent, QPainter, QPen
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from user_interface.event_handlers import EventHandlers
from process_operations.video_processor import VideoProcessor
from object_detection.object_detector import ObjectDetector

class ClickableLabel(QLabel):
    clicked = pyqtSignal(QMouseEvent)
    region_selected = pyqtSignal(tuple)  # Emit (x1, y1, x2, y2)

    def __init__(self, parent_app, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.object_statuses = {}  # {track_id: {'status': 'friend'/'adversary'/None, 'selected': True/False}}
        self.selected_object_ids = []  # Birden fazla nesneyi tutmak için liste
        self.parent_app = parent_app  # Application nesnesine referans
        self.start_point = None
        self.end_point = None
        self.drawing = False
        self.current_rect = None

    def mousePressEvent(self, event):
        if self.parent_app.selecting_region:  # Doğru kontrol
            self.start_point = event.pos()
            self.drawing = True
            self.current_rect = None
            self.update()
        else:
            self.clicked.emit(event)

    def mouseMoveEvent(self, event):
        if self.drawing:
            self.end_point = event.pos()
            self.current_rect = (self.start_point, self.end_point)
            self.update()  # Redraw the label to show the selection rectangle

    def mouseReleaseEvent(self, event):
        if self.drawing:
            self.end_point = event.pos()
            self.drawing = False
            self.update()
            x1, y1 = self.start_point.x(), self.start_point.y()
            x2, y2 = self.end_point.x(), self.end_point.y()
            self.region_selected.emit((min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)))
            self.start_point = None
            self.end_point = None
            self.current_rect = None

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.current_rect:
            painter = QPainter(self)
            pen = QPen(Qt.red, 2, Qt.DashLine)
            painter.setPen(pen)
            p1, p2 = self.current_rect
            x1, y1 = p1.x(), p1.y()
            x2, y2 = p2.x(), p2.y()
            painter.drawRect(min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))

class Application(QWidget):
    def __init__(self):
        super().__init__()
        # Initialize ObjectDetector
        self.object_detector = ObjectDetector()

        # Initialize VideoProcessor
        self.video_processor = VideoProcessor(self)

        # Initialize EventHandlers
        self.event_handlers = EventHandlers(self)

        # Video control variables
        self.playing = False
        self.video_path = ""
        self.cap = None
        self.fps = 0
        self.current_frame = 0
        self.object_statuses = {}
        self.selected_object_ids = []  # Birden fazla nesneyi tutmak için liste
        self.selecting_object = False
        self.selecting_region = False  # Yeni eklenen değişken

        self.setWindowTitle("System User Interface")
        self.setStyleSheet("background-color: #2C3E50;")
        self.default_font = QFont("Helvetica", 12)

        # Define fixed window size and center it
        self.window_width = 1700
        self.window_height = 950
        self.setFixedSize(self.window_width, self.window_height)
        self.center_window()

        # Main layout
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)

        # Video info section (top)
        self.video_info_frame = QFrame()
        self.video_info_frame.setStyleSheet("background-color: #34495E")
        self.video_info_frame.setFixedHeight(80)
        self.main_layout.addWidget(self.video_info_frame)

        self.video_info_layout = QVBoxLayout()
        self.video_info_frame.setLayout(self.video_info_layout)
        self.video_info_label = QLabel("No video selected.")
        self.video_info_label.setStyleSheet("color: white;")
        self.video_info_label.setFont(self.default_font)
        self.video_info_layout.addWidget(self.video_info_label)

        # Content section (middle)
        self.content_frame = QFrame()
        self.content_frame.setStyleSheet("background-color: #34495E")
        self.main_layout.addWidget(self.content_frame)

        self.content_layout = QHBoxLayout()
        self.content_frame.setLayout(self.content_layout)

        # Add left margin before video frame
        self.left_margin = QSpacerItem(20, 20, QSizePolicy.Fixed, QSizePolicy.Minimum)
        self.content_layout.addSpacerItem(self.left_margin)

        # Video frame (middle-left)
        self.video_frame = QFrame()
        self.video_frame.setStyleSheet("background-color: black")
        self.video_frame_width = 1280
        self.video_frame_height = 720
        self.video_frame.setFixedSize(self.video_frame_width, self.video_frame_height)
        self.content_layout.addWidget(self.video_frame)

        # Remove padding around video_label to avoid black gaps
        self.video_frame_layout = QVBoxLayout()
        self.video_frame_layout.setAlignment(Qt.AlignCenter)
        self.video_frame_layout.setContentsMargins(0, 0, 0, 0)  # Remove all margins
        self.video_frame_layout.setSpacing(0)  # Remove spacing
        self.video_frame.setLayout(self.video_frame_layout)

        self.video_label = ClickableLabel(self)  # self referansı geçildi
        self.video_label.setStyleSheet("background-color: black;")  # Matches the frame color
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setFixedSize(self.video_frame_width, self.video_frame_height)  # Match the frame size
        self.video_label.clicked.connect(self.on_video_click)
        self.video_label.region_selected.connect(self.on_region_selected)  # Yeni eklenen sinyal bağlantısı
        self.video_frame_layout.addWidget(self.video_label)


        # Add right margin after video frame
        self.right_margin = QSpacerItem(20, 20, QSizePolicy.Fixed, QSizePolicy.Minimum)
        self.content_layout.addSpacerItem(self.right_margin)

        # Spacer frame between video and action buttons
        self.spacer_frame = QFrame()
        self.spacer_frame.setStyleSheet("background-color: #2C3E50;")
        self.spacer_frame.setFixedWidth(10)  # Genişlik
        self.content_layout.setContentsMargins(0, 0, 0, 0)  # Kenar boşluklarını sıfırla
        self.content_layout.setSpacing(0)  # Layout içerisindeki spacing'i kaldır
        self.content_layout.addWidget(self.spacer_frame)

        # Action buttons frame (middle-right)
        self.action_frame = QFrame()
        self.action_frame.setStyleSheet("background-color: #34495E")
        self.action_frame.setFixedWidth(300)
        self.action_frame.setFixedHeight(720)
        self.content_layout.addWidget(self.action_frame)

        self.action_layout = QVBoxLayout()
        self.action_layout.setAlignment(Qt.AlignCenter)
        self.action_frame.setLayout(self.action_layout)

        # Create action buttons
        self.create_action_buttons()

        # Control buttons section (bottom)
        self.control_frame = QFrame()
        self.control_frame.setStyleSheet("background-color: #34495E")
        self.control_frame.setFixedHeight(80)
        self.main_layout.addWidget(self.control_frame)

        self.control_layout = QHBoxLayout()
        self.control_layout.setSpacing(20)
        self.control_frame.setLayout(self.control_layout)

        # Create control buttons
        self.create_control_buttons()

    def center_window(self):
        frame_geometry = self.frameGeometry()
        center_point = QApplication.desktop().availableGeometry().center()
        frame_geometry.moveCenter(center_point)
        self.move(frame_geometry.topLeft())

    def create_action_buttons(self):
        button_specs = [
            ("Select Object", self.event_handlers.select_object, "#2980B9"),
            ("Select Region", self.event_handlers.select_region, "#2980B9"),
            ("Track Object", self.event_handlers.track_object, "#2980B9"),
            ("Untrack Object", self.event_handlers.untrack_object, "#2980B9"),
            ("Mark as Adversary", self.event_handlers.mark_adversary, "#C0392B"),
            ("Mark as Friend", self.event_handlers.mark_friend, "#27AE60"),
            ("Threat Assessment", self.event_handlers.perform_threat_assessment, "#000000")
        ]


        self.action_layout.setSpacing(20)

        for text, command, color in button_specs:
            btn = QPushButton(text)
            btn.clicked.connect(command)
            btn.setFixedSize(200, 50)
            btn.setStyleSheet(f"""
                background-color: {color};
                color: white;
                border: none;
                border-radius: 25px;
            """)
            btn.setFont(self.default_font)
            btn.setCursor(Qt.PointingHandCursor)
            self.action_layout.addWidget(btn)

            if text == "Mark as Friend":
                self.mark_friend_button = btn
                self.mark_friend_button.setEnabled(False)
            elif text == "Mark as Adversary":
                self.mark_adversary_button = btn
                self.mark_adversary_button.setEnabled(False)

    def create_control_buttons(self):
        control_buttons = [
            ("Select Video", self.event_handlers.open_video, "#2980B9"),
            ("Play", self.event_handlers.resume_video, "#27AE60"),
            ("Pause", self.event_handlers.pause_video, "#F1C40F"),
            ("Exit", self.event_handlers.quit_app, "#C0392B")
        ]

        for text, command, color in control_buttons:
            btn = QPushButton(text)
            btn.clicked.connect(command)
            btn.setFixedSize(200, 50)
            btn.setStyleSheet(f"""
                background-color: {color};
                color: white;
                border: none;
                border-radius: 25px;
            """)
            btn.setFont(self.default_font)
            btn.setCursor(Qt.PointingHandCursor)
            self.control_layout.addWidget(btn)

            if text == "Play":
                self.play_button = btn
                self.play_button.setEnabled(False)
            elif text == "Pause":
                self.pause_button = btn
                self.pause_button.setEnabled(False)

    def on_video_click(self, event):
        if self.selecting_object:
            x_click = event.pos().x()
            y_click = event.pos().y()
            tracked_objects = self.video_processor.current_tracked_objects
            object_selected = False

            # Önce mevcut seçimi temizle
            for track_id in self.object_statuses.keys():
                self.object_statuses[track_id]['selected'] = False

            self.selected_object_ids = []

            for obj in tracked_objects:
                x1, y1, x2, y2 = map(int, obj['bbox'])
                track_id = obj['track_id']

                if x1 <= x_click <= x2 and y1 <= y_click <= y2:
                    if track_id not in self.object_statuses:
                        self.object_statuses[track_id] = {'status': None, 'selected': False}
                    self.object_statuses[track_id]['selected'] = True
                    self.selected_object_ids.append(track_id)
                    print(f"Object {track_id} selected.")
                    object_selected = True
                    break

            if object_selected:
                if hasattr(self, 'mark_friend_button') and hasattr(self, 'mark_adversary_button'):
                    self.mark_friend_button.setEnabled(True)
                    self.mark_adversary_button.setEnabled(True)
            else:
                if hasattr(self, 'mark_friend_button') and hasattr(self, 'mark_adversary_button'):
                    self.mark_friend_button.setEnabled(False)
                    self.mark_adversary_button.setEnabled(False)
                print("No object selected.")

            self.video_processor.refresh_video_display()


    def on_region_selected(self, region):
        if self.selecting_region:
            x1, y1, x2, y2 = region

            # Önce mevcut seçimi temizle
            for track_id in self.object_statuses.keys():
                self.object_statuses[track_id]['selected'] = False

            self.selected_object_ids = []

            # Seçilen alan içindeki nesneleri bul
            tracked_objects = self.video_processor.current_tracked_objects
            objects_selected = False

            for obj in tracked_objects:
                obj_x1, obj_y1, obj_x2, obj_y2 = obj['bbox']
                track_id = obj['track_id']

                if not (x2 < obj_x1 or x1 > obj_x2 or y2 < obj_y1 or y1 > obj_y2):
                    if track_id not in self.object_statuses:
                        self.object_statuses[track_id] = {'status': None, 'selected': False}
                    self.object_statuses[track_id]['selected'] = True
                    self.selected_object_ids.append(track_id)
                    print(f"Object {track_id} selected in region.")
                    objects_selected = True

            if objects_selected:
                if hasattr(self, 'mark_friend_button') and hasattr(self, 'mark_adversary_button'):
                    self.mark_friend_button.setEnabled(True)
                    self.mark_adversary_button.setEnabled(True)
            else:
                print("No objects found in the selected region.")

            self.selecting_region = True
            self.video_processor.refresh_video_display()


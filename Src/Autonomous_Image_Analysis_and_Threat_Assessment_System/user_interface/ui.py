# user_interface/ui.py
from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QFrame, QVBoxLayout, QHBoxLayout, QApplication, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt5.QtGui import QFont, QMouseEvent, QPainter, QPen, QBrush, QColor
from PyQt5.QtCore import Qt, pyqtSignal, QTimer

from threat_assesment.threat_assessment import ThreatAssessment
from user_interface.event_handlers import EventHandlers
from process_operations.video_processor import VideoProcessor
from object_detection.object_detector import ObjectDetector


class ClickableLabel(QLabel):
    clicked = pyqtSignal(QMouseEvent)
    region_selected = pyqtSignal(tuple)

    def __init__(self, parent_app, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parent_app = parent_app
        self.start_point = None
        self.end_point = None
        self.drawing = False
        self.current_rect = None

    def mousePressEvent(self, event):
        if self.parent_app.selecting_region:
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
            self.update()

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
        # Initialize ThreatAssessment
        self.threat_assessment = ThreatAssessment()
        # Initialize EventHandlers
        self.event_handlers = EventHandlers(self)

        # Video control variables
        self.playing = False
        self.video_path = ""
        self.cap = None
        self.fps = 0
        self.current_frame = 0
        self.object_statuses = {}
        self.selected_object_ids = []
        self.selecting_object = False
        self.selecting_region = False

        self.setWindowTitle("System User Interface")
        self.setStyleSheet("background-color: #2C3E50;")
        self.default_font = QFont("Helvetica", 12)

        # Updated window width and height
        self.window_width = 2060
        self.window_height = 1100
        self.setFixedSize(self.window_width, self.window_height)
        self.center_window()

        # Left Panel 1 - Object List
        self.left_panel1 = QFrame(self)
        self.left_panel1.setStyleSheet("background-color: #34495E;")
        self.left_panel1.setGeometry(30, 30, 300, 1040)  # Width 300
        self.left_panel1_layout = QVBoxLayout()
        self.left_panel1_layout.setSpacing(30)
        self.left_panel1.setLayout(self.left_panel1_layout)

        # QTableWidget for object list
        self.object_table = QTableWidget()
        self.object_table.setColumnCount(4)
        self.object_table.setHorizontalHeaderLabels(["ID", "Type", "Status", "Threat"])
        self.object_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.object_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.object_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.object_table.setSelectionMode(QTableWidget.SingleSelection)
        self.object_table.verticalHeader().setVisible(False)
        # Manually set column widths
        self.object_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.object_table.setColumnWidth(0, 25)
        self.object_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.object_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.object_table.setColumnWidth(3, 55)
        self.object_table.setStyleSheet("""
            QTableWidget {
                background-color: #2C3E50;
                color: white;
                border: none;
            }
            QHeaderView::section {
                background-color: #34495E;
                color: white;
                font-weight: bold;
            }
            QTableWidget::item:selected {
                background-color: #FFA500;
                color: white;
            }
            QTableWidget::item:hover {
                background-color: #3D566E;
                color: white;
            }
        """)
        self.object_table.cellClicked.connect(self.on_object_table_click)
        self.left_panel1_layout.addWidget(self.object_table)

        # Top
        self.video_info_frame = QFrame(self)
        self.video_info_frame.setStyleSheet("background-color: #34495E")
        self.video_info_frame.setGeometry(360, 30, 1670, 100)
        self.video_info_layout = QVBoxLayout()
        self.video_info_frame.setLayout(self.video_info_layout)
        self.video_info_label = QLabel("No video selected.")
        self.video_info_label.setStyleSheet("color: white;")
        self.video_info_label.setFont(self.default_font)
        self.video_info_layout.addWidget(self.video_info_label)

        # Middle Left
        self.content_frame = QFrame(self)
        self.content_frame.setStyleSheet("background-color: #34495E")
        self.content_frame.setGeometry(360, 160, 1340, 780)
        self.content_layout = QHBoxLayout()
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        self.content_frame.setLayout(self.content_layout)

        # Middle Left video place
        self.video_frame = QFrame()
        self.video_frame.setStyleSheet("background-color: black")
        self.video_frame_width = 1280
        self.video_frame_height = 720
        self.video_frame.setFixedSize(self.video_frame_width, self.video_frame_height)

        self.video_frame_layout = QVBoxLayout()
        self.video_frame_layout.setAlignment(Qt.AlignCenter)
        self.video_frame_layout.setContentsMargins(0, 0, 0, 0)
        self.video_frame.setLayout(self.video_frame_layout)

        self.video_label = ClickableLabel(self)
        self.video_label.setStyleSheet("background-color: black;")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setFixedSize(self.video_frame_width, self.video_frame_height)
        self.video_label.clicked.connect(self.on_video_click)
        self.video_label.region_selected.connect(self.on_region_selected)
        self.video_frame_layout.addWidget(self.video_label)
        
        self.content_layout.addWidget(self.video_frame)

        # Middle Right
        self.action_frame = QFrame(self)
        self.action_frame.setStyleSheet("background-color: #34495E")
        self.action_frame.setGeometry(1730, 160, 300, 780)
        self.action_layout = QVBoxLayout()
        self.action_layout.setAlignment(Qt.AlignCenter)
        self.action_frame.setLayout(self.action_layout)
        self.create_action_buttons()

        # Bottom
        self.control_frame = QFrame(self)
        self.control_frame.setStyleSheet("background-color: #34495E")
        self.control_frame.setGeometry(360, 970, 1670, 100)
        self.control_layout = QHBoxLayout()
        self.control_layout.setSpacing(20)
        self.control_frame.setLayout(self.control_layout)
        self.create_control_buttons()

        # Timer to update object table
        self.update_objects_timer = QTimer()
        self.update_objects_timer.timeout.connect(self.update_object_table)
        self.update_objects_timer.start(500)  # Update every 500 ms

    def center_window(self):
        frame_geometry = self.frameGeometry()
        screen = QApplication.primaryScreen()
        center_point = screen.availableGeometry().center()
        frame_geometry.moveCenter(center_point)
        self.move(frame_geometry.topLeft())

    def create_action_buttons(self):
        button_specs = [
            ("Select Object", self.event_handlers.select_object, "#2980B9"),
            ("Select Region", self.event_handlers.select_region, "#2980B9"),
            ("Mark as Adversary", self.event_handlers.mark_adversary, "#C0392B"),
            ("Reset Status", self.event_handlers.reset_status, "#7F8C8D"),
            ("Mark as Friend", self.event_handlers.mark_friend, "#27AE60"),
        ]

        self.action_layout.setSpacing(20)

        for text, command, color in button_specs:
            btn = QPushButton(text)
            btn.clicked.connect(command)
            btn.setFixedSize(200, 50)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color};
                    color: white;
                    border: none;
                    border-radius: 25px;
                }}
                QPushButton:hover {{
                    background-color: {self.lighten_color(color, 20)};
                }}
                QPushButton:pressed {{
                    background-color: {self.darken_color(color, 20)};
                }}
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
            elif text == "Reset Status":
                self.reset_status_button = btn
                self.reset_status_button.setEnabled(False)

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
                QPushButton {{
                    background-color: {color};
                    color: white;
                    border: none;
                    border-radius: 25px;
                }}
                QPushButton:hover {{
                    background-color: {self.lighten_color(color, 20)};
                }}
                QPushButton:pressed {{
                    background-color: {self.darken_color(color, 20)};
                }}
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

    def lighten_color(self, color, amount):
        color = color.lstrip('#')
        r, g, b = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
        r = min(255, r + amount)
        g = min(255, g + amount)
        b = min(255, b + amount)
        return f'#{r:02X}{g:02X}{b:02X}'

    def darken_color(self, color, amount):
        color = color.lstrip('#')
        r, g, b = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
        r = max(0, r - amount)
        g = max(0, g - amount)
        b = max(0, b - amount)
        return f'#{r:02X}{g:02X}{b:02X}'

    def on_video_click(self, event):
        if self.selecting_object:
            x_click = event.pos().x()
            y_click = event.pos().y()
            tracked_objects = self.video_processor.current_tracked_objects
            object_selected = False

            # Clear existing selections
            for track_id in self.object_statuses.keys():
                self.object_statuses[track_id]['selected'] = False

            self.selected_object_ids = []

            for obj in tracked_objects:
                x1, y1, x2, y2 = map(int, obj['bbox'])
                track_id = obj['track_id']

                if x1 <= x_click <= x2 and y1 <= y_click <= y2:
                    track_id = str(obj['track_id'])
                    if track_id not in self.object_statuses:
                        self.object_statuses[track_id] = {'status': None, 'selected': False, 'threat_level': 1.0}
                    self.object_statuses[track_id]['selected'] = True
                    self.selected_object_ids.append(track_id)
                    print(f"Object {track_id} selected.")
                    object_selected = True
                    break

            if object_selected:
                if hasattr(self, 'mark_friend_button') and hasattr(self, 'mark_adversary_button') and hasattr(self, 'reset_status_button'):
                    self.mark_friend_button.setEnabled(True)
                    self.mark_adversary_button.setEnabled(True)
                    self.reset_status_button.setEnabled(True)
            else:
                if hasattr(self, 'mark_friend_button') and hasattr(self, 'mark_adversary_button') and hasattr(self, 'reset_status_button'):
                    self.mark_friend_button.setEnabled(False)
                    self.mark_adversary_button.setEnabled(False)
                    self.reset_status_button.setEnabled(False)
                print("No object selected.")

            self.video_processor.refresh_video_display()
            self.update_object_table()

    def on_region_selected(self, region):
        if self.selecting_region:
            x1, y1, x2, y2 = region

            # Clear existing selections
            for track_id in self.object_statuses.keys():
                self.object_statuses[track_id]['selected'] = False

            self.selected_object_ids = []

            # Find objects within the selected region
            tracked_objects = self.video_processor.current_tracked_objects
            objects_selected = False

            for obj in tracked_objects:
                track_id = str(obj['track_id'])
                obj_x1, obj_y1, obj_x2, obj_y2 = obj['bbox']

                if not (x2 < obj_x1 or x1 > obj_x2 or y2 < obj_y1 or y1 > obj_y2):
                    if track_id not in self.object_statuses:
                        self.object_statuses[track_id] = {'status': None, 'selected': False, 'threat_level': 1.0}
                    self.object_statuses[track_id]['selected'] = True
                    self.selected_object_ids.append(track_id)
                    print(f"Object {track_id} selected in region.")
                    objects_selected = True

            if objects_selected:
                if hasattr(self, 'mark_friend_button') and hasattr(self, 'mark_adversary_button') and hasattr(self, 'reset_status_button'):
                    self.mark_friend_button.setEnabled(True)
                    self.mark_adversary_button.setEnabled(True)
                    self.reset_status_button.setEnabled(True)
            else:
                if hasattr(self, 'mark_friend_button') and hasattr(self, 'mark_adversary_button') and hasattr(self, 'reset_status_button'):
                    self.mark_friend_button.setEnabled(False)
                    self.mark_adversary_button.setEnabled(False)
                    self.reset_status_button.setEnabled(False)
                print("No objects found in the selected region.")

            self.selecting_region = True
            self.video_processor.refresh_video_display()
            self.update_object_table()

    def update_object_table(self):
        tracked_objects = self.video_processor.current_tracked_objects
        self.object_table.setRowCount(len(tracked_objects))

        for row, obj in enumerate(tracked_objects):
            track_id = str(obj['track_id'])
            cls = obj['cls']
            
            # Add object to object_statuses if not present
            if track_id not in self.object_statuses:
                self.object_statuses[track_id] = {
                    'status': 'Unknown', 
                    'selected': False, 
                    'threat_level': 1.0
                }

            status = self.object_statuses[track_id]['status']
            threat = self.object_statuses[track_id]['threat_level']
            is_selected = self.object_statuses[track_id]['selected']

            # Create table items
            id_item = QTableWidgetItem(track_id)
            type_item = QTableWidgetItem(cls)
            status_item = QTableWidgetItem(status if status else "Unknown")
            threat_item = QTableWidgetItem(str(int(threat)))

            # Set items in the table
            self.object_table.setItem(row, 0, id_item)
            self.object_table.setItem(row, 1, type_item)
            self.object_table.setItem(row, 2, status_item)
            self.object_table.setItem(row, 3, threat_item)

            # Determine row background color
            if is_selected:
                background_color = QColor('#FFA500')  # Orange for selected
            else:
                if status == "adversary":
                    background_color = QColor('#C0392B')  # Red
                elif status == "friend":
                    background_color = QColor('#27AE60')  # Green
                else:
                    background_color = QColor('#2C3E50')  # Default

            # Apply background color to all columns in the row
            for column in range(self.object_table.columnCount()):
                item = self.object_table.item(row, column)
                if item:
                    item.setBackground(QBrush(background_color))

                    if is_selected:
                        font = item.font()
                        font.setBold(True)
                        item.setFont(font)
                    else:
                        font = item.font()
                        font.setBold(False)
                        item.setFont(font)

    def on_object_table_click(self, row, column):
        track_id_item = self.object_table.item(row, 0)
        if track_id_item:
            track_id = int(track_id_item.text())
            self.select_object_by_id(track_id)

    def select_object_by_id(self, track_id):
        track_id = str(track_id)
        # Deselect all objects
        for tid in self.object_statuses.keys():
            self.object_statuses[tid]['selected'] = False

        # Select the chosen object
        if track_id in self.object_statuses:
            self.object_statuses[track_id]['selected'] = True
        else:
            self.object_statuses[track_id] = {'status': None, 'selected': True, 'threat_level': 1.0}

        self.selected_object_ids = [track_id]

        # Enable buttons
        if hasattr(self, 'mark_friend_button') and hasattr(self, 'mark_adversary_button') and hasattr(self, 'reset_status_button'):
            self.mark_friend_button.setEnabled(True)
            self.mark_adversary_button.setEnabled(True)
            self.reset_status_button.setEnabled(True)

        # Update table
        self.update_object_table()

        # Refresh video display
        self.video_processor.refresh_video_display()

    def clear_selections(self):
        # Clear selected flags
        for track_id in self.object_statuses.keys():
            self.object_statuses[track_id]['selected'] = False

        # Clear selected object IDs
        self.selected_object_ids = []

        # Disable action buttons
        if hasattr(self, 'mark_friend_button') and hasattr(self, 'mark_adversary_button') and hasattr(self, 'reset_status_button'):
            self.mark_friend_button.setEnabled(False)
            self.mark_adversary_button.setEnabled(False)
            self.reset_status_button.setEnabled(False)

        # Clear table selection
        self.object_table.clearSelection()

        # Update the UI
        self.update_object_table()
        self.video_processor.refresh_video_display()

    def reset_app_state(self):
        self.object_statuses.clear()
        self.selected_object_ids.clear()
        self.video_processor.stop_processing_frames()
        self.video_processor = VideoProcessor(self)
        self.current_frame = 0
        self.playing = False
        self.cap = None
        self.video_path = ""
        self.video_info_label.setText("No video selected.")
        self.video_label.clear()
        self.object_table.setRowCount(0)
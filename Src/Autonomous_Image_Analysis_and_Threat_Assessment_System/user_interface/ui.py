# user_interface/ui.py
from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QFrame, QVBoxLayout, QHBoxLayout,
    QApplication, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt5.QtGui import QFont, QMouseEvent, QPainter, QPen, QBrush, QColor, QIcon
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QSize

from project_utils.config import SCALE
from threat_assessment.manager import ThreatAssessment
from user_interface.event_handlers import EventHandlers
from process_operations.video_processor import VideoProcessor
from object_detection.object_detector import ObjectDetector

import math


class ClickableLabel(QLabel):
    clicked = pyqtSignal(QMouseEvent)
    region_selected = pyqtSignal(object)

    def __init__(self, parent_app, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parent_app = parent_app
        self.start_point = None
        self.end_point = None
        self.drawing = False
        self.current_rect = None

    def mousePressEvent(self, event):
        if (self.parent_app.selecting_region or
                self.parent_app.selecting_friendly_zone or
                self.parent_app.selecting_enemy_zone):
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
            self.region_selected.emit(
                (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
            )
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
            painter.drawRect(min(x1, x2), min(y1, y2),
                             abs(x2 - x1), abs(y2 - y1))


class Application(QWidget):
    def __init__(self):
        super().__init__()

        # ───────── Ölçek faktörü ─────────
        self.SCALE = SCALE
        s = self.SCALE

        # Video çerçeve boyutları
        self.video_frame_width  = (int(1600 * s) // 32) * 32
        self.video_frame_height = (int(896  * s) // 32) * 32

        # Object detection and processing
        self.object_detector = ObjectDetector()
        self.video_processor = VideoProcessor(
            self,
            display_width=self.video_frame_width,
            display_height=self.video_frame_height
        )
        self.threat_assessment = ThreatAssessment()
        self.event_handlers = EventHandlers(self)

        # State
        self.playing = False
        self.video_path = ""
        self.cap = None
        self.fps = 0
        self.current_frame = 0
        self.object_statuses = {}
        self.selected_object_ids = []
        self.selecting_object = False
        self.selecting_region = False

        # Dost-düşman bölgeler
        self.friendly_zones = []
        self.enemy_zones = []
        self.selecting_friendly_zone = False
        self.selecting_enemy_zone = False

        # UI setup
        self.setWindowTitle("System User Interface")
        self.setStyleSheet("background-color: #1F2224;")
        self.default_font = QFont("Helvetica", max(int(12 * s), 8))

        self.window_width  = int(2260 * s)
        self.window_height = int(1200 * s)

        self.setFixedSize(self.window_width, self.window_height)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(10)

        # Sistem Adı
        self.system_name_outer = QFrame()
        self.system_name_outer.setStyleSheet(
            "background-color: #2A2F33; border-radius: 10px;"
        )
        self.system_name_outer.setFixedHeight(int(70 * s))
        system_name_outer_layout = QVBoxLayout()
        system_name_outer_layout.setContentsMargins(10, 10, 10, 10)
        system_name_outer_layout.setSpacing(0)
        self.system_name_outer.setLayout(system_name_outer_layout)

        self.system_name_inner = QFrame()
        self.system_name_inner.setStyleSheet(
            "background-color: #393E40; border-radius: 10px;"
        )
        self.system_name_inner.setFixedHeight(int(50 * s))
        system_name_inner_layout = QHBoxLayout()
        system_name_inner_layout.setContentsMargins(10, 10, 10, 10)
        system_name_inner_layout.setAlignment(Qt.AlignCenter)
        self.system_name_inner.setLayout(system_name_inner_layout)

        self.system_name_label = QLabel(
            "Autonomous Image Analysis and Threat Assessment System"
        )
        self.system_name_label.setStyleSheet("color: white;")
        self.system_name_label.setFont(
            QFont("Helvetica", max(int(16 * s), 10), QFont.Bold)
        )
        system_name_inner_layout.addWidget(self.system_name_label)
        system_name_outer_layout.addWidget(self.system_name_inner)
        main_layout.addWidget(self.system_name_outer)

        # İçerik
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(int(50 * s))
        main_layout.addLayout(content_layout)

        # Sol Panel
        self.left_panel1 = QFrame()
        self.left_panel1.setStyleSheet(
            "background-color: #2A2F33; border-radius: 10px;"
        )
        self.left_panel1.setFixedWidth(int(500 * s))
        left_panel_layout = QVBoxLayout()
        left_panel_layout.setContentsMargins(10, 10, 10, 10)
        left_panel_layout.setSpacing(10)
        self.left_panel1.setLayout(left_panel_layout)

        self.object_table = QTableWidget()
        self.object_table.setColumnCount(4)
        self.object_table.setHorizontalHeaderLabels(["ID", "Type", "Status", "Threat"])
        header = self.object_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # ID
        header.setSectionResizeMode(1, QHeaderView.Interactive)       # Type
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Status
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Threat

        # Type sütunu için minimum genişlik
        header.setMinimumSectionSize(95)
        self.object_table.setColumnWidth(1, 195)  # Type sütunu genişliği


        self.object_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.object_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.object_table.setSelectionMode(QTableWidget.SingleSelection)
        self.object_table.verticalHeader().setVisible(False)
        self.object_table.setStyleSheet("""
            QTableWidget { background-color: #393E40; color: white; border: none; }
            QHeaderView::section { background-color: #2B2E30; color: white; font-weight: bold; }
            QTableWidget::item:selected { background-color: #FFA500; color: white; }
            QTableWidget::item:hover { background-color: #4D4D4D; color: white; }
        """)
        self.object_table.cellClicked.connect(self.on_object_table_click)
        left_panel_layout.addWidget(self.object_table)
        content_layout.addWidget(self.left_panel1)

        # Sağ Panel
        self.right_panel_outer = QFrame()
        self.right_panel_outer.setStyleSheet(
            "background-color: #2A2F33; border-radius: 10px;"
        )
        right_panel_outer_layout = QVBoxLayout()
        right_panel_outer_layout.setContentsMargins(10, 10, 10, 10)
        right_panel_outer_layout.setSpacing(10)
        self.right_panel_outer.setLayout(right_panel_outer_layout)

        self.right_panel_inner = QFrame()
        self.right_panel_inner.setStyleSheet(
            "background-color: #393E40; border-radius: 10px;"
        )
        right_panel_inner_layout = QVBoxLayout()
        right_panel_inner_layout.setContentsMargins(10, 10, 10, 10)
        right_panel_inner_layout.setSpacing(10)
        self.right_panel_inner.setLayout(right_panel_inner_layout)

        # Video Görüntüleme
        self.video_frame = QFrame()
        self.video_frame.setStyleSheet("background-color: black; border-radius: 0px;")
        self.video_frame.setFixedSize(
            self.video_frame_width, self.video_frame_height
        )
        video_frame_layout = QVBoxLayout()
        video_frame_layout.setAlignment(Qt.AlignCenter)
        video_frame_layout.setContentsMargins(0, 0, 0, 0)
        self.video_frame.setLayout(video_frame_layout)

        self.video_label = ClickableLabel(self)
        self.video_label.setStyleSheet("background-color: black;")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setFixedSize(
            self.video_frame_width, self.video_frame_height
        )
        self.video_label.clicked.connect(self.on_video_click)
        self.video_label.region_selected.connect(self.on_region_selected)
        video_frame_layout.addWidget(self.video_label)
        right_panel_inner_layout.addWidget(self.video_frame, alignment=Qt.AlignCenter)

        # Spacer
        spacer = QFrame()
        spacer.setFixedHeight(int(40 * s))
        right_panel_inner_layout.addWidget(spacer)

        # Butonlar (Action + Control)
        action_icons = [
            ("others\\Select_Object.png", self.event_handlers.select_object),
            ("others\\Select_Region.png", self.event_handlers.select_region),
            ("others\\Mark_Foe.png", self.event_handlers.mark_foe),
            ("others\\Reset_Status.png", self.event_handlers.reset_status),
            ("others\\Mark_Friend.png", self.event_handlers.mark_friend)
        ]
        control_icons = [
            ("others\\Friendly_Zone.png", self.event_handlers.select_friendly_zone),
            ("others\\Enemy_Zone.png", self.event_handlers.select_enemy_zone),
            ("others\\Clear_Zones.png", self.event_handlers.clear_zones),
            ("others\\Select_Theater.png", self.event_handlers.open_video),
            ("others\\Play.png", self.event_handlers.resume_video),
            ("others\\Pause.png", self.event_handlers.pause_video),
            ("others\\Exit.png", self.event_handlers.quit_app)
            # , ("others\\Calculate_Distance.png", self.event_handlers.calculate_distance_between_selected)
        ]
        self.buttons_frame = QFrame()
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        self.buttons_frame.setLayout(buttons_layout)

        btn_size = int(100 * s)
        for icon_path, command in action_icons + control_icons:
            btn = QPushButton()
            btn.clicked.connect(command)
            btn.setFixedSize(btn_size, btn_size)
            btn.setFlat(True)
            btn.setStyleSheet("border: none; background: transparent;")
            btn.setIcon(QIcon(icon_path))
            btn.setIconSize(QSize(btn_size, btn_size))
            btn.setCursor(Qt.PointingHandCursor)
            buttons_layout.addWidget(btn)

        right_panel_inner_layout.addWidget(self.buttons_frame)
        right_panel_outer_layout.addWidget(self.right_panel_inner)
        content_layout.addWidget(self.right_panel_outer)

        main_layout.addLayout(content_layout)

        # Periyodik tablo güncellemesi
        self.update_objects_timer = QTimer()
        self.update_objects_timer.timeout.connect(self.update_object_table)
        self.update_objects_timer.start(500)

    def showEvent(self, event):
        super().showEvent(event)
        self.center_window()

    def center_window(self):
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        screen_width = screen_geometry.width()
        screen_height = screen_geometry.height()
        x = (screen_width - self.window_width) // 2
        y = (screen_height - self.window_height) // 2
        self.move(x, y)

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

            # Seçimleri temizle
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
                if hasattr(self, 'mark_friend_button') and hasattr(self, 'mark_foe_button') and hasattr(self, 'reset_status_button'):
                    self.mark_friend_button.setEnabled(True)
                    self.mark_foe_button.setEnabled(True)
                    self.reset_status_button.setEnabled(True)
            else:
                if hasattr(self, 'mark_friend_button') and hasattr(self, 'mark_foe_button') and hasattr(self, 'reset_status_button'):
                    self.mark_friend_button.setEnabled(False)
                    self.mark_foe_button.setEnabled(False)
                    self.reset_status_button.setEnabled(False)
                print("No object selected.")

            self.video_processor.refresh_video_display()
            self.update_object_table()

    def on_region_selected(self, region):
        if self.selecting_friendly_zone or self.selecting_enemy_zone:
            x1, y1, x2, y2 = region
            if self.selecting_friendly_zone:
                self.friendly_zones.append((x1, y1, x2, y2))
                print(f"Friendly zone added: {(x1, y1, x2, y2)}")
            elif self.selecting_enemy_zone:
                self.enemy_zones.append((x1, y1, x2, y2))
                print(f"Enemy zone added: {(x1, y1, x2, y2)}")
            self.selecting_friendly_zone = False
            self.selecting_enemy_zone = False
            self.video_processor.refresh_video_display()
            
            # 1) Bölgelere göre statü ata + tehditleri güncelle
            self.assign_status_based_on_zones()
            # 2) Tabloyu ve video ekranını yenile
            self.update_object_table()
            self.video_processor.refresh_video_display()

            return

        if self.selecting_region:
            x1, y1, x2, y2 = region

            # Seçimleri temizle
            for track_id in self.object_statuses.keys():
                self.object_statuses[track_id]['selected'] = False

            self.selected_object_ids = []

            tracked_objects = self.video_processor.current_tracked_objects
            objects_selected = False

            for obj in tracked_objects:
                track_id = str(obj['track_id'])
                obj_x1, obj_y1, obj_x2, obj_y2 = obj['bbox']
                # Dikdörtgen kesişim kontrolü
                if not (x2 < obj_x1 or x1 > obj_x2 or y2 < obj_y1 or y1 > obj_y2):
                    if track_id not in self.object_statuses:
                        self.object_statuses[track_id] = {'status': None, 'selected': False, 'threat_level': 1.0}
                    self.object_statuses[track_id]['selected'] = True
                    self.selected_object_ids.append(track_id)
                    print(f"Object {track_id} selected in region.")
                    objects_selected = True

            if objects_selected:
                if hasattr(self, 'mark_friend_button') and hasattr(self, 'mark_foe_button') and hasattr(self, 'reset_status_button'):
                    self.mark_friend_button.setEnabled(True)
                    self.mark_foe_button.setEnabled(True)
                    self.reset_status_button.setEnabled(True)
            else:
                if hasattr(self, 'mark_friend_button') and hasattr(self, 'mark_foe_button') and hasattr(self, 'reset_status_button'):
                    self.mark_friend_button.setEnabled(False)
                    self.mark_foe_button.setEnabled(False)
                    self.reset_status_button.setEnabled(False)
                print("No objects found in the selected region.")

            self.selecting_region = True
            self.video_processor.refresh_video_display()
            self.update_object_table()

    def update_object_table(self):
        """
        Tabloyu ve object_statuses sözlüğünü senkronize tutar.
        Yeni bir nesne ilk kez görülürse:
        ▸ statü = unknown
        ▸ taban tehdit = sınıf katsayısı (bulunamazsa Unknown katsayısı)
        """
        tracked_objects = self.video_processor.current_tracked_objects
        self.object_table.setRowCount(len(tracked_objects))

        for row, obj in enumerate(tracked_objects):
            track_id = str(obj['track_id'])
            cls      = obj['cls'].strip()          # ‼️ boşluk/küçük farkları at
            base_thr = self.threat_assessment.threat_coefficients.get(cls, 1)

            # object_statuses’e ekle / güncelle (ilk girişse)
            if track_id not in self.object_statuses:
                self.object_statuses[track_id] = {
                    'status'      : 'unknown',
                    'selected'    : False,
                    'threat_level': base_thr,
                }

            status      = self.object_statuses[track_id]['status']
            threat_lvl  = self.object_statuses[track_id]['threat_level']
            is_selected = self.object_statuses[track_id]['selected']

            # ─────────── tablo hücreleri ───────────
            self.object_table.setItem(row, 0, QTableWidgetItem(track_id))
            self.object_table.setItem(row, 1, QTableWidgetItem(cls))
            self.object_table.setItem(row, 2, QTableWidgetItem(status.capitalize()))
            self.object_table.setItem(row, 3, QTableWidgetItem(str(int(threat_lvl))))

            # Satır arka planı
            if is_selected:
                bg = QColor('#FFA500')          # turuncu
            elif status == "foe":
                bg = QColor('#C0392B')          # kırmızı
            elif status == "friend":
                bg = QColor('#27AE60')          # yeşil
            else:
                bg = QColor('#2C2F33')          # varsayılan

            for col in range(self.object_table.columnCount()):
                item = self.object_table.item(row, col)
                if item:
                    item.setBackground(QBrush(bg))
                    f = item.font()
                    f.setBold(is_selected)
                    item.setFont(f)




    def on_object_table_click(self, row, column):
        track_id_item = self.object_table.item(row, 0)
        if track_id_item:
            track_id = int(track_id_item.text())
            self.select_object_by_id(track_id)

    def select_object_by_id(self, track_id):
        track_id = str(track_id)
        for tid in self.object_statuses.keys():
            self.object_statuses[tid]['selected'] = False

        if track_id in self.object_statuses:
            self.object_statuses[track_id]['selected'] = True
        else:
            self.object_statuses[track_id] = {'status': None, 'selected': True, 'threat_level': 1.0}

        self.selected_object_ids = [track_id]

        if hasattr(self, 'mark_friend_button') and hasattr(self, 'mark_foe_button') and hasattr(self, 'reset_status_button'):
            self.mark_friend_button.setEnabled(True)
            self.mark_foe_button.setEnabled(True)
            self.reset_status_button.setEnabled(True)

        self.update_object_table()
        self.video_processor.refresh_video_display()

    def clear_selections(self):
        for track_id in self.object_statuses.keys():
            self.object_statuses[track_id]['selected'] = False

        self.selected_object_ids = []

        if hasattr(self, 'mark_friend_button') and hasattr(self, 'mark_foe_button') and hasattr(self, 'reset_status_button'):
            self.mark_friend_button.setEnabled(False)
            self.mark_foe_button.setEnabled(False)
            self.reset_status_button.setEnabled(False)

        self.object_table.clearSelection()
        self.update_object_table()
        self.video_processor.refresh_video_display()

    def reset_app_state(self):
        self.friendly_zones.clear()
        self.enemy_zones.clear()
        self.selecting_friendly_zone = False
        self.selecting_enemy_zone = False
        self.object_statuses.clear()
        self.selected_object_ids.clear()
        self.video_processor.stop_processing_frames()
        self.video_processor = VideoProcessor(self, display_width=self.video_frame_width, display_height=self.video_frame_height)
        self.current_frame = 0
        self.playing = False
        self.cap = None
        self.video_path = ""
        self.video_label.clear()
        self.object_table.setRowCount(0)

    def assign_status_based_on_zones(self):
            """
            • Her kare sonunda VideoProcessor çağırır.
            • Bölgelere göre friend / foe / unknown statüsü atar.
            • Ardından tehdit değerlerini HEMEN yeniden hesaplar.
            """
            for obj in self.video_processor.current_tracked_objects:
                tid = str(obj['track_id'])

                # Varsayılan tablo girişi oluştur
                if tid not in self.object_statuses:
                    # Sınıfa göre taban katsayıyı al (bulunamazsa Unknown)
                    base_threat = self.threat_assessment.threat_coefficients.get(
                        obj['cls'].strip(), 1
                    )
                    self.object_statuses[tid] = {
                        'status'      : "unknown",
                        'selected'    : False,
                        'threat_level': base_threat,
                    }

                # Elle friend / foe seçildiyse değiştirme
                if self.object_statuses[tid]['status'] in ("friend", "foe"):
                    continue

                # Bölge testleri
                x1, y1, x2, y2 = obj['bbox']
                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

                in_friend = any(fx1 <= cx <= fx2 and fy1 <= cy <= fy2
                                for fx1, fy1, fx2, fy2 in self.friendly_zones)
                in_enemy  = any(ex1 <= cx <= ex2 and ey1 <= cy <= ey2
                                for ex1, ey1, ex2, ey2 in self.enemy_zones)

                if in_friend:
                    self.object_statuses[tid]['status'] = "friend"
                elif in_enemy:
                    self.object_statuses[tid]['status'] = "foe"
                else:
                    self.object_statuses[tid]['status'] = "unknown"

            # ► Statüler güncellendi → hemen tehditleri yeniden hesapla
            self.threat_assessment.perform_threat_assessment(self)

            # Ekranı yenile
            self.update_object_table()
            self.video_processor.refresh_video_display()
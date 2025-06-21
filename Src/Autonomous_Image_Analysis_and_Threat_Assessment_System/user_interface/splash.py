# user_interface/splash.py
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QPushButton, QLabel,
    QApplication, QSpacerItem, QSizePolicy, QHBoxLayout, QFrame
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QPixmap
from project_utils.config import SCALE
from user_interface.ui import Application


class SplashScreen(QMainWindow):
    def __init__(self):
        super().__init__()

        # ───────── Ölçek faktörü ─────────
        self.SCALE = SCALE
        s = self.SCALE               # kısaltma

        # Pencere boyutu
        self.window_width  = int(2260 * s)
        self.window_height = int(1200 * s)
        self.setFixedSize(self.window_width, self.window_height)
        self.setWindowTitle("Detect System")

        # Arka plan rengi
        self.setStyleSheet("background-color: #1F2224;")

        self.main_window  = None
        self.initialized  = False

        # ───────── Merkez widget + layout ─────────
        self.central_widget  = QWidget()
        self.setCentralWidget(self.central_widget)
        self.central_layout  = QVBoxLayout(self.central_widget)
        self.central_layout.setContentsMargins(20, 20, 20, 20)

        # ───────── Konteyner çerçevesi ─────────
        self.container_frame = QFrame()
        self.container_frame.setStyleSheet(f"""
            background-color: #1F2224;
            border-radius: {int(20 * s)}px;
        """)
        self.central_layout.addWidget(self.container_frame)

        self.layout = QVBoxLayout(self.container_frame)
        self.layout.setAlignment(Qt.AlignCenter)

        # Spacer (üst)
        self.layout.addSpacerItem(
            QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding)
        )

        # ───────── Daire içindeki logo ─────────
        self.circle_label = QLabel()
        circle_size = int(800 * s)
        self.circle_label.setFixedSize(circle_size, circle_size)
        self.circle_label.setStyleSheet(f"""
            background-color: #0B0F11;
            border-radius: {circle_size // 2}px;
        """)
        self.circle_label.setAlignment(Qt.AlignCenter)

        pixmap = QPixmap("others\\SYSTEM.png")
        pixmap_size = int(600 * s)
        scaled_pixmap = pixmap.scaled(
            pixmap_size, pixmap_size,
            Qt.IgnoreAspectRatio, Qt.SmoothTransformation
        )
        self.circle_label.setPixmap(scaled_pixmap)
        self.layout.addWidget(self.circle_label, alignment=Qt.AlignHCenter)

        # Spacer (logo ile buton arası)
        self.layout.addSpacing(int(100 * s))

        # ───────── START butonu ─────────
        self.start_button = QPushButton("START")
        self.start_button.setFixedSize(int(250 * s), int(60 * s))
        self.start_button.setCursor(Qt.PointingHandCursor)
        self.start_button.setFont(QFont("Arial", max(int(16 * s), 9), QFont.Bold))
        radius = int(30 * s)
        self.start_button.setStyleSheet(f"""
            QPushButton {{
                background-color: #BBD8E5;
                color: #1D2B36;
                border: none;
                border-radius: {radius}px;
            }}
            QPushButton:hover {{
                background-color: #CBE3EF;
            }}
        """)
        self.start_button.clicked.connect(self.start_app)
        self.layout.addWidget(self.start_button, alignment=Qt.AlignHCenter)

        # Spacer (alt)
        self.layout.addSpacerItem(
            QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding)
        )

        # ───────── Footer bilgisi ─────────
        self.footer_layout = QHBoxLayout()
        self.footer_layout.addSpacerItem(
            QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum)
        )
        self.footer_label = QLabel(
            "<div style='color: #AAAAAA; text-align: right;'>"
            "<p>Developed by <b>Furkan, Beyza, Burhan</b></p>"
            "<p>Version <b>1.0.0</b></p>"
            "<p>© 2025 All Rights Reserved</p>"
            "</div>"
        )
        self.footer_label.setStyleSheet("color: #AAAAAA;")
        self.footer_label.setAlignment(Qt.AlignRight | Qt.AlignBottom)
        self.footer_layout.addWidget(self.footer_label)
        self.layout.addLayout(self.footer_layout)

        # ───────── Timer ─────────
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.launch_main_app)

    # ------------------------------------------------------------------ #
    #                    Event & yardımcı metotlar                       #
    # ------------------------------------------------------------------ #
    def showEvent(self, event):
        super().showEvent(event)
        self.center_window()

    def center_window(self):
        screen = QApplication.primaryScreen().availableGeometry()
        x = (screen.width()  - self.window_width)  // 2
        y = (screen.height() - self.window_height) // 2
        self.move(x, y)

    def start_app(self):
        self.start_button.setText("Loading...")
        self.start_button.setEnabled(False)
        self.timer.start(800)

    def launch_main_app(self):
        self.main_window = Application()
        self.main_window.show()
        self.close()

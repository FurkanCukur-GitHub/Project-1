# user_interface/splash.py
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QPushButton, QLabel,
    QApplication, QSpacerItem, QSizePolicy, QHBoxLayout, QFrame
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QPixmap
from user_interface.ui import Application


class SplashScreen(QMainWindow):
    def __init__(self):
        super().__init__()
        self.window_width = 2060
        self.window_height = 1200
        self.setFixedSize(self.window_width, self.window_height)
        self.setWindowTitle("Detect System")

        # Make the entire QMainWindow background match the dark color
        self.setStyleSheet("background-color: #1F2224;")

        self.main_window = None
        self.initialized = False

        # Central widget + layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.central_layout = QVBoxLayout(self.central_widget)
        # You can tweak these margins or set them to zero if you want no padding at all
        self.central_layout.setContentsMargins(20, 20, 20, 20)

        # Container frame (removed the "border" property, kept border-radius if you want curved corners)
        self.container_frame = QFrame()
        self.container_frame.setStyleSheet("""
            background-color: #1F2224;
            border-radius: 20px;
        """)
        self.central_layout.addWidget(self.container_frame)

        # Layout inside container frame
        self.layout = QVBoxLayout(self.container_frame)
        self.layout.setAlignment(Qt.AlignCenter)

        # Spacer at the top
        self.layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # Circle label with an image inside
        self.circle_label = QLabel()
        self.circle_label.setFixedSize(800, 800)
        self.circle_label.setStyleSheet("""
            background-color: #0B0F11;
            border-radius: 400px;
        """)
        self.circle_label.setAlignment(Qt.AlignCenter)

        pixmap = QPixmap("others\\SYSTEM.png")
        scaled_pixmap = pixmap.scaled(600, 600, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        self.circle_label.setPixmap(scaled_pixmap)
        self.layout.addWidget(self.circle_label, alignment=Qt.AlignHCenter)

        # Spacer before the button
        self.layout.addSpacing(100)

        # Start button
        self.start_button = QPushButton("START")
        self.start_button.setFixedSize(250, 60)
        self.start_button.setCursor(Qt.PointingHandCursor)
        self.start_button.setFont(QFont("Arial", 16, QFont.Bold))
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #BBD8E5;
                color: #1D2B36;
                border: none;
                border-radius: 30px;
            }
            QPushButton:hover {
                background-color: #CBE3EF;
            }
        """)
        self.start_button.clicked.connect(self.start_app)
        self.layout.addWidget(self.start_button, alignment=Qt.AlignHCenter)

        # Spacer at the bottom
        self.layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # Footer info (bottom-right corner)
        self.footer_layout = QHBoxLayout()
        self.footer_layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum))
        self.footer_label = QLabel()
        self.footer_label.setText(
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

        # Timer for delayed launch
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.launch_main_app)

    def showEvent(self, event):
        super().showEvent(event)
        self.center_window()

    def center_window(self):
        screen = QApplication.primaryScreen().availableGeometry()
        x = (screen.width() - self.window_width) // 2
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

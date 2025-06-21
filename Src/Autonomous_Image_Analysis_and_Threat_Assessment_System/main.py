# main.py
import sys
import warnings
import os
from PyQt5.QtWidgets import QApplication
from user_interface.splash import SplashScreen

warnings.filterwarnings("ignore", category=RuntimeWarning)
os.environ["QT_LOGGING_RULES"] = "*.debug=false"

def main():
    app = QApplication(sys.argv)
    splash = SplashScreen()
    splash.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
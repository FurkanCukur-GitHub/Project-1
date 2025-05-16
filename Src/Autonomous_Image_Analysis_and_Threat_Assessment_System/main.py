# main.py
import sys
from PyQt5.QtWidgets import QApplication
from user_interface.splash import SplashScreen

def main():
    app = QApplication(sys.argv)

    splash = SplashScreen()
    splash.show()

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()

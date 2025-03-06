# main.py
from PyQt5.QtWidgets import QApplication
from user_interface.ui import Application
import sys

def main():
    app = QApplication(sys.argv)
    window = Application()
    window.show()
    result = app.exec_()
    sys.exit(result)

if __name__ == "__main__":
    main()
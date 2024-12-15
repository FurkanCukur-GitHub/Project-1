# main.py
from PyQt5.QtWidgets import QApplication
from user_interface.ui import Application
import sys
import cProfile
import pstats

def main():
    # Uncomment to profile the application
    # profiler = cProfile.Profile()
    # profiler.enable()

    app = QApplication(sys.argv)
    window = Application()
    window.show()
    result = app.exec_()

    # profiler.disable()
    # with open("profile_stats.txt", "w") as f:
    #     stats = pstats.Stats(profiler, stream=f)
    #     stats.strip_dirs()
    #     stats.sort_stats("cumulative")
    #     stats.print_stats()

    sys.exit(result)

if __name__ == "__main__":
    main()
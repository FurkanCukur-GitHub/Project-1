# main.py
from PyQt5.QtWidgets import QApplication
from user_interface.ui import Application
import sys
import cProfile
import pstats

def main():
    # profiler = cProfile.Profile()
    # profiler.enable()

    app = QApplication(sys.argv)
    window = Application()
    window.show()
    result = app.exec_()

    # profiler.disable()
    # stats = pstats.Stats(profiler).sort_stats('cumtime')
    # stats.print_stats(10)  # Prints the top 10 functions with the most cumulative time

    sys.exit(result)

if __name__ == "__main__":
    main()

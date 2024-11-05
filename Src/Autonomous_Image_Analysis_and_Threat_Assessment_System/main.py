# main.py
import tkinter as tk
from user_interface.ui import Application

def main():
    root = tk.Tk()
    app = Application(root)
    root.mainloop()

if __name__ == "__main__":
    main()

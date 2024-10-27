import tkinter as tk
from user_interface.ui import application

def main():
    root = tk.Tk()
    app = application(root)
    root.mainloop()

if __name__ == "__main__":
    main()

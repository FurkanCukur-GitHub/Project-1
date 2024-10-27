import torch
from ultralytics import YOLO
from tkinter import messagebox
import sys

# Define the model path here
MODEL_PATH = '../datasets/vehicles/runs/detect/train1/weights/best.pt'

class YOLOModel:
    def __init__(self):
        try:
            self.model = YOLO(MODEL_PATH)
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
            self.model.to(self.device)
            print(f"Model '{MODEL_PATH}' loaded successfully and running on '{self.device}'.")
        except Exception as e:
            messagebox.showerror("Model Loading Error", f"Failed to load the YOLO model.\nError: {e}")
            sys.exit(1)
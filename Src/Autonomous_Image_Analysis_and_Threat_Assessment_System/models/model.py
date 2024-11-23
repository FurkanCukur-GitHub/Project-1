import torch
from ultralytics import YOLO
from tkinter import messagebox
import sys

MODEL_PATH = '../datasets/merged_datasets/runs/detect/train3/weights/best.pt'

class YOLOModel:
    def __init__(self):
        try:
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
            print(f"Device selected: {self.device}")
            self.model = YOLO(MODEL_PATH)
            self.model.fuse()  # Fuse Conv2d + BatchNorm2d layers for faster inference
            self.model.to(self.device)
            print(f"Model '{MODEL_PATH}' loaded successfully and running on '{self.device}'.")
        except Exception as e:
            messagebox.showerror("Model Loading Error", f"Failed to load the YOLO model.\nError: {e}")
            sys.exit(1)

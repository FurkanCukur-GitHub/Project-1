# models/model.py
import torch
from ultralytics import YOLO
from PyQt5.QtWidgets import QMessageBox
import sys
from utils.config import MODEL_PATH

class YOLOModel:
    def __init__(self):
        try:
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
            print(f"Device selected: {self.device}")
            self.model = YOLO(MODEL_PATH)
            self.model.fuse()

            if self.device == 'cuda':
                self.model.model.half()

            self.model.to(self.device)
            print(f"Model '{MODEL_PATH}' loaded successfully and running on '{self.device}'.")

        except Exception as e:
            QMessageBox.critical(None, "Model Loading Error", f"Failed to load the YOLO model.\nError: {e}")
            sys.exit(1)

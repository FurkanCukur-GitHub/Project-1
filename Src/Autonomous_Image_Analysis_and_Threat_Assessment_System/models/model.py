# models/model.py
import torch
from PyQt5.QtWidgets import QMessageBox
import sys
from utils.config import MODEL_PATH
from ultralytics import YOLO

class YOLOModel:
    def __init__(self):
        try:
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
            print(f"Device selected: {self.device}")

            print("Loading YOLO model from best.pt...")
            self.model = YOLO(MODEL_PATH) 
            self.model.fuse()

            if self.device == 'cuda':
                self.model.model.half()

            if hasattr(self.model.model, 'names'):
                self.names = self.model.model.names
            else:
                self.names = {i: f"class{i}" for i in range(1000)}
            
            print(f"YOLO model '{MODEL_PATH}' loaded successfully on {self.device}.")

        except Exception as e:
            QMessageBox.critical(None, "Model Loading Error", f"Failed to load the YOLO model.\nError: {e}")
            sys.exit(1)


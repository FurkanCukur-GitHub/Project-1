# models/model.py
import torch
from PyQt5.QtWidgets import QMessageBox
import sys
from utils.config import MODEL_PATH
from modules.autobackend import AutoBackend

class YOLOModel:
    def __init__(self):
        try:
            # Check CUDA device
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
            print(f"Device selected: {self.device}")

            # Load TensorRT Engine model
            if MODEL_PATH.endswith('.engine'):
                print("Loading TensorRT Engine model...")
                # Enable fp16 support as True
                self.model = AutoBackend(weights=MODEL_PATH, device=torch.device(self.device), fp16=True)
                self.names = self.model.names
            else:
                raise ValueError("Invalid model file. TensorRT requires a '.engine' file.")

            # Check if model names are loaded
            if not hasattr(self, 'names') or not self.names:
                raise ValueError("TensorRT model failed to load correctly. 'names' attribute is missing or empty.")
            
            print(f"TensorRT Model '{MODEL_PATH}' loaded successfully and running on '{self.device}'.")

        except Exception as e:
            # Show error message on GUI and terminate the program
            QMessageBox.critical(None, "Model Loading Error", f"Failed to load the TensorRT YOLO model.\nError: {e}")
            sys.exit(1)
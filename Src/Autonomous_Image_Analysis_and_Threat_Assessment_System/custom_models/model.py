# models/model.py
import sys
import torch
from ultralytics import YOLO
from PyQt5.QtWidgets import QMessageBox


class YOLOModel:
    def __init__(self, model_path: str):
        try:
            if not model_path:
                raise ValueError("YOLOModel requires a non-empty model_path.")

            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            print(f"Device selected: {self.device}")
            print(f"Loading YOLOv8 model from {model_path} …")

            self.model = YOLO(model_path)
            self.model.fuse()
            
            # MODEL'İ GPU'ya half formatta gönder
            self.model.model.half().to(self.device)

            self.names = (
                self.model.model.names
                if hasattr(self.model.model, "names")
                else {i: f"class{i}" for i in range(1000)}
            )

            print(f"YOLOv8 model '{model_path}' loaded successfully on {self.device}.")

        except Exception as e:
            QMessageBox.critical(
                None,
                "Model Loading Error",
                f"Failed to load the YOLOv8 model.\nError: {e}",
            )
            sys.exit(1)

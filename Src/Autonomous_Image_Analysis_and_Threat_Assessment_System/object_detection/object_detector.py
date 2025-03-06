# object_detection/object_detector.py
import torch
import numpy as np
from models.model import YOLOModel

class ObjectDetector:
    def __init__(self):
        self.yolo_model = YOLOModel()
        self.model = self.yolo_model.model
        self.names = self.yolo_model.names

    def detect_objects(self, frames):
        batch_detections = []
        with torch.inference_mode():
            results = self.model(frames, verbose=False)
            
            for result in results:
                detections = []
                boxes = result.boxes  
                if boxes is not None and len(boxes) > 0:
                    boxes_xyxy = boxes.xyxy.cpu().numpy()
                    confidences = boxes.conf.cpu().numpy()
                    class_ids = boxes.cls.cpu().numpy().astype(int)
                    
                    for j in range(len(boxes_xyxy)):
                        x1, y1, x2, y2 = boxes_xyxy[j].tolist()
                        conf = float(confidences[j])
                        cls_id = int(class_ids[j])
                        class_name = self.names.get(cls_id, "Unknown")
                        detections.append({
                            'bbox': [x1, y1, x2, y2],
                            'conf': conf,
                            'cls': class_name,
                        })
                batch_detections.append(detections)
        return batch_detections
# object_detection/object_detector.py
import cv2
import torch
import numpy as np
from models.model import YOLOModel
from modules.utils import preprocess
from ultralytics.utils import ops

class ObjectDetector:
    def __init__(self):
        # Load YOLO TensorRT model
        self.yolo_model = YOLOModel()
        self.model = self.yolo_model.model
        ['Human', 'Drone', 'Helicopter', 'Missile', 'Missile Launchers', 'Aircraft', 'Tank', 'Truck', 'Warship', 'Weapon']
        self.names = {
            0: "Human",
            1: "Drone",
            2: "Helicopter",
            3: "Missile",
            4: "Missile Launchers",
            5: "Aircraft",
            6: "Tank",
            7: "Truck",
            8: "Warship",
            9: "Weapon",
        }

        # Check for TensorRT Engine
        if not hasattr(self.model, 'context'):
            raise RuntimeError("TensorRT model could not be loaded! Please use TensorRT engine format.")

    def detect_objects(self, frames):
        batch_detections = []

        with torch.inference_mode():
            # Preprocess frames and collect valid ones
            processed_imgs = []
            valid_indices = []
            for idx, frame in enumerate(frames):
                try:
                    img = preprocess(frame)
                    processed_imgs.append(img)
                    valid_indices.append(idx)
                except Exception as e:
                    print(f"Error preprocessing frame {idx}: {e}")

            if not processed_imgs:
                return [[] for _ in frames]  # Return empty detections for all frames

            batch_input = torch.cat(processed_imgs, dim=0)

            # Run inference
            preds = self.model.forward(batch_input)
            preds = preds.unsqueeze(0) if preds.ndimension() == 2 else preds
            nms_output = ops.non_max_suppression(preds, conf_thres=0.5, iou_thres=0.7, max_det=300)

            # Process outputs
            for i in range(len(frames)):
                if i in valid_indices:
                    orig_h, orig_w, _ = frames[i].shape
                    detections = []
                    det = nms_output[valid_indices.index(i)]
                    if len(det):
                        det[:, :4] = ops.scale_boxes((640, 640), det[:, :4], (orig_h, orig_w)).round()
                        for box in det:
                            x1, y1, x2, y2 = box[:4].tolist()
                            confidence = float(box[4])
                            class_id = int(box[5])
                            class_name = self.names.get(class_id, "Unknown")
                            detections.append({
                                'bbox': [x1, y1, x2, y2],
                                'conf': confidence,
                                'cls': class_name,
                            })
                    batch_detections.append(detections)
                else:
                    batch_detections.append([])  # Empty result for invalid frames

        return batch_detections
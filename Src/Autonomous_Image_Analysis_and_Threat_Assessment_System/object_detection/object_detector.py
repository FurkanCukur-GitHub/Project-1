# object_detection/object_detector.py
from models.model import YOLOModel

class ObjectDetector:
    def __init__(self):
        self.yolo_model = YOLOModel()
        self.model = self.yolo_model.model  # The YOLO model instance
        self.names = self.model.names  # Get class names from the model

    def detect_objects(self, frames):
        # Convert frames to RGB
        frames_rgb = [frame[:, :, ::-1] for frame in frames]

        # Run the model on the frames with verbose=False for performance optimization
        results = self.model(frames_rgb, verbose=False)

        # Continue with existing detection logic
        batch_detections = []
        for result in results:
            frame_detections = []
            boxes = result.boxes  # This is a Boxes object

            if boxes is not None:
                # Get the bounding boxes, confidence scores, and class IDs
                xyxy = boxes.xyxy.cpu().numpy()  # Bounding boxes in [x1, y1, x2, y2] format
                conf = boxes.conf.cpu().numpy()  # Confidence scores
                cls = boxes.cls.cpu().numpy()    # Class IDs

                for i in range(len(boxes)):
                    x1, y1, x2, y2 = xyxy[i]
                    confidence = conf[i]
                    class_id = int(cls[i])
                    class_name = self.names[class_id] if class_id < len(self.names) else "Unknown"
                    frame_detections.append([x1, y1, x2, y2, confidence, class_name, class_id])
            batch_detections.append(frame_detections)
        return batch_detections
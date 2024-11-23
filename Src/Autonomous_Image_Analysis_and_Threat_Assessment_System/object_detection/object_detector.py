# object_detection/object_detector.py
from models.model import YOLOModel

class ObjectDetector:
    def __init__(self):
        self.yolo_model = YOLOModel()
        self.model = self.yolo_model.model  # The YOLO model instance
        self.names = ['Human', 'Car', 'Motorcycle']

    def detect_objects(self, frame):
        # Convert frame to RGB
        frame_rgb = frame[:, :, ::-1]

        # Run the model on the frame
        results = self.model(frame_rgb)

        detections = []
        for result in results:
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
                    detections.append([x1, y1, x2, y2, confidence, class_name])
        return detections
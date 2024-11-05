# object_detection/object_detector.py
from models.model import YOLOModel
import cv2

class ObjectDetector:
    def __init__(self):
        self.model_loader = YOLOModel()
        self.model = self.model_loader.model

    def detect_objects(self, image):
        results = self.model.predict(source=image)
        return results

    def annotate_frame(self, frame, results):
        # Algılamaları çerçeve üzerine çiz
        for result in results:
            for box in result.boxes:
                # Sınır kutusu koordinatlarını al
                xyxy = box.xyxy[0].cpu().numpy()  # [x1, y1, x2, y2]
                x1, y1, x2, y2 = map(int, xyxy)
                
                # Sınıf kimliğini al
                class_id = int(box.cls[0].cpu().numpy())
                class_name = self.model.names[class_id]  # Modelinizin sınıf isimlerini nasıl tuttuğuna göre ayarlayın
                
                # Sınır kutusunu çiz
                cv2.rectangle(frame, (x1, y1), (x2, y2), color=(0, 255, 0), thickness=3)

                # Sınıf adı metnini ekle
                cv2.putText(frame, class_name, (x1, y1 - 10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (36,255,12), 2)
        return frame

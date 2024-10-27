from models.model import YOLOModel

class ObjectDetector:
    def __init__(self):
        self.model_loader = YOLOModel()
        self.model = self.model_loader.model

    def detect_objects(self, image):
        results = self.model.predict(source=image)
        return results

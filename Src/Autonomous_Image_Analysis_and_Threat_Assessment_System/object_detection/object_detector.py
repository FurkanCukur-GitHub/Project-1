# object_detection/object_detector.py
import torch
from custom_models.model import YOLOModel
from project_utils.config import MODEL_PATH_HUMAN, MODEL_PATH_MILITARY_VEHICLE


class ObjectDetector:
    def __init__(self):
        self.human_detector = YOLOModel(model_path=MODEL_PATH_HUMAN)
        self.human_names = self.human_detector.names

        self.vehicle_detector = YOLOModel(model_path=MODEL_PATH_MILITARY_VEHICLE)
        self.vehicle_names = self.vehicle_detector.names

    # --------------------------------------------------------------------- #
    def detect_objects(self, frames, threshold: float = 0.3):
        batch_out = []

        with torch.inference_mode():
            human_res   = self.human_detector.model(frames, verbose=False)
            vehicle_res = self.vehicle_detector.model(frames, verbose=False)

            for hr, vr in zip(human_res, vehicle_res):
                dets = []
                dets.extend(self._parse(hr, self.human_names, threshold))
                dets.extend(self._parse(vr, self.vehicle_names, threshold))
                batch_out.append(dets)

        return batch_out

    # --------------------------------------------------------------------- #
    @staticmethod
    def _parse(result, name_map, threshold):
        out = []
        boxes = getattr(result, "boxes", None)
        if not boxes:
            return out

        for (x1, y1, x2, y2), conf, cid in zip(
            boxes.xyxy.cpu().numpy(),
            boxes.conf.cpu().numpy(),
            boxes.cls.cpu().numpy().astype(int),
        ):
            if conf < threshold:
                continue
            out.append(
                {
                    "bbox": [float(x1), float(y1), float(x2), float(y2)],
                    "conf": float(conf),
                    "cls":  name_map.get(int(cid), f"class_{cid}"),
                }
            )
        return out

# object_tracking/object_tracker.py
import torch
from deep_sort_realtime.deepsort_tracker import DeepSort
from utils.config import MAX_AGE, N_INIT, NMS_MAX_OVERLAP

class ObjectTracker:
    def __init__(self):
        # Initialize the DeepSort object with GPU support
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.tracker = DeepSort(
            max_age=MAX_AGE,
            n_init=N_INIT,
            nms_max_overlap=NMS_MAX_OVERLAP,
            embedder_gpu=(self.device == 'cuda'),
            half=(self.device == 'cuda')  # Use half precision if possible
        )

    def update_tracks(self, detections, frame):
        # detections is a list of [x1, y1, x2, y2, conf, cls_name, class_id]
        # Convert detections to the format expected by DeepSort
        formatted_detections = []
        for det in detections:
            x1, y1, x2, y2, conf, cls_name, class_id = det
            width = x2 - x1
            height = y2 - y1
            formatted_detections.append(([x1, y1, width, height], conf, cls_name))

        # Update tracks
        tracks = self.tracker.update_tracks(formatted_detections, frame=frame)

        # Collect tracked objects
        tracked_objects = []
        for track in tracks:
            if not track.is_confirmed():
                continue
            track_id = track.track_id
            ltrb = track.to_ltrb()  # [left, top, right, bottom]
            cls = track.det_class
            conf = track.det_conf if track.det_conf is not None else 0.0
            tracked_objects.append({'track_id': track_id, 'bbox': ltrb, 'cls': cls, 'conf': conf})
        return tracked_objects
# object_tracking/object_tracker.py
import torch
from deep_sort_realtime.deepsort_tracker import DeepSort
from utils.config import MAX_AGE, N_INIT, NMS_MAX_OVERLAP

class ObjectTracker:
    def __init__(self):
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.tracker = DeepSort(
            max_age=MAX_AGE,
            n_init=N_INIT,
            nms_max_overlap=NMS_MAX_OVERLAP,
            half=(self.device == 'cuda')
        )

        self.id_map = {}
        self.next_id = 1

    def update_tracks(self, detections, frame):
        formatted_detections = []
        for det in detections:
            bbox = det['bbox']  
            x1, y1, x2, y2 = bbox
            width = x2 - x1
            height = y2 - y1
            conf = det['conf']
            cls_name = det['cls']

            formatted_detections.append(([x1, y1, width, height], conf, cls_name))

        with torch.no_grad():
            tracks = self.tracker.update_tracks(formatted_detections, frame=frame)

        tracked_objects = []
        for track in tracks:
            if not track.is_confirmed():
                continue

            deep_sort_id = track.track_id

            if deep_sort_id not in self.id_map:
                self.id_map[deep_sort_id] = self.next_id
                self.next_id += 1

            track_id = self.id_map[deep_sort_id]

            ltrb = track.to_ltrb()  
            cls = track.det_class
            conf = track.det_conf if track.det_conf is not None else 0.0

            tracked_objects.append({
                'track_id': track_id,  
                'bbox': [int(ltrb[0]), int(ltrb[1]), int(ltrb[2]), int(ltrb[3])],
                'cls': cls,
                'conf': round(conf, 2)
            })

        return tracked_objects
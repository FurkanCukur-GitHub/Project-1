# object_tracking/object_tracker.py
import torch, math
from collections import Counter, deque
from deep_sort_realtime.deepsort_tracker import DeepSort
from project_utils.config import MAX_AGE, N_INIT, NMS_MAX_OVERLAP

# ------------------------------- AYARLAR ------------------------------------ #
HISTORY       = 3    # Merkez eşleştirmesi için kaç kare geriye bakılsın?
MAJORITY_WIN  = 5    # Etiketi sabitlemek için pencere boyu
KEEP_MISSES   = 5    # Algılama kaybolduktan sonra kaç kare kutu kalsın?

# ----------------------------- Yardımcılar ---------------------------------- #
def _bbox_center(ltrb):
    return (ltrb[0] + ltrb[2]) * 0.5, (ltrb[1] + ltrb[3]) * 0.5

def _center_in_box(center, box):
    cx, cy = center
    return box[0] <= cx <= box[2] and box[1] <= cy <= box[3]

def _iou(b1, b2):
    xa, ya = max(b1[0], b2[0]), max(b1[1], b2[1])
    xb, yb = min(b1[2], b2[2]), min(b1[3], b2[3])
    inter  = max(0, xb - xa) * max(0, yb - ya)
    if inter == 0: return 0.0
    a1 = (b1[2]-b1[0]) * (b1[3]-b1[1])
    a2 = (b2[2]-b2[0]) * (b2[3]-b2[1])
    return inter / (a1 + a2 - inter)

# --------------------------------------------------------------------------- #
class ObjectTracker:
    """
    • Deep SORT izleri  
    • Sınıf bağımsız eşleştirme (YOLO class=0)  
    • Merkez‑içinde kuralı (HISTORY kare)  
    • Algılama kaybolursa TTL=KEEP_MISSES kare daha kutuyu koru
    """
    def __init__(self,
                 history:int      = HISTORY,
                 majority:int     = MAJORITY_WIN,
                 keep_misses:int  = KEEP_MISSES):

        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.tracker = DeepSort(
            max_age         = MAX_AGE,
            n_init          = N_INIT,
            nms_max_overlap = NMS_MAX_OVERLAP,
            half            = (self.device == 'cuda'),
            embedder_gpu    = (self.device == 'cuda')
        )

        self.next_app_id  = 1
        self.deep2app_id  = {}       # deep_id → app_id
        self.track_meta   = {}       # deep_id → {'labels':Counter,'best':str}

        self.prev_tracks  = deque(maxlen=history)   # merkez eşleştirmesi
        self.memory       = {}       # app_id → {'bbox', 'cls', 'ttl'}

        self.majority_win = majority
        self.keep_misses  = keep_misses

    # ------------------------------------------------------------------ #
    def update_tracks(self, detections, frame):
        """
        detections = [{'bbox':[x1,y1,x2,y2],'conf':0.9,'cls':'Tank'}, ...]
        """
        # 1) Deep SORT girişini hazırla (class=0)
        ds_in, det_boxes, det_labels = [], [], []
        for det in detections:
            x1,y1,x2,y2 = det['bbox']
            w, h        = x2 - x1, y2 - y1
            ds_in.append(([x1, y1, w, h], det['conf'], 0))
            det_boxes.append([x1, y1, x2, y2])
            det_labels.append(det['cls'])

        # 2) Deep SORT güncelle
        with torch.no_grad():
            tracks = self.tracker.update_tracks(ds_in, frame=frame)

        tracked_objects  = []
        updated_app_ids  = set()   # bu karede gerçek algılamayla güncellenenler

        # 3) Onaylı izler → APP‑ID çöz, etiket güncelle
        for tr in tracks:
            if not tr.is_confirmed():
                continue

            deep_id = tr.track_id
            ltrb    = tr.to_ltrb()
            app_id  = self._resolve_app_id(deep_id, ltrb)
            label   = self._update_label(deep_id, ltrb, det_boxes, det_labels)

            bbox_int = [int(v) for v in ltrb]
            conf_val = round(tr.det_conf or 0.0, 2)

            tracked_objects.append({
                'track_id': app_id,
                'bbox'    : bbox_int,
                'cls'     : label,
                'conf'    : conf_val
            })
            updated_app_ids.add(app_id)

            # Bellekte TTL sıfırla
            self.memory[app_id] = {'bbox': bbox_int, 'cls': label,
                                   'ttl': self.keep_misses}

        # 4) Güncellenmeyen (algılaması kaçan) izler için TTL düşür
        for app_id in list(self.memory):
            if app_id in updated_app_ids:
                continue
            self.memory[app_id]['ttl'] -= 1
            if self.memory[app_id]['ttl'] > 0:
                tracked_objects.append({
                    'track_id': app_id,
                    'bbox'    : self.memory[app_id]['bbox'],
                    'cls'     : self.memory[app_id]['cls'],
                    'conf'    : 0.0               # bu karede algılama yok
                })
            else:
                del self.memory[app_id]          # TTL bitti → sil

        # 5) Merkez eşleştirmesi için bu kareyi kaydet
        frame_tracks = {
            tr.track_id: {'bbox': tr.to_ltrb(), 'app_id': self.deep2app_id[tr.track_id]}
            for tr in tracks if tr.is_confirmed()
        }
        self.prev_tracks.append(frame_tracks)

        return tracked_objects

    # ------------------------------------------------------------------ #
    def _resolve_app_id(self, deep_id, ltrb_new):
        if deep_id in self.deep2app_id:
            return self.deep2app_id[deep_id]

        center_new = _bbox_center(ltrb_new)
        for past in reversed(self.prev_tracks):        # en yeni → eski
            for prev_id, info in past.items():
                if _center_in_box(center_new, info['bbox']):
                    self.deep2app_id[deep_id] = info['app_id']
                    return info['app_id']

        # Yeni APP‑ID
        self.deep2app_id[deep_id] = self.next_app_id
        self.next_app_id         += 1
        return self.deep2app_id[deep_id]

    # ------------------------------------------------------------------ #
    def _update_label(self, deep_id, tr_box, det_boxes, det_labels):
        meta = self.track_meta.setdefault(deep_id, {'label': None})

        # 1) Etiket zaten kilitlenmişse doğrudan dön
        if meta['label'] is not None:
            return meta['label']

        # 2) İlk kez tanışıyoruz → en yüksek IoU’lu algılamayı seç
        best_lbl, best_iou = None, 0.0
        for box, lbl in zip(det_boxes, det_labels):
            iou = _iou(tr_box, box)
            if iou > best_iou:
                best_iou, best_lbl = iou, lbl

        # En azından bir eşleşme bulunduysa kilitle
        if best_lbl:
            meta['label'] = best_lbl
            return best_lbl

        # Hiç eşleşme yoksa (nadir) 'Unknown' ile kilitle
        meta['label'] = "Unknown"
        return "Unknown"


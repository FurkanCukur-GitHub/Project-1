# threat_assessment/manager.py
"""
Basitleştirilmiş tehdit hesaplayıcı

• Dost nesnelerinin tehdidi = 0
• Düşman nesnelerinin tehdidi = base × 2 × (1 + Δ/SCALE)
• Unknown nesnelerin tehdidi  = base × (1 + Δ/SCALE)

Δ  =  (ilk görüldüğü karedeki mesafe  −  güncel mesafe)
SCALE = 50 px  ⇒  her 50 px yaklaşmaya +1 katsayı
"""

from collections import defaultdict
import numpy as np
from sklearn.cluster import DBSCAN

from .config import THREAT_COEFF, GROUP_RADIUS_PX
from .core   import ObjectState, TrackHistory, ObjectGroup
from .rules import _nearest_distance


SCALE = 50.0        # px başına dinamik artış
EPS   = 1e-6

class ThreatAssessment:
    def __init__(self):
        self.base_coeff  = THREAT_COEFF
        self.threat_coefficients = self.base_coeff
        self.histories   = defaultdict(TrackHistory)
        self.first_dist  = {}

    # ------------------------------------------------------------------
    def update(self, tracked_objects, friendly_zones=None):
        states = [self._to_state(o) for o in tracked_objects]

        # 1) Koordinat geçmişi güncelle
        for st in states:
            self.histories[st.track_id].add(st.center)

        # 2) Dost bölgesi merkezleri
        zone_centers = [
            np.array([(x1 + x2) * 0.5, (y1 + y2) * 0.5])
            for (x1, y1, x2, y2) in (friendly_zones or [])
        ]

        # 3) Nesne skorlaması
        for st in states:
            base = self.base_coeff.get(st.cls, self.base_coeff["Unknown"])
            history = self.histories[st.track_id]

            # Dost nesne tehdit değeri sıfır
            if st.status == "friend":
                st.threat = 0.0
                continue

            # Unknown nesne tehdit hesabı
            if st.status == "unknown":
                total_threat = 0.0
                foe_groups = [s for s in states if s.status == "foe"]

                # Düşmanlara yakınlık skoru
                foe_centers = [f.center for f in foe_groups]
                d_foe = _nearest_distance(st.center, foe_centers)
                threat_foe = max(0.0, (200 - d_foe) / 200) * base

                # Dost bölgelere yakınlık skoru
                threat_friend = sum([
                    max(0.0, (200 - np.linalg.norm(st.center - c)) / 200) * base
                    for c in zone_centers
                ])

                total_threat = threat_foe + threat_friend

                # Min = base, Max = base * 2
                st.threat = round(max(base, min(base * 2, total_threat)), 2)
                continue

            # Foe nesnesi için tehdit değerlendirmesi
            if st.status == "foe":
                total_dyn_score = 0.0
                total_velocity_score = 0.0

                for i, c in enumerate(zone_centers):
                    d_curr = np.linalg.norm(st.center - c)

                    # İlk karedeki mesafeyi kaydet
                    if (st.track_id, i) not in self.first_dist:
                        self.first_dist[(st.track_id, i)] = d_curr
                    d_init = self.first_dist[(st.track_id, i)]

                    # Δ mesafe
                    delta = max(0.0, d_init - d_curr)
                    dyn_score = delta / SCALE
                    total_dyn_score += dyn_score

                    # Yaklaşma yönü ve hız bileşeni
                    v = history.velocity()
                    speed = np.linalg.norm(v)
                    if speed < 1e-3:
                        velocity_score = 0.0
                    else:
                        dir_vec = c - st.center
                        dist = np.linalg.norm(dir_vec)
                        if dist > 1e-3:
                            dir_vec /= dist
                            speed_towards = np.dot(v, dir_vec)
                            velocity_score = max(0.0, speed_towards / 20)
                        else:
                            velocity_score = 0.0

                    total_velocity_score += velocity_score

                # ❗ Başlangıç sabit: base * 2 (dost bölgesi sayısından bağımsız)
                threat_total = (base * 2) + total_dyn_score + total_velocity_score
                st.threat = round(threat_total, 2)

        return [vars(s) for s in states]




    # ------------------------------------------------------------------
    def perform_threat_assessment(self, app):
        """
        UI çağrısı:
        • Nesne statülerini tabloya geri yazar
        • Video durdurulmuş olsa bile çalışır
        """
        tracked = app.video_processor.current_tracked_objects

        # Statüleri (friend/foe/unknown) aktar
        for obj in tracked:
            tid = str(obj["track_id"])
            obj["status"] = app.object_statuses.get(tid, {}).get("status", "unknown")

        scored = self.update(tracked, friendly_zones=app.friendly_zones)

        for obj in scored:
            tid = str(obj["track_id"])
            if tid not in app.object_statuses:
                app.object_statuses[tid] = {
                    "status": "unknown",
                    "selected": False,
                    "threat_level": 1.0,
                }
            app.object_statuses[tid]["threat_level"] = obj["threat"]

    # ------------------------------------------------------------------
    #  Yardımcılar
    # ------------------------------------------------------------------
    @staticmethod
    def _to_state(o: dict) -> ObjectState:
        return ObjectState(
            track_id = o["track_id"],
            cls      = o["cls"],
            status   = o.get("status", "unknown"),
            bbox     = tuple(o["bbox"]),
            conf     = o.get("conf", 0.0),
        )

    @staticmethod
    def _cluster(states):
        """Friend / foe grupları – dost merkezleri yoksa fallback."""
        if not states:
            return [], []
        pts = np.stack([s.center for s in states])
        labels = DBSCAN(eps=GROUP_RADIUS_PX, min_samples=1).fit_predict(pts)

        groups = {}
        for st, lab in zip(states, labels):
            groups.setdefault((lab, st.status), []).append(st)

        friend_g, foe_g = [], []
        for (lab, status), members in groups.items():
            g = ObjectGroup(group_id=lab, status=status, members=members)
            if status == "friend":
                friend_g.append(g)
            elif status == "foe":
                foe_g.append(g)
        return friend_g, foe_g
# threat_assessment/manager.py
from collections import defaultdict
import numpy as np


from .config import THREAT_COEFF, PIXEL_TO_METER
from .core   import ObjectState, TrackHistory

class ThreatAssessment:
    def __init__(self):
        self.base_coeff   = THREAT_COEFF
        self.threat_coefficients = self.base_coeff
        self.histories    = defaultdict(TrackHistory)
        self.first_dist   = {}
        self.prev_threat  = defaultdict(float)

    # --------------------------------------------------------------
    def update(self, tracked_objects, *, friendly_zones=None, enemy_zones=None):
        states = [self._to_state(o) for o in tracked_objects]

        for st in states:
            self.histories[st.track_id].add(st.center)
        zone_centers = [
            np.array([(x1+x2)*0.5, (y1+y2)*0.5]) * PIXEL_TO_METER
            for (x1, y1, x2, y2) in (friendly_zones or [])
        ]

        # --------------- DÖNGÜ: Her nesne ---------------
        for st in states:
            base    = self.base_coeff.get(st.cls, 1)
            history = self.histories[st.track_id]

            # ---------- FRIEND ----------
            if st.status == "friend":
                st.threat = 0.0
                self.prev_threat[st.track_id] = 0.0
                continue

            # ==========================================================
            # ---------- UNKNOWN  (dost + düşman bölgeleri) ------------
            # ==========================================================
            if st.status == "unknown":
                dist_extra_sum = 0.0
                vel_score_sum  = 0.0

                # Dost ve düşman bölge merkezleri
                friend_centers = zone_centers
                enemy_centers  = [
                    np.array([(x1+x2)*0.5, (y1+y2)*0.5]) * PIXEL_TO_METER
                    for (x1, y1, x2, y2) in (enemy_zones or [])
                ]
                all_centers = friend_centers + enemy_centers

                # Mesafeye göre katsayı
                def factor_by_dist(d: float) -> float:
                    if d > 100:   return 1.0
                    elif d > 90:  return 1.3
                    elif d > 80:  return 1.6
                    elif d > 70:  return 1.9
                    elif d > 60:  return 2.2
                    elif d > 50:  return 2.5
                    elif d > 40:  return 2.8
                    elif d > 30:  return 3.1
                    elif d > 20:  return 3.4
                    elif d > 10:  return 3.7
                    else:         return 4.0        # 0–10 m

                # Her merkez için katkı
                for c in all_centers:
                    d      = np.linalg.norm(st.center - c)
                    factor = factor_by_dist(d)

                    if factor > 1.0:                          # ≤100 m
                        dist_extra_sum += base * (factor - 1.0)

                    # Hız bileşeni
                    v     = history.velocity()
                    speed = np.linalg.norm(v)
                    if speed >= 1e-3:
                        dir_vec = c - st.center
                        dist    = np.linalg.norm(dir_vec)
                        if dist >= 1e-3:
                            dir_vec /= dist
                            speed_towards = np.dot(v, dir_vec)
                            vel_score_sum += max(
                                0.0,
                                speed_towards / (10 * PIXEL_TO_METER)
                            )

                st.threat = round(base + dist_extra_sum + vel_score_sum, 2)

            # ==========================================================
            # --------------------  FOE  -------------------------------
            # ==========================================================
            elif st.status == "foe":
                dist_score_sum = 0.0
                vel_score_sum  = 0.0

                if not zone_centers:                 # dost bölgesi tanımsız
                    dist_score_sum = base * 2

                for c in zone_centers:
                    d = np.linalg.norm(st.center - c)

                    # 5 m'lik dilimler
                    if d > 100:      factor = 1.0
                    elif d > 95:     factor = 1.2
                    elif d > 90:     factor = 1.4
                    elif d > 85:     factor = 1.6
                    elif d > 80:     factor = 1.8
                    elif d > 75:     factor = 2.0
                    elif d > 70:     factor = 2.2
                    elif d > 65:     factor = 2.4
                    elif d > 60:     factor = 2.6
                    elif d > 55:     factor = 2.8
                    elif d > 50:     factor = 3.0
                    elif d > 45:     factor = 3.2
                    elif d > 40:     factor = 3.4
                    elif d > 35:     factor = 3.6
                    elif d > 30:     factor = 3.8
                    elif d > 25:     factor = 4.0
                    elif d > 20:     factor = 4.2
                    elif d > 15:     factor = 4.4
                    elif d > 10:     factor = 4.6
                    elif d > 5:      factor = 4.8
                    else:            factor = 5.0

                    dist_score_sum += (base * 2) * factor

                    # Hız bileşeni
                    v     = history.velocity()
                    speed = np.linalg.norm(v)
                    if speed >= 1e-3:
                        dir_vec = c - st.center
                        dist    = np.linalg.norm(dir_vec)
                        if dist >= 1e-3:
                            dir_vec /= dist
                            speed_towards = np.dot(v, dir_vec)
                            vel_score_sum += max(
                                0.0,
                                speed_towards / (10 * PIXEL_TO_METER)
                            )

                if dist_score_sum == 0.0:
                    dist_score_sum = base * 2

                st.threat = round(dist_score_sum + vel_score_sum, 2)

            # ==========================================================
            # ------------ KARARLILIK (Histerezis) --------------------
            # ==========================================================
            THR_HYST = 1.0                 # ±1 puan içindeki salınımları bastır
            prev = self.prev_threat[st.track_id]
            new  = st.threat

            if new > prev and (new - prev) < THR_HYST:
                new = prev
            elif new < prev and (prev - new) < THR_HYST:
                new = prev

            self.prev_threat[st.track_id] = new
            st.threat = new


        return [vars(s) for s in states]

    # ------------------------------------------------------------------
    def perform_threat_assessment(self, app):
        tracked = app.video_processor.current_tracked_objects
        for obj in tracked:
            tid = str(obj["track_id"])
            obj["status"] = app.object_statuses.get(tid, {}).get("status", "unknown")

        scored = self.update(
            tracked,
            friendly_zones=app.friendly_zones,
            enemy_zones   =app.enemy_zones
        )


        for obj in scored:
            tid = str(obj["track_id"])
            app.object_statuses.setdefault(tid, {"status":"unknown","selected":False,"threat_level":1.0})
            app.object_statuses[tid]["threat_level"] = obj["threat"]

    # ------------------------------------------------------------------
    @staticmethod
    def _to_state(o: dict) -> ObjectState:
        return ObjectState(
            track_id=o["track_id"],
            cls=o["cls"],
            status=o.get("status", "unknown"),
            bbox=tuple(o["bbox"]),
            conf=o.get("conf", 0.0),
        )
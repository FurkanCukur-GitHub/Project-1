# threat_assessment/rules.py
"""
Tehdit kuralları (mesafe + hız/yön odaklı).

• DistanceToFriendlyZone – dost bölgesi / dost grup merkezlerine mesafe
• VelocityTowardsFriendlyZone – dost bölgesine doğru hız bileşeni
• UnknownNearFoe / UnknownNearFriend – mevcut mantık korunur
"""

from abc import ABC, abstractmethod
import numpy as np
from .config import GROUP_RADIUS_PX   # GROUP_RADIUS_PX sadece diğer kurallarda gerekirse

# ─────────────────────────── yardımcılar ────────────────────────────
def _nearest_distance(pt, centers):
    if not centers:
        return 1e9
    return min(np.linalg.norm(pt - c) for c in centers)

def _all_distances(pt, centers):
    return [np.linalg.norm(pt - c) for c in centers] if centers else []

# ─────────────────────────── soyut temel ────────────────────────────
class Rule(ABC):
    weight: float = 1.0
    @abstractmethod
    def score(self, obj, *, friend_groups, foe_groups, histories, zone_centers):
        ...

# ────────────────── 1) Dost bölgesine MESAFE kuralı ─────────────────
class DistanceToFriendlyZone(Rule):
    """
    Uzaklık ↘︎ oldukça sınırsız artan skor:
        score = max(0, K/(d+ε) - 1)
    d = K   →  score = 0
    d = K/2 →  score = 1
    d → 0   →  score → ∞
    """
    weight = 1.0         # artık katsayı burada değil, formül kendiyle büyür
    K      = 300         # 'referans uzaklık' (px)
    EPS    = 1e-6

    def score(self, obj, *, friend_groups, zone_centers, **_):
        # Dost bölgesi > dost grup merkezleri hiyerarşisi
        centers = zone_centers if zone_centers else [g.center for g in friend_groups]
        scores = [
            max(0.0, (self.K / (d + self.EPS)) - 1.0)
            for d in _all_distances(obj.center, centers)
        ]
        return sum(scores)


# ───────────── 2) Dost bölgesine DOĞRU HIZ kuralı ─────────────
class VelocityTowardsFriendlyZone(Rule):
    weight    = 2.5
    SPEED_REF = 20      # px / frame

    def score(self, obj, *, friend_groups, histories, zone_centers, **_):
        hist = histories.get(obj.track_id)
        if not hist or len(hist.pts) < 3:
            return 0.0

        v = hist.velocity()
        speed = np.linalg.norm(v)
        if speed < 1e-3:
            return 0.0

        # Dost merkezleri
        if zone_centers:
            centers = zone_centers
        else:
            centers = [g.center for g in friend_groups]

        total = 0.0
        for c in centers:
            dir_vec = c - obj.center
            dist    = np.linalg.norm(dir_vec)
            if dist < 1e-3:
                continue
            dir_vec /= dist
            speed_towards = np.dot(v, dir_vec)
            total += max(0.0, speed_towards / self.SPEED_REF)
        return total

# ───────── Unknown nesne düşmana / dosta yakınsa kuralları ──────────
class UnknownNearFoe(Rule):
    weight    = 1.2
    DIST_REF  = 200

    def score(self, obj, *, foe_groups, **__):
        if obj.status != "unknown":
            return 0.0
        foe_centers = [g.center for g in foe_groups]
        d = _nearest_distance(obj.center, foe_centers)
        return max(0.0, (self.DIST_REF - d) / self.DIST_REF)

class UnknownNearFriend(Rule):
    weight    = 1.5
    DIST_REF  = 200

    def score(self, obj, *, friend_groups, zone_centers, **__):
        if obj.status != "unknown":
            return 0.0
        if zone_centers:
            centers = zone_centers
        else:
            centers = [g.center for g in friend_groups]
        d = _nearest_distance(obj.center, centers)
        return max(0.0, (self.DIST_REF - d) / self.DIST_REF)

# ─────────────── Frame-to-Frame yaklaşma kuralı ───────────────
class ApproachingFriendDelta(Rule):
    """
    Önceki kareye göre dost merkezine yaklaşma miktarını (px)
    doğrudan skora çevirir.

        delta = d_prev − d_curr   (yalnız pozitifse)
        score = delta / SCALE

    SCALE = 50 ⇒ 50 px yaklaşma → +1 dinamik skor.
    """
    weight = 1.0
    SCALE  = 50.0

    def score(self, obj, *, friend_groups, histories, zone_centers, **kw):
        hist = histories.get(obj.track_id)
        if not hist or len(hist.pts) < 2:
            return 0.0

        # Dost merkezleri (öncelik: zone_centers > friend group centers)
        centers = zone_centers if zone_centers else [g.center for g in friend_groups]
        if not centers:
            return 0.0

        # En yakın mesafe; önceki kare ve şimdiki kare
        pt_curr = hist.pts[-1]
        pt_prev = hist.pts[-2]

        d_curr = min(np.linalg.norm(pt_curr - c) for c in centers)
        d_prev = min(np.linalg.norm(pt_prev - c) for c in centers)

        if d_prev - d_curr <= 0.0:
            return 0.0          # Yaklaşmıyor

        return (d_prev - d_curr) / self.SCALE

# ──────────────────────── aktif kural listesi ───────────────────────
ALL_RULES = [
    DistanceToFriendlyZone(),
    VelocityTowardsFriendlyZone(),
    ApproachingFriendDelta(),     # ← yeni kural
    UnknownNearFoe(),
    UnknownNearFriend(),
]


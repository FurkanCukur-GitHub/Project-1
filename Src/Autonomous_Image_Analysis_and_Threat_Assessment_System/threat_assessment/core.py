# threat_assessment/core.py

from dataclasses import dataclass, field
from collections import deque
import numpy as np
from .config import HISTORY_LEN, PIXEL_TO_METER

@dataclass
class ObjectState:
    track_id: int
    cls: str
    status: str   # 'friend'|'foe'|'unknown'
    bbox: tuple   # (x1,y1,x2,y2) – piksel cinsinden
    conf: float
    threat: float = 0.0

    @property
    def center(self):
        """Merkezi METRE cinsinden döndürür."""
        x1, y1, x2, y2 = self.bbox
        cx = (x1 + x2) * 0.5 * PIXEL_TO_METER
        cy = (y1 + y2) * 0.5 * PIXEL_TO_METER
        return np.array([cx, cy])

@dataclass
class TrackHistory:
    pts: deque = field(default_factory=lambda: deque(maxlen=HISTORY_LEN))
    def add(self, pt):
        self.pts.append(pt)
    def velocity(self):
        if len(self.pts) < 2:
            return np.zeros(2)
        return self.pts[-1] - self.pts[-2]

@dataclass
class ObjectGroup:
    group_id: int
    status: str
    members: list[ObjectState]
    @property
    def center(self):
        if not self.members:
            return np.array([0.0, 0.0])
        return np.stack([m.center for m in self.members]).mean(axis=0)
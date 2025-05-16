# threat_assessment/__init__.py
"""Package init – kolay dış erişim için kısayollar."""
from .config import THREAT_COEFF
from .manager import ThreatAssessment

__all__ = [
    "THREAT_COEFF",
    "ThreatAssessment",
]


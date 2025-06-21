# threat_assessment/config.py

THREAT_COEFF = {
    # ---------------- Araç modeli (16 sınıf) ---------------- #
    "AMV-7 Marshall": 7,
    "HEMTT": 5,
    "HEMTT Ammo": 5,
    "HEMTT Box": 6,
    "HEMTT Fuel": 5,
    "HEMTT Medical": 5,
    "HEMTT Transport": 5,
    "HEMTT Transport (Covered)": 6,
    "Hunter HMG": 6,
    "IFV-6a Cheetah": 9,
    "IFV-6c Panther": 8,
    "M2A1 Slammer": 10,
    "M4 Scorcher": 10,
    "M5 Sandstorm MLRS": 10,
    "Prowler (HMG)": 6,
    "Rhino MGS": 8,
    # ---------------- İnsan modeli ---------------- #
    "person": 4
}

# --------------- Kalibrasyon --------------- #
# 900 piksel = 100 metre
PIXEL_TO_METER = 100.0 / 900.0

# Kümeleme ve hız hesaplaması için eşikler
GROUP_RADIUS_PX = 80     # DBSCAN eps
HISTORY_LEN     = 10     # merkez geçmişi uzunluğu (kare)
# threat_assessment/config.py

THREAT_COEFF = {
    # ---------------- Araç modeli (17 sınıf) ---------------- #
    "AMV-7 Marshall": 6,
    "HEMTT": 3,
    "HEMTT Ammo": 5,
    "HEMTT Box": 3,
    "HEMTT Fuel": 4,
    "HEMTT Medical": 2,
    "HEMTT Transport": 3,
    "HEMTT Transport (Covered)": 3,
    "Hunter HMG": 6,
    "IFV-6a Cheetah": 8,
    "IFV-6c Panther": 7,
    "M2A1 Slammer": 10,
    "M4 Scorcher": 9,
    "M5 Sandstorm MLRS": 9,
    "Prowler (HMG)": 5,
    "Rhino MGS": 9,
    # ---------------- İnsan modeli ---------------- #
    "Human": 1,
    # ---------------- Bilinmeyen ---------------- #
    "Unknown": 3,
}

# Kümeleme ve hız hesaplaması için eşikler
GROUP_RADIUS_PX = 80     # DBSCAN eps
HISTORY_LEN     = 10     # merkez geçmişi uzunluğu (kare)
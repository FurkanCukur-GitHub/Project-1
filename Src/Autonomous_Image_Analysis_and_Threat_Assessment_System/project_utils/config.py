# utils/config.py
BATCH_SIZE = 16

SCALE = 1

# DeepSort configuration
MAX_AGE = 60
N_INIT = 5
NMS_MAX_OVERLAP = 0.5

# Model configuration
# İnsan tespiti için model ağırlık dosyası
MODEL_PATH_HUMAN = '../custom_models/person_model.pt'
# Askeri araç tespiti için model ağırlık dosyası
MODEL_PATH_MILITARY_VEHICLE = '../custom_models/vehicle_model.pt'

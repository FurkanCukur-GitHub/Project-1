import os
from ultralytics import YOLO

def train_model():
    # Hangi dizinde çalıştığını göster (kontrol için çok yararlı!)
    print("Aktif çalışma dizini:", os.getcwd())
    assert os.path.exists("data.yaml"), "data.yaml bu dizinde bulunamadı!"

    # Modeli yükle
    model = YOLO("yolov5n.pt")  # küçük model, istersen yolov8l veya yolov8x kullanabilirsin

    # Eğitimi başlat
    model.train(
        data="data.yaml",             # data.yaml dosyan bu script ile aynı klasörde olmalı
        epochs=100,
        imgsz=(1080, 1920),           # görüntü boyutu (senin tercihin)
        batch=8,
        device=0,                     # GPU ID (RTX 5080 genelde 0’dır)
        name="person",               # runs/train/vehicle klasörü oluşur
        project="runs/train",
        amp=True,                     # Automatic Mixed Precision (daha hızlı eğitim)
        cache=False,                   # RAM'e veri önbelleklemesi (16+ GB RAM varsa önerilir)
        workers=6,                    # DataLoader işçi sayısı (8 iyi bir başlangıç)
        cos_lr=True,                  # Cosine learning rate decay
        optimizer='AdamW',            # Alternatif: 'SGD' (daha stabil olabilir)
        deterministic=True,          # Aynı sonuçları tekrar alabilmek için (reproducibility)
        exist_ok=True                 # Daha önce aynı isimde klasör varsa devam eder
    )

if __name__ == "__main__":
    from multiprocessing import freeze_support
    freeze_support()  # Windows multiprocessing hatasını önler
    train_model()

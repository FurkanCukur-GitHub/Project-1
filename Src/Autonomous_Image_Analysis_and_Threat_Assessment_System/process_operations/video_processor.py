# process_operations/video_processor.py
import time
import cv2
from PIL import Image, ImageTk

class VideoProcessor:
    def __init__(self, app):
        self.app = app

    def play_video(self):
        while self.app.playing and self.app.cap.isOpened():
            start_time = time.time()

            if self.app.direction == 1:
                ret, frame = self.app.cap.read()
                if not ret:
                    # Videonun sonuna ulaşıldı, başa dön
                    self.app.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, frame = self.app.cap.read()
                    if not ret:
                        break
            elif self.app.direction == -1:
                # Ters oynatma: iki çerçeve geri git ve bir çerçeve oku
                current_frame = int(self.app.cap.get(cv2.CAP_PROP_POS_FRAMES))
                new_frame = current_frame - 2  # İki çerçeve geri git
                if new_frame < 0:
                    # Videonun başına ulaşıldı, sona dön
                    frame_count = int(self.app.cap.get(cv2.CAP_PROP_FRAME_COUNT))
                    self.app.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_count - 1)
                else:
                    self.app.cap.set(cv2.CAP_PROP_POS_FRAMES, new_frame)
                ret, frame = self.app.cap.read()
                if not ret:
                    self.app.event_handlers.stop_video()
                    break

            self.app.current_frame += 1
            if self.app.current_frame % self.app.frame_skip != 0:
                continue  # Çerçeveyi atla eğer çerçeve atlama etkinse

            # Çerçeveyi video görüntüleme alanına sığacak şekilde yeniden boyutlandır
            frame = cv2.resize(frame, (self.app.display_width, self.app.display_height))

            # Çerçeveyi RGB formatına dönüştür
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Nesne algılama işlemi
            try:
                results = self.app.object_detector.detect_objects(frame_rgb)
                # Anotasyonları ekle
                annotated_frame = self.app.object_detector.annotate_frame(frame_rgb, results)
            except Exception as e:
                print(f"Model çıkarımı sırasında hata: {e}")
                self.app.event_handlers.stop_video()
                break

            # PIL Image'e dönüştür
            img = Image.fromarray(annotated_frame)
            imgtk = ImageTk.PhotoImage(image=img)

            # Ana iş parçacığında video etiketini güncelle
            self.app.video_label.after(0, self.update_video_label, imgtk)

            # Geçen süreyi hesapla ve uyuma süresini belirle
            elapsed_time = time.time() - start_time
            time.sleep(max(0, (1 / self.app.fps) - elapsed_time))

        # Döngü sona erdiğinde thread çalışma bayrağını sıfırla
        self.app.video_thread_running = False

    def update_video_label(self, imgtk):
        self.app.video_label.imgtk = imgtk
        self.app.video_label.configure(image=imgtk)

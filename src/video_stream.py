import cv2
import time
from src.emotion_recognition import EmotionRecognizer

class VideoCamera(object):
    def __init__(self, camera_index=1):
        self.camera_index = camera_index
        self.video = None
        self.emotion_recognizer = EmotionRecognizer('model/ferNet.h5', 'model/haarcascade_frontalface_default.xml')
        self.latest_emotions = []
        self.last_recognition_time = 0

    def start_camera(self):
        self.stop_camera()  # Ensure any previous camera is stopped
        self.video = cv2.VideoCapture(self.camera_index)

    def stop_camera(self):
        if self.video is not None:
            self.video.release()
            self.video = None

    def switch_camera(self, camera_index):
        self.camera_index = camera_index
        self.start_camera()

    def get_frame(self):
        if self.video is None:
            self.start_camera()
        success, image = self.video.read()
        if success:
            current_time = time.time()
            # Perform emotion recognition every 1 second
            if current_time - self.last_recognition_time >= 1:
                image, emotions = self.emotion_recognizer.recognize(image)
                self.latest_emotions = emotions  # Store the latest emotions detected
                self.last_recognition_time = current_time
            else:
                image, _ = self.emotion_recognizer.detect_faces(image)

            ret, jpeg = cv2.imencode('.jpg', image)
            return jpeg.tobytes()
        else:
            return None

    def reset_stats(self):
        self.latest_emotions = []

    def __del__(self):
        self.stop_camera()

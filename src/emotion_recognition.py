import cv2
import numpy as np
from tensorflow.keras.models import load_model

class EmotionRecognizer:
    def __init__(self, model_path, haar_path):
        self.model = load_model(model_path)
        self.face_detector = cv2.CascadeClassifier(haar_path)
        self.emotion_labels = ['Angry', 'Disgust', 'Fear', 'Happy', 'Neutral', 'Sad', 'Surprise']

    def detect_faces(self, img):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = self.face_detector.detectMultiScale(gray, 1.3, 5)
        for (x, y, w, h) in faces:
            cv2.rectangle(img, (x, y), (x+w, y+h), (0, 255, 0), 2)
        return img, faces

    def recognize(self, img):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = self.face_detector.detectMultiScale(gray, 1.3, 5)
        emotion_results = []

        for (x, y, w, h) in faces:
            face_img = gray[y:y+h, x:x+w]
            face_img = cv2.resize(face_img, (48, 48))
            face_img = face_img.astype('float32') / 255
            face_img = np.expand_dims(face_img, axis=-1)  # Add channel dimension
            face_img = np.expand_dims(face_img, axis=0)  # Add batch dimension
            predictions = self.model.predict(face_img)
            max_index = np.argmax(predictions)
            emotion = self.emotion_labels[max_index]
            cv2.putText(img, emotion, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (36, 255, 12), 2)
            cv2.rectangle(img, (x, y), (x+w, y+h), (0, 255, 0), 2)
            emotion_results.append({'emotion': emotion, 'probability': predictions[0, max_index].item()})

        return img, emotion_results

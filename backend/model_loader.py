import tensorflow as tf
import numpy as np
import cv2
import os

model = None

def load_model():
    global model

    if model is not None:
        return model

    os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

    model = tf.keras.models.load_model("../model/model.h5", compile=False)

    model.load_weights("../weights/modeldense1.h5")

    return model


def preprocess(image):
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    im = cv2.filter2D(image, -1, kernel)
    return im / 255.0


def predict_img(img):
    model = load_model()

    img = preprocess(img)
    img = cv2.resize(img, (224, 224))
    img = img.reshape(-1, 224, 224, 3)

    pred = model.predict(img)[0]
    max_index = np.argmax(pred)
    confidence = float(np.max(pred)) * 100

    if max_index % 2 == 0:
        return f"🟢 Benign (No Cancer)\nConfidence: {confidence:.2f}%"
    else:
        return f"🔴 Malignant (Cancer)\nConfidence: {confidence:.2f}%"
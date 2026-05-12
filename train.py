import tensorflow as tf
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from model import get_densenet, get_resnet, get_efficientnet, get_inception
import os

IMG_SIZE = (224, 224)
BATCH_SIZE = 16
EPOCHS = 5  # increase 

# -------- DATA --------
train_gen = ImageDataGenerator(rescale=1./255, validation_split=0.2)

train_data = train_gen.flow_from_directory(
    "dataset/train",
    target_size=IMG_SIZE,
    batch_size=BATCH_SIZE,
    class_mode='categorical',
    subset='training'
)

val_data = train_gen.flow_from_directory(
    "dataset/train",
    target_size=IMG_SIZE,
    batch_size=BATCH_SIZE,
    class_mode='categorical',
    subset='validation'
)

# -------- TRAIN FUNCTION --------
def train_model(model, name):
    model.compile(
        optimizer=tf.keras.optimizers.legacy.Adam(learning_rate=0.0001),
        loss='categorical_crossentropy',
        metrics=['accuracy']
    )
    class_weights = {
    0: 1.0,   # benign
    1: 0.5    # malignant
}
    model.fit(
        train_data,
        validation_data=val_data,
        epochs=EPOCHS,
        class_weight=class_weights
    )

    os.makedirs("weights", exist_ok=True)
    model.save_weights(f"weights/{name}.h5")
    print(f"Saved: weights/{name}.h5")


# -------- TRAIN ALL MODELS --------

#print("🚀 Training DenseNet...")
#train_model(get_densenet(), "densenet")

#print("🚀 Training ResNet...")
#train_model(get_resnet(), "resnet")

print("🚀 Training EfficientNet...")
train_model(get_efficientnet(), "efficientnet")

print("🚀 Training Inception...")
train_model(get_inception(), "inception")
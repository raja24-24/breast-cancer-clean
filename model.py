from tensorflow.keras.applications import DenseNet201, ResNet50, EfficientNetB0, InceptionResNetV2
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, BatchNormalization
from keras.regularizers import l1_l2

# -------- COMMON MODEL --------
def build_model(base_model):
    model = Sequential()
    model.add(base_model)
    model.add(BatchNormalization())
    model.add(Dense(512, activation='relu', kernel_regularizer=l1_l2(0.01)))
    model.add(BatchNormalization())
    model.add(Dense(2, activation='softmax'))  
    return model


# -------- MODELS --------

def get_densenet():
    base = DenseNet201(input_shape=(224,224,3), include_top=False, pooling='max', weights='imagenet')
    for layer in base.layers[:-20]:
         layer.trainable = False

    for layer in base.layers[-20:]:
        layer.trainable = True 
    return build_model(base)


def get_resnet():
    base = ResNet50(input_shape=(224,224,3), include_top=False, pooling='max', weights='imagenet')
    for layer in base.layers[:-20]:
         layer.trainable = False

    for layer in base.layers[-20:]:
        layer.trainable = True  
    return build_model(base)


def get_efficientnet():
    base = EfficientNetB0(input_shape=(224,224,3), include_top=False, pooling='max', weights='imagenet')
    for layer in base.layers[:-20]:
         layer.trainable = False

    for layer in base.layers[-20:]:
        layer.trainable = True  
    return build_model(base)


def get_inception():
    base = InceptionResNetV2(input_shape=(224,224,3), include_top=False, pooling='max', weights='imagenet')
    for layer in base.layers[:-20]:
         layer.trainable = False

    for layer in base.layers[-20:]:
        layer.trainable = True  
    return build_model(base)

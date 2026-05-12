import gdown
import os

def download_weights():
    os.makedirs("weights", exist_ok=True)
    file_path = "weights/modeldense1.h5"

   
    if os.path.exists(file_path):
        print("✅ Weights already exist. Skipping download.")
        return

    url = "https://drive.google.com/uc?id=1--7p9rRJy7WU4OmomkzM8i0veetZctTT"
    print("⬇️ Downloading weights...")
    gdown.download(url, file_path, quiet=False)
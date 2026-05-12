import os
import shutil
import pandas as pd

csv_path = "dataset/Training_set.csv"
image_folder = "dataset/train"
output_folder = "dataset/train"

os.makedirs(f"{output_folder}/benign", exist_ok=True)
os.makedirs(f"{output_folder}/malignant", exist_ok=True)

df = pd.read_csv(csv_path)

# Clean column names
df.columns = df.columns.str.strip().str.lower()

print("Unique labels:", df['label'].unique())

for _, row in df.iterrows():
    img_name = row['filename']
    raw_label = str(row['label']).lower()

    if "benign" in raw_label:
        label = "benign"
    elif "malignant" in raw_label:
        label = "malignant"
    else:
        print(f"⚠️ Unknown label: {raw_label}")
        continue

    src = os.path.join(image_folder, img_name)
    dst = os.path.join(output_folder, label, img_name)

    if os.path.exists(src):
        shutil.copy(src, dst)

print("Dataset organized successfully!")
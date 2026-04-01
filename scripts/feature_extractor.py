import cv2
import os
import csv
import numpy as np
from pathlib import Path

# --- CONFIGURATION ---
DATASET_PATH = '../data/Dataset'
OUTPUT_FILE = 'riperadar_synthetic_dataset.csv'

# Define the target fruits we want for the project
TARGETS = ['Apple', 'Banana', 'Pear', 'Tomato']

def get_color_features(img_path):
    # Load image
    img = cv2.imread(str(img_path))
    if img is None:
        return None
    
    # Convert from BGR to RGB
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    # Calculate average R, G, B
    avg_color = np.mean(img, axis=(0, 1))
    r, g, b = avg_color
    
    # Feature Extraction: R/G Ratio
    # Formula: $$R/G = \frac{Red}{Green}$$
    rg_ratio = r / g if g > 0 else 0
    
    return [round(r, 2), round(g, 2), round(b, 2), round(rg_ratio, 4)]

print("🚀 Starting Feature Extraction...")

with open(OUTPUT_FILE, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(['label', 'sub_type', 'r', 'g', 'b', 'rg_ratio'])

    # Iterate through all subdirectories
    for folder in os.listdir(DATASET_PATH):
        folder_path = Path(DATASET_PATH) / folder
        
        if folder_path.is_dir():
            # Determine which target fruit this belongs to
            label = "Other"
            for t in TARGETS:
                if t in folder:
                    label = t
                    break
            
            print(f"Processing: {folder} (Label: {label})")
            
            # Process each image in the subfolder
            for img_name in os.listdir(folder_path):
                if img_name.lower().endswith(('.png', '.jpg', '.jpeg')):
                    features = get_color_features(folder_path / img_name)
                    if features:
                        writer.writerow([label, folder] + features)

print(f"✅ Finished! Dataset saved as {OUTPUT_FILE}")
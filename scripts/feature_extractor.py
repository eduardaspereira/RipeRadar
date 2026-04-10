import cv2
import os
import csv
import numpy as np
from pathlib import Path
from scipy.stats import entropy

# --- CONFIGURATION ---
DATASET_PATH = '../data/Dataset'
OUTPUT_FILE = 'riperadar_synthetic_dataset.csv'

# Define as frutas alvo
TARGETS = ['Apple', 'Banana', 'Pear', 'Tomato']

def get_color_features(img_path):
    # Carregar imagem
    img = cv2.imread(str(img_path))
    if img is None:
        return None
    
    # Converter para RGB e Gray (para entropia)
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 1. Médias de Cor
    avg_color = np.mean(img_rgb, axis=(0, 1))
    r, g, b = avg_color
    
    # 2. Variância (Mede a heterogeneidade)
    # Frutas com manchas terão variância mais alta
    var_color = np.var(img_rgb, axis=(0, 1))
    var_r, var_g, var_b = var_color
    
    # 3. Entropia de Shannon (Complexidade da textura)
    # Calculada no canal cinzento para representar a desordem visual global
    hist, _ = np.histogram(img_gray.ravel(), bins=256, range=(0, 255), density=True)
    color_entropy = entropy(hist + 1e-7, base=2) # Adicionamos um pequeno offset para evitar log(0)
    
    # 4. R/G Ratio
    rg_ratio = r / g if g > 0 else 0
    
    return [
        round(r, 2), round(g, 2), round(b, 2), 
        round(var_r, 2), round(var_g, 2), round(var_b, 2),
        round(color_entropy, 4), round(rg_ratio, 4)
    ]

print("🚀 A iniciar a extração de features melhorada...")

header = ['label', 'sub_type', 'r', 'g', 'b', 'var_r', 'var_g', 'var_b', 'entropy', 'rg_ratio']

with open(OUTPUT_FILE, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(header)

    for folder in os.listdir(DATASET_PATH):
        folder_path = Path(DATASET_PATH) / folder
        
        if folder_path.is_dir():
            label = "Other"
            for t in TARGETS:
                if t in folder:
                    label = t
                    break
            
            print(f"A processar: {folder} (Label: {label})")
            
            for img_name in os.listdir(folder_path):
                if img_name.lower().endswith(('.png', '.jpg', '.jpeg')):
                    features = get_color_features(folder_path / img_name)
                    if features:
                        writer.writerow([label, folder] + features)

print(f"✅ Concluído! Dataset guardado como {OUTPUT_FILE}")
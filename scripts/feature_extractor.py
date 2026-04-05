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
    
    # 1. Converter para RGB e Gray
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # NOVO: Criar uma máscara para ignorar o fundo (ajustado para ignorar o que for quase preto)
    # O valor '20' pode ser aumentado se o teu fundo for cinzento ou diminuído se for muito escuro
    _, mask = cv2.threshold(img_gray, 20, 255, cv2.THRESH_BINARY)
    
    # Filtrar píxeis da fruta
    pixels_fruta_rgb = img_rgb[mask == 255]
    pixels_fruta_gray = img_gray[mask == 255]
    
    # Segurança: Se a máscara estiver vazia (ex: imagem toda preta), ignoramos a imagem
    if len(pixels_fruta_rgb) == 0:
        return None

    # 2. Médias de Cor (Apenas nos píxeis da fruta)
    # cv2.mean devolve (R, G, B, Alpha)
    r, g, b, _ = cv2.mean(img_rgb, mask=mask)
    
    # 3. Variância (Apenas na fruta)
    var_r, var_g, var_b = np.var(pixels_fruta_rgb, axis=0)
    
    # 4. Entropia (Apenas na fruta)
    # Usamos o array filtrado de tons de cinza para medir a complexidade da textura
    hist, _ = np.histogram(pixels_fruta_gray, bins=256, range=(0, 255), density=True)
    color_entropy = entropy(hist + 1e-7, base=2)
    
    # 5. R/G Ratio
    rg_ratio = r / g if g > 0 else 0
    
    return [
        round(r, 2), round(g, 2), round(b, 2), 
        round(var_r, 2), round(var_g, 2), round(var_b, 2),
        round(color_entropy, 4), round(rg_ratio, 4)
    ]

print("🚀 A iniciar a extração de features com segmentação de fundo...")

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

print(f"✅ Concluído! O teu dataset filtrado foi guardado como {OUTPUT_FILE}")  
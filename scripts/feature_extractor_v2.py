"""
RipeRadar V2 - Advanced Feature Extraction Pipeline
====================================================
Extrai 20 features avançadas em vez de apenas 4 (R,G,B,R/G ratio)

Funcionalidades:
- Espaço de cor perceptual (LAB, HSV)
- Entropias e texturas
- Normalizações robustas a iluminação
- Pronto para integração com sensor temporal
"""

import cv2
import numpy as np
import pandas as pd
import csv
from pathlib import Path
from scipy.stats import entropy
from skimage.color import rgb2lab, rgb2hsv

# --- CONFIGURATION ---
DATASET_PATH = '../data/Dataset'
OUTPUT_FILE = 'riperadar_features_v2.csv'
TARGETS = ['Apple', 'Banana', 'Pear', 'Tomato']

def get_advanced_color_features(img_path):
    """
    Extrai 20 features avançadas de uma imagem de fruta.
    
    Returns: [features] lista de 20 valores numéricos
    """
    try:
        img = cv2.imread(str(img_path))
        if img is None:
            return None
        
        # 1. Pré-processamento: Máscara para ignorar fundo
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Segmentação: Tudo que não é preto é fruta (ajustar threshold se necessário)
        _, mask = cv2.threshold(img_gray, 20, 255, cv2.THRESH_BINARY)
        
        # Aplicar morphological closing para remover buracos
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        
        # Verificação de segurança
        if np.sum(mask) == 0:
            return None
        
        # Filtrar píxeis da fruta
        pixels_rgb = img_rgb[mask == 255]
        pixels_gray = img_gray[mask == 255]
        
        if len(pixels_rgb) < 100:  # Mínimo de píxeis detectados
            return None
        
        # ========== FEATURES DE COR (1-8) ==========
        
        # Feature 1-3: Médias RGB
        r_mean = np.mean(pixels_rgb[:, 0])
        g_mean = np.mean(pixels_rgb[:, 1])
        b_mean = np.mean(pixels_rgb[:, 2])
        
        # Feature 4: R/G Ratio (clássico)
        rg_ratio = r_mean / (g_mean + 1e-6)
        
        # Feature 5: B/(R+G) - "Blue Prominence" (cor mais escura = podridão)
        blue_prominence = b_mean / (r_mean + g_mean + 1e-6)
        
        # Feature 6: Saturação (mede quanto "vívida" é a cor)
        max_rgb = np.max(pixels_rgb, axis=1)
        min_rgb = np.min(pixels_rgb, axis=1)
        saturation = np.mean((max_rgb - min_rgb) / (max_rgb + 1e-6))
        
        # Feature 7-9: Espaço LAB (perceptualmente uniforme)
        pixels_lab = rgb2lab(pixels_rgb.astype(np.float32) / 255.0)
        l_mean = np.mean(pixels_lab[:, 0])
        a_mean = np.mean(pixels_lab[:, 1])
        b_mean_lab = np.mean(pixels_lab[:, 2])
        
        # Feature 10: Hue médio (HSV - ângulo da cor 0-360°)
        pixels_hsv = rgb2hsv(pixels_rgb.astype(np.float32) / 255.0)
        hue_mean = np.mean(pixels_hsv[:, 0]) * 360  # Converter para graus
        
        # ========== FEATURES DE VARIABILIDADE (9-12) ==========
        
        # Feature 11-13: Variância de cor (heterogeneidade)
        var_r = np.var(pixels_rgb[:, 0])
        var_g = np.var(pixels_rgb[:, 1])
        var_b = np.var(pixels_rgb[:, 2])
        color_variance = (var_r + var_g + var_b) / 3
        
        # Feature 14: Entropia de cor (complexidade cromática)
        hist_r, _ = np.histogram(pixels_rgb[:, 0], bins=32, range=(0, 255), density=True)
        hist_g, _ = np.histogram(pixels_rgb[:, 1], bins=32, range=(0, 255), density=True)
        hist_b, _ = np.histogram(pixels_rgb[:, 2], bins=32, range=(0, 255), density=True)
        color_entropy = (entropy(hist_r + 1e-7) + entropy(hist_g + 1e-7) + entropy(hist_b + 1e-7)) / 3
        
        # ========== FEATURES DE TEXTURA (13-16) ==========
        
        # Feature 15: Entropia de cinzentos (complexidade de textura)
        hist_gray, _ = np.histogram(pixels_gray, bins=256, range=(0, 255), density=True)
        gray_entropy = entropy(hist_gray + 1e-7, base=2)
        
        # Feature 16-17: Contraste local e nitidez (detecta bolor/textura fina)
        # Aplicar filtro Laplacian para detectar bordas/detalhes
        laplacian = cv2.Laplacian(img_gray, cv2.CV_64F)
        laplacian_masked = laplacian[mask == 255]
        edge_strength = np.mean(np.abs(laplacian_masked))
        edge_variance = np.var(laplacian_masked)
        
        # ========== FEATURES DE NORMALIZAÇÃO ROBUSTA (18-20) ==========
        
        # Feature 18: Distância Euclidiana normalizada ao perfil médio
        # (Será calibrada com frutas de referência no field)
        # Por agora, usar uma baseline teórica
        baseline_green_banana = np.array([100, 120, 50])  # RGB expected
        color_distance_normalized = np.sqrt(np.sum((np.array([r_mean, g_mean, b_mean]) - baseline_green_banana)**2)) / 255.0
        
        # Feature 19: Skewness da distribuição de brilho
        brightness_mean = np.mean(pixels_gray)
        brightness_std = np.std(pixels_gray)
        brightness_skew = np.mean(((pixels_gray - brightness_mean) / (brightness_std + 1e-6))**3)
        
        # Feature 20: Kurtosis (mede outliers - pode indicar bolor/fungos)
        brightness_kurtosis = np.mean(((pixels_gray - brightness_mean) / (brightness_std + 1e-6))**4) - 3
        
        # Compilar todas as 20 features
        features = [
            round(r_mean, 2),                      # 1
            round(g_mean, 2),                      # 2
            round(b_mean, 2),                      # 3
            round(rg_ratio, 4),                    # 4
            round(blue_prominence, 4),            # 5
            round(saturation, 4),                 # 6
            round(l_mean, 2),                      # 7 (LAB L)
            round(a_mean, 2),                      # 8 (LAB a - Vermelho/Verde)
            round(b_mean_lab, 2),                 # 9 (LAB b - Amarelo/Azul)
            round(hue_mean, 2),                    # 10 (HSV Hue)
            round(color_variance, 2),             # 11
            round(var_r, 2),                       # 12
            round(var_g, 2),                       # 13
            round(var_b, 2),                       # 14
            round(color_entropy, 4),              # 15
            round(gray_entropy, 4),               # 16
            round(edge_strength, 4),              # 17
            round(edge_variance, 4),              # 18
            round(color_distance_normalized, 4),  # 19
            round(brightness_skew, 4),            # 20
            round(brightness_kurtosis, 4)         # 21 (BONUS!)
        ]
        
        return features
    
    except Exception as e:
        print(f"❌ Erro ao processar {img_path}: {e}")
        return None


def main():
    print("🚀 RipeRadar V2: Extração de Features Avançadas")
    print(f"Dataset path: {DATASET_PATH}")
    print(f"Output file: {OUTPUT_FILE}\n")
    
    # Header das 21 features
    header = [
        'label', 'sub_type',
        'r_mean', 'g_mean', 'b_mean',                    # 1-3
        'rg_ratio', 'blue_prominence', 'saturation',     # 4-6
        'lab_l', 'lab_a', 'lab_b', 'hue_mean',          # 7-10
        'color_variance', 'var_r', 'var_g', 'var_b',    # 11-14
        'color_entropy', 'gray_entropy',                 # 15-16
        'edge_strength', 'edge_variance',                # 17-18
        'color_distance_norm', 'brightness_skew',       # 19-20
        'brightness_kurtosis'                            # 21
    ]
    
    processed_count = 0
    skipped_count = 0
    
    with open(OUTPUT_FILE, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(header)
        
        dataset_path = Path(DATASET_PATH)
        
        for folder in sorted(dataset_path.iterdir()):
            if not folder.is_dir():
                continue
            
            # Identificar label da fruta
            label = "Other"
            for target in TARGETS:
                if target in folder.name:
                    label = target
                    break
            
            print(f"📁 Processando: {folder.name:30} (Label: {label})")
            
            images = list(folder.glob('*.[jJ][pP][gG]')) + list(folder.glob('*.[pP][nN][gG]'))
            
            for img_path in images:
                features = get_advanced_color_features(img_path)
                
                if features is not None:
                    writer.writerow([label, folder.name] + features)
                    processed_count += 1
                    
                    # Progress
                    if processed_count % 10 == 0:
                        print(f"   ✓ {processed_count} imagens processadas")
                else:
                    skipped_count += 1
    
    print(f"\n✅ Extração completa!")
    print(f"   Processadas: {processed_count} imagens")
    print(f"   Skipped: {skipped_count} imagens")
    print(f"   Arquivo: {OUTPUT_FILE}")
    
    # Mostrar estatísticas do dataset
    df = pd.read_csv(OUTPUT_FILE)
    print(f"\n📊 Dataset Shape: {df.shape}")
    print(f"Distribuição de labels:")
    print(df['label'].value_counts())


if __name__ == "__main__":
    main()

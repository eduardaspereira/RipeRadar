import time
import board
import adafruit_tcs34725
import joblib
import pandas as pd
import numpy as np

# 1. Carregar o modelo treinado
model = joblib.load('riperadar_model.pkl')

# 2. Configuração do Sensor
i2c = board.I2C()
sensor = adafruit_tcs34725.TCS34725(i2c)

# Define os nomes exatos das features usados durante o treino
# ATENÇÃO: Se treinaste o modelo com variância e entropia, tens de as adicionar aqui!
FEATURE_NAMES = ['r', 'g', 'b', 'rg_ratio']

print("🍎 RipeRadar Live: Pronto para identificar fruta!")

try:
    while True:
        # Obter valores brutos do sensor
        r_raw, g_raw, b_raw, clear = sensor.color_raw
        
        if clear > 0:
            # --- NORMALIZAÇÃO ---
            # Transformar em percentagem (0 a 1) para ignorar variações de luminosidade
            r = r_raw / clear
            g = g_raw / clear
            b = b_raw / clear
            
            # Cálculo do R/G Ratio baseado nos valores normalizados
            rg_ratio = r / g if g > 0 else 0
            
            # Criar o DataFrame com os nomes das colunas para o modelo
            current_data = pd.DataFrame([[r, g, b, rg_ratio]], columns=FEATURE_NAMES)
            
            # Predição
            prediction = model.predict(current_data)[0]
            probs = model.predict_proba(current_data)
            confidence = np.max(probs)
            
            # Mostrar resultado na consola
            print(f"\r🔍 Predição: {prediction:10} | Confiança: {confidence:.2%}", end="")
            
        time.sleep(0.5)
except KeyboardInterrupt:
    print("\nA parar...")
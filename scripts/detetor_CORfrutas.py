import time
import board
import adafruit_tcs34725
import serial  # Para comunicar com o Nicla/Portenta conforme o plano 

# 1. Configuração do Hardware
i2c = board.I2C()
color_sensor = adafruit_tcs34725.TCS34725(i2c)
color_sensor.integration_time = 154
color_sensor.gain = 4

# Tenta abrir a porta serial para o Nicla Sense ME (ajusta a porta se necessário)
try:
    ser = serial.Serial('/dev/ttyACM0', 9600, timeout=1)
except:
    ser = None
    print("Aviso: Nicla Sense ME não detectado via Serial. A usar modo apenas cor.")

# 2. Base de Conhecimento (Perfis Normalizados: R/C, G/C, B/C)
# Estes valores devem ser afinados na tua Semana 2 de calibração [cite: 31]
FRUIT_PROFILES = {
    "Banana": {"color": [0.44, 0.41, 0.15], "gas_threshold": 50},
    "Maçã":   {"color": [0.58, 0.22, 0.20], "gas_threshold": 30},
    "Pêra":   {"color": [0.35, 0.48, 0.17], "gas_threshold": 40}
}

def identify_fruit(r_n, g_n, b_n, gas_level):
    best_match = "Desconhecido"
    min_distance = 1.0  # Valor alto inicial
    
    for fruit, data in FRUIT_PROFILES.items():
        # Cálculo da Distância Euclidiana entre a leitura e o perfil
        dist = ((r_n - data["color"][0])**2 + 
                (g_n - data["color"][1])**2 + 
                (b_n - data["color"][2])**2)**0.5
        
        if dist < min_distance:
            min_distance = dist
            best_match = fruit
            
    # Refinamento com dados do Nicla Sense ME (Gás/Etileno) [cite: 15]
    if gas_level > 200: # Se o gás for absurdamente alto, algo está errado ou muito podre
        return f"{best_match} (Estado Crítico/Podre)"
        
    return best_match, min_distance

print("--- RipeRadar: Sistema de Identificação Ativo ---")

try:
    while True:
        # A. Leitura do Sensor de Cor
        r, g, b, c = color_sensor.color_raw
        if c == 0: continue
        
        # Normalização para evitar erros de brilho
        r_n, g_n, b_n = r/c, g/c, b/c
        
        # B. Leitura do Nicla Sense ME (via Serial) 
        gas_val = 0
        if ser and ser.in_waiting > 0:
            try:
                line = ser.readline().decode('utf-8').strip()
                gas_val = float(line) # Assume que o Nicla envia apenas o valor do gás
            except:
                pass

        # C. Identificação
        fruit, confidence = identify_fruit(r_n, g_n, b_n, gas_val)
        
        # D. Output Visual
        # Criar um quadrado colorido no terminal para tu veres o que o sensor vê
        r8, g8, b8 = color_sensor.color_rgb_bytes
        square = f"\x1b[48;2;{r8};{g8};{b8}m    \x1b[0m"
        
        print(f"\r{square} Aposta do RipeRadar: {fruit:10} (Confiança: {1-confidence:.2%})", end="")
        
        time.sleep(0.5)

except KeyboardInterrupt:
    print("\nSistema encerrado pelo utilizador.")
import time
import board
import adafruit_tcs34725

# Configuração do Sensor Layer [cite: 8]
i2c = board.I2C()
sensor = adafruit_tcs34725.TCS34725(i2c)

# Perfis baseados em normalização (R/C, G/C, B/C)
PERFIS_EXPERT = {
    "Banana": {"r_c": 0.38, "g_c": 0.42, "b_c": 0.20, "gas_ref": 20},
    "Maçã":   {"r_c": 0.45, "g_c": 0.38, "b_c": 0.17, "gas_ref": 45},
    "Pêra":   {"r_c": 0.32, "g_c": 0.48, "b_c": 0.20, "gas_ref": 15}
}

def identificar_expert(rn, gn, bn, clear, gas):
    votos = {"Banana": 0, "Maçã": 0, "Pêra": 0}
    
    for fruta, p in PERFIS_EXPERT.items():
        # 1. Distância de Cor
        dist = ((rn - p["r_c"])**2 + (gn - p["g_c"])**2 + (bn - p["b_c"])**2)**0.5
        votos[fruta] += (1 - dist) * 0.6  # Peso de 60% para a cor
        
        # 2. Peso do Gás (Nicla Sense ME)
        if abs(gas - p["gas_ref"]) < 10:
            votos[fruta] += 0.4  # Peso de 40% para o gás 
            
    return max(votos, key=votos.get)

def get_status(fruit, rg_ratio, gas_level):
    # Lógica de decisão do Edge AI Layer [cite: 10, 23]
    ripe_limit = PROFILES[fruit]["threshold_ripe"]
    
    if rg_ratio < (ripe_limit * 0.8):
        return "Verde (Fresh)"
    elif rg_ratio >= ripe_limit:
        if gas_level > 100: # Se o Nicla detectar gás alto [cite: 15]
            return "Podre (Rotten)"
        return "Madura (Ripe)"
    return "A amadurecer"

try:
    print("🚀 RipeRadar: Sistema Integrado Ativo")
    while True:
        r, g, b, c = sensor.color_raw
        if c == 0: continue
        
        # Normalização [cite: 20]
        rn, gn, bn = r/c, g/c, b/c
        rg_ratio = r/g if g > 0 else 0
        
        # 1. Identificar a fruta (Distância Euclidiana)
        best_fruit = "Desconhecida"
        min_dist = 1.0
        for name, p in PROFILES.items():
            dist = ((rn - p["r_n"])**2 + (gn - p["g_n"])**2)**0.5
            if dist < min_dist:
                min_dist = dist
                best_fruit = name
        
        # 2. Verificar Maturação (Simulando entrada do Nicla Sense ME [cite: 15])
        gas_simulado = 20 # Substituir pela leitura Serial do Portenta C33 [cite: 18]
        estado = get_status(best_fruit, rg_ratio, gas_simulado)
        
        print(f"\rFruta: {best_fruit:7} | R/G: {rg_ratio:.2f} | Estado: {estado:15}", end="")
        time.sleep(0.5)

except KeyboardInterrupt:
    print("\nParado.")
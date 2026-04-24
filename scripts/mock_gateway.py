import paho.mqtt.client as mqtt
import json
import time
import random

MQTT_BROKER = "127.0.0.1"
MQTT_TOPIC = "riperadar/telemetry"

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.connect(MQTT_BROKER, 1883, 60)

print("🚀 Simulador de Gateway RipeRadar iniciado...")

while True:
    # Simular dados do Nicla e Nano
    gas = random.uniform(30000, 60000)
    temp = random.uniform(18, 28)
    
    # Criar o payload exatamente como o teu script original
    payload = {
        "device_id": "ripe_radar_gateway_01",
        "timestamp": int(time.time()),
        "environment": {
            "temperature_c": round(temp, 2),
            "humidity_percent": random.randint(40, 60),
            "gas_resistance_ohms": round(gas, 2),
            "baro_hpa": 1013.25
        },
        "final_decision": {
            "class": random.choice(["maca_fresca", "maca_podre", "banana_fresca"]),
            "confidence": random.randint(70, 95),
            "esf_penalty_applied": random.randint(0, 15)
        }
    }
    
    client.publish(MQTT_TOPIC, json.dumps(payload))
    print(f"📡 Dados enviados para {MQTT_TOPIC}")
    time.sleep(5)
import asyncio
import struct
import json
import time
import paho.mqtt.client as mqtt
from bleak import BleakClient, BleakScanner

# ==========================================
# MQTT CONFIGURATION
# ==========================================
MQTT_BROKER = "127.0.0.1" # Localhost, since broker is on the same Pi
MQTT_PORT = 1883
MQTT_TOPIC = "riperadar/telemetry"

# Initialize MQTT Client
mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "Gateway_Pi5")

try:
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    mqtt_client.loop_start() # Run MQTT network loop in the background
    print(f"✅ Conectado ao broker MQTT em {MQTT_BROKER}:{MQTT_PORT}")
except Exception as e:
    print(f"❌ Erro ao conectar ao MQTT: {e}")

# ==========================================
# CONFIGURATION & UUIDS
# ==========================================
NANO_NAME = "Nano_Camera"
NICLA_NAME = "NiclaSenseME"

# Nano Camera UUID
CAMERA_CHAR_UUID = "19b10001-e8f2-537e-4f6c-d104768a1214"

# Nicla Sense ME UUIDs
NICLA_TEMP_UUID  = "19b10001-e8f2-537e-4f6c-d104768a1214"
NICLA_GAS_UUID   = "19b10002-e8f2-537e-4f6c-d104768a1214"
NICLA_BARO_UUID  = "19b10003-e8f2-537e-4f6c-d104768a1214"
NICLA_HUM_UUID   = "19b10004-e8f2-537e-4f6c-d104768a1214"

CLASSES = [
    "banana_fresca", "banana_podre",
    "laranja_fresca", "laranja_podre",
    "maca_fresca", "maca_podre"
]

# Global dictionary to hold the latest Nicla sensor readings
latest_env = {
    "temp": 20.0,
    "gas": 100000.0, # Default high resistance (clean air)
    "baro": 1000.0,
    "hum": 50.0
}

stop_event = asyncio.Event()

# ==========================================
# NICLA HANDLERS (Unpacking 4-byte Floats)
# ==========================================
def temp_handler(sender, data):
    latest_env["temp"] = struct.unpack('<f', data)[0]

def gas_handler(sender, data):
    latest_env["gas"] = struct.unpack('<f', data)[0]

def baro_handler(sender, data):
    latest_env["baro"] = struct.unpack('<f', data)[0]

def hum_handler(sender, data):
    latest_env["hum"] = struct.unpack('<f', data)[0]

# ==========================================
# NANO CAMERA HANDLER & SENSOR FUSION
# ==========================================
def camera_notification_handler(sender, data):
    mensagem = data.decode('utf-8').strip()
    
    if not mensagem or ',' not in mensagem:
        return
        
    try:
        valores_percentuais = [int(v) for v in mensagem.split(',')]
        
        if len(valores_percentuais) == len(CLASSES):
            prob_camera = dict(zip(CLASSES, valores_percentuais))
            
            print("\n" + "="*40)
            print("📡 NOVOS DADOS RECEBIDOS")
            print("="*40)
            print(f"🌡️  Ambiente atual -> Temp: {latest_env['temp']:.1f}ºC | Hum: {latest_env['hum']:.1f}% | Gás (VOC): {latest_env['gas']:.0f} Ω")
            
            print("\n📷 Confiança Base da Câmara:")
            for fruta, prob in prob_camera.items():
                if prob > 0:
                    print(f"   {fruta}: {prob}%")
            
            # ----------------------------------------------------
            # CONTINUOUS SENSOR FUSION CALCULUS
            # ----------------------------------------------------
            fusion_results = prob_camera.copy()
            
            # Constants for calibration (You should measure these in your tests)
            R_CLEAN = 50000.0  # Baseline resistance in clean air (Ohms)
            T_OPT = 20.0       # Optimal storage temperature (Celsius)
            T_MAX = 35.0       # Maximum expected temperature
            
            # Weights for the Environmental Stress Factor (ESF)
            W_GAS = 0.20       # Gas contributes up to 20% shift
            W_TEMP = 0.05      # Temp contributes up to 5% shift
            
            # Calculate Gas Stress (0.0 to 1.0)
            # If current gas is higher than clean air, stress is 0
            gas_stress = max(0, (R_CLEAN - latest_env["gas"]) / R_CLEAN)
            
            # Calculate Temperature Stress (0.0 to 1.0)
            temp_stress = max(0, (latest_env["temp"] - T_OPT) / (T_MAX - T_OPT))
            # Cap temp stress at 1.0 just in case
            temp_stress = min(1.0, temp_stress) 
            
            # Calculate total Environmental Stress Factor (ESF)
            # This represents the total percentage points to shift from fresh to rotten
            esf_shift_percentage = int((W_GAS * gas_stress + W_TEMP * temp_stress) * 100)
            
            # Apply the continuous modifier to the pairs
            for fruit_base in ["banana", "laranja", "maca"]:
                fresh_key = f"{fruit_base}_fresca"
                rotten_key = f"{fruit_base}_podre"
                
                # Only apply if the camera detected this fruit
                if prob_camera[fresh_key] > 0 or prob_camera[rotten_key] > 0:
                    
                    # Shift probability from fresh to rotten based on ESF
                    # Ensure we don't subtract more "fresh" confidence than actually exists
                    shift_amount = min(fusion_results[fresh_key], esf_shift_percentage)
                    
                    fusion_results[fresh_key] -= shift_amount
                    fusion_results[rotten_key] += shift_amount

            # ==========================================
            # NEW: BUILD JSON AND PUBLISH TO MQTT
            # ==========================================
            # Find the dominant fruit post-fusion
            dominant_class = max(fusion_results, key=fusion_results.get)
            confidence = fusion_results[dominant_class]

            payload = {
                "device_id": "ripe_radar_gateway_01",
                "timestamp": int(time.time()),
                "environment": {
                    "temperature_c": round(latest_env["temp"], 2),
                    "humidity_percent": round(latest_env["hum"], 2),
                    "gas_resistance_ohms": round(latest_env["gas"], 2),
                    "baro_hpa": round(latest_env["baro"], 2)
                },
                "camera_base_inference": prob_camera,
                "fusion_results": fusion_results,
                "final_decision": {
                    "class": dominant_class,
                    "confidence": confidence,
                    "esf_penalty_applied": esf_shift_percentage
                }
            }
            # Convert dictionary to JSON string and publish
            json_payload = json.dumps(payload)
            mqtt_client.publish(MQTT_TOPIC, json_payload)
            print(f"Payload publicado no MQTT (Tópico: {MQTT_TOPIC})")

    except ValueError:
        pass

# ==========================================
# CONNECTION TASKS
# ==========================================
async def connect_nicla(device):
    try:
        async with BleakClient(device, timeout=30.0) as client:
            print(f"[Nicla] Conectado a {device.address}")
            await client.start_notify(NICLA_TEMP_UUID, temp_handler)
            await client.start_notify(NICLA_GAS_UUID, gas_handler)
            await client.start_notify(NICLA_BARO_UUID, baro_handler)
            await client.start_notify(NICLA_HUM_UUID, hum_handler)
            print("[Nicla] Subscrições ativas. A recolher dados ambientais...")
            await stop_event.wait()
    except Exception as e:
        print(f"[Nicla] Falha na conexão: {e}")

async def connect_nano(device):
    try:
        async with BleakClient(device, timeout=30.0) as client:
            print(f"[Nano] Conectado a {device.address}")
            await client.start_notify(CAMERA_CHAR_UUID, camera_notification_handler)
            print("[Nano] Subscrição ativa. À escuta da câmara...")
            await stop_event.wait()
    except Exception as e:
        print(f"[Nano] Falha na conexão: {e}")

async def main():
    print("A procurar dispositivos Bluetooth...")
    devices = await BleakScanner.discover(timeout=5.0)
    
    nano_device = next((d for d in devices if d.name == NANO_NAME), None)
    nicla_device = next((d for d in devices if d.name == NICLA_NAME), None)
    
    if not nano_device:
        print(f"❌ {NANO_NAME} não encontrado.")
    if not nicla_device:
        print(f"❌ {NICLA_NAME} não encontrado.")
        
    if not nano_device or not nicla_device:
        print("Certifica-te que ambos os arduinos estão ligados. A terminar.")
        return

    print("Dispositivos encontrados! A iniciar ligações simultâneas...")
    
    # Run both BLE connection loops at the same time
    await asyncio.gather(
        connect_nicla(nicla_device),
        connect_nano(nano_device)
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nPrograma terminado.")
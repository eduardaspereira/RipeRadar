import asyncio
import re
import os
import json
from dotenv import load_dotenv
from bleak import BleakClient, BleakScanner
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# 1. Carregamento de credenciais
load_dotenv()
INFLUX_URL = os.getenv("INFLUX_URL")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN")
INFLUX_ORG = os.getenv("INFLUX_ORG")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET")

# Inicializacao da base de dados InfluxDB
client_db = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = client_db.write_api(write_options=SYNCHRONOUS)

# Semáforo para evitar colisões no adaptador Bluetooth do Raspberry Pi
ble_scan_lock = asyncio.Lock()

# Memoria de Estado Global (Late Fusion Buffer)
system_state = {
    "temp": 0.0, 
    "hum": 0.0, 
    "hPa": 0.0, 
    "voc_gas": 0.0,
    "classe_dominante": "Desconhecido", 
    "confianca": 0.0
}

def enviar_telemetria():
    """Constroi e envia o pacote de dados fundidos para o InfluxDB."""
    # O measurement foi alterado para refletir o que o projeto realmente é
    point = (
        Point("mqtt_consumer")
        .field("temp", system_state["temp"])
        .field("hum", system_state["hum"])
        .field("hPa", system_state["hPa"])
        .field("voc_gas", system_state["voc_gas"])
        .field("classe_dominante", system_state["classe_dominante"])
        .field("confianca", system_state["confianca"])
    )
    try:
        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)
    except Exception as e:
        print(f"[ERROR] Falha na escrita para InfluxDB: {e}")

def nicla_handler(sender, data):
    """Processa pacotes BLE vindos do Nicla Sense ME (Gases)."""
    payload = data.decode('utf-8').strip()
    nums = re.findall(r"[-+]?\d*\.\d+|\d+", payload)
    
    if len(nums) >= 4:
        system_state["temp"] = float(nums[0])
        system_state["hum"] = float(nums[1])
        system_state["hPa"] = float(nums[2])
        system_state["voc_gas"] = float(nums[3])
        
        print(f"[SENSE] Temp: {system_state['temp']}C | Hum: {system_state['hum']}% | VOC: {system_state['voc_gas']} Ohm")
        enviar_telemetria()

def vision_handler(sender, data):
    """Processa pacotes BLE vindos do Arduino Nano 33 (Visao IA)."""
    payload = data.decode('utf-8').strip()
    try:
        vision_data = json.loads(payload)
        if "classe_dominante" in vision_data and "confianca" in vision_data:
            system_state["classe_dominante"] = vision_data["classe_dominante"]
            system_state["confianca"] = float(vision_data["confianca"])
            
            print(f"[VISION] Alvo: {system_state['classe_dominante']} | Certeza: {system_state['confianca']}")
            enviar_telemetria()
    except json.JSONDecodeError:
        print(f"[WARN] Payload JSON invalido recebido da Camara: {payload}")

async def gerir_conexao(nome_dispositivo, char_uuid, handler):
    """Tarefa assincrona para manter conexao BLE estavel baseada em eventos."""
    
    # Evento para detetar quando o Bluetooth cai de forma passiva (não bloqueante)
    disconnect_event = asyncio.Event()

    def handle_disconnect(_):
        # Quando o Arduino ou o Nicla perdem o sinal, este evento é ativado
        disconnect_event.set()

    while True:
        try:
            # Pede autorização ao Lock antes de usar o scanner Bluetooth
            async with ble_scan_lock:
                device = await BleakScanner.find_device_by_name(nome_dispositivo, timeout=10.0)
            
            if device:
                disconnect_event.clear()
                # Configura o callback de desconexão
                async with BleakClient(device, timeout=15.0, disconnected_callback=handle_disconnect) as client:
                    await client.start_notify(char_uuid, handler)
                    
                    # O script fica aqui parado a dormir de forma extremamente eficiente
                    # até o dispositivo cortar a ligação (como acontece com a câmara)
                    await disconnect_event.wait()
                        
        except Exception as e:
                print(f"[ERROR] Excecao Bluetooth em {nome_dispositivo}: {repr(e)}")
                
        # Pausa antes de tentar reconectar
        await asyncio.sleep(1)


async def main():
    print("[SYSTEM] RipeRadar Multi-Sensor Gateway Iniciado.")
    print("[SYSTEM] Orquestrador Assincrono ativado. Pressione Ctrl+C para abortar.\n")
    
    # Cria as tarefas assincronas
    tarefa_nicla = asyncio.create_task(gerir_conexao("RipeRadar", "19B10001-E8F2-537E-4F6C-D104768A1214", nicla_handler))
    
    # Dá 2 segundos para o rádio Bluetooth do Raspberry Pi "respirar" antes de lançar a segunda
    await asyncio.sleep(2) 
    
    tarefa_visao = asyncio.create_task(gerir_conexao("Arduino33", "19B10011-E8F2-537E-4F6C-D104768A1214", vision_handler))
    
    # Executa ambas
    await asyncio.gather(tarefa_nicla, tarefa_visao)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[SYSTEM] Encerramento forçado do Gateway.")
import asyncio
import re
import os
from dotenv import load_dotenv
from bleak import BleakClient, BleakScanner
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# 1. Carregamento de credenciais ambientais
load_dotenv()
INFLUX_URL = os.getenv("INFLUX_URL")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN")
INFLUX_ORG = os.getenv("INFLUX_ORG")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET")

# Identificadores BLE
NICLA_NAME = "RipeRadar"
CHAR_UUID = "19B10001-E8F2-537E-4F6C-D104768A1214"

# Inicializacao do cliente de base de dados temporal
client_db = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = client_db.write_api(write_options=SYNCHRONOUS)

def notification_handler(sender, data):
    """Callback executado na rececao de novos pacotes BLE."""
    payload = data.decode('utf-8').strip()
    nums = re.findall(r"[-+]?\d*\.\d+|\d+", payload)
    
    if len(nums) >= 4:
        temp = float(nums[0])
        hum = float(nums[1])
        hpa = float(nums[2])
        voc = float(nums[3])

        print(f"[DATA] Temp: {temp} C | Hum: {hum} % | hPa: {hpa} | VOC: {voc} Ohm")

        point = (
            Point("mqtt_consumer")
            .field("temp", temp)
            .field("hum", hum)
            .field("hPa", hpa)
            .field("voc_gas", voc)
            #.field("classe_dominante", "laranja") # Parametro estatico para validacao estrutural
            #.field("confianca", 95.5)             # Parametro estatico para validacao estrutural
        )

        try:
            write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)
            print("[INFO] Transmissao para InfluxDB concluida.")
        except Exception as e:
            print(f"[ERROR] Falha na escrita para InfluxDB: {e}")

async def main():
    print(f"[SYSTEM] Inicializando modulo de recepcao BLE. Alvo: {NICLA_NAME}")

    while True:
        try:
            device = await BleakScanner.find_device_by_name(NICLA_NAME, timeout=5.0)
            
            if device:
                print(f"[INFO] Hardware detetado ({device.address}). A negociar conexao...")
                
                async with BleakClient(device) as client:
                    print("[INFO] Conexao BLE ativa. A aguardar telemetria...")
                    
                    await client.start_notify(CHAR_UUID, notification_handler)
                    
                    while client.is_connected:
                        await asyncio.sleep(1)
                        
                print("[WARN] Conexao perdida. A iniciar protocolo de reconexao...")
            else:
                print("[SCAN] Alvo nao detetado. Nova tentativa em curso...")
                await asyncio.sleep(2)
                
        except KeyboardInterrupt:
            print("\n[SYSTEM] Interrupcao manual do sistema (SIGINT).")
            break
        except Exception as e:
            print(f"[ERROR] Excecao na interface Bluetooth: {e}. Retentando...")
            await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(main())
import serial
import time
import re
import os
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# 1. Carregar variáveis seguras
load_dotenv()
INFLUX_URL = os.getenv("INFLUX_URL")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN")
INFLUX_ORG = os.getenv("INFLUX_ORG")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET")

SERIAL_PORT = '/dev/ttyACM0'
BAUD_RATE = 115200

def main():
    print("🚀 A iniciar leitura do Nicla Sense ME (USB)...")

    # Iniciar cliente InfluxDB
    try:
        client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
        write_api = client.write_api(write_options=SYNCHRONOUS)
    except Exception as e:
        print(f"❌ Erro de configuração do InfluxDB: {e}")
        return

    # Iniciar porta Serial
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.5)
        print(f"✅ Conectado à porta {SERIAL_PORT}")
    except Exception as e:
        print(f"❌ Erro ao abrir a porta serial: {e}")
        return

    # O nosso "Buffer" (Memória temporária para juntar as linhas do Arduino)
    sensor_data = {"temp": None, "hum": 0.0, "hPa": 1013.2, "voc_gas": None}

    while True:
        try:
            if ser.in_waiting > 0:
                # Ler a linha crua do USB
                raw_line = ser.readline().decode('utf-8', errors='ignore').strip()
                
                # Extrair apenas os números
                nums = re.findall(r"[-+]?\d*\.\d+|\d+", raw_line)

                # 1. Capturar Temperatura e Humidade
                if "TEMP" in raw_line.upper() and len(nums) >= 1:
                    sensor_data["temp"] = float(nums[0])
                    if len(nums) >= 2:
                        sensor_data["hum"] = float(nums[1])

                # 2. Capturar Pressão (Caso adiciones no Arduino futuramente)
                elif "BARO" in raw_line.upper() and len(nums) >= 1:
                    sensor_data["hPa"] = float(nums[0])

                # 3. Capturar Gás (VOC)
                elif "GAS" in raw_line.upper() and len(nums) >= 1:
                    sensor_data["voc_gas"] = float(nums[0])

                # 4. Quando tivermos o pacote essencial (Temp + Gas), enviamos!
                if sensor_data["temp"] is not None and sensor_data["voc_gas"] is not None:
                    print(f"📡 Pacote Lido -> Temp: {sensor_data['temp']}ºC | Hum: {sensor_data['hum']}% | Gas: {sensor_data['voc_gas']}Ω")

                    # Montar o pacote para o InfluxDB
                    point = (
                        Point("mqtt_consumer")
                        .field("temp", sensor_data["temp"])
                        .field("hum", sensor_data["hum"])
                        .field("hPa", sensor_data["hPa"])
                        .field("voc_gas", sensor_data["voc_gas"])
                        .field("classe_dominante", "laranja") # Fixo para não quebrar a dashboard
                        .field("confianca", 95.5)             # Fixo para não quebrar a dashboard
                    )

                    write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)
                    print("☁️ Enviado para a Cloud!")

                    # Limpar a memória para construir o próximo pacote
                    sensor_data = {"temp": None, "hum": 0.0, "hPa": 1013.2, "voc_gas": None}

        except KeyboardInterrupt:
            print("\n🛑 Script parado.")
            break
        except Exception as e:
            # Ignora pequenos erros de leitura do USB para não estoirar o programa
            pass

    ser.close()
    client.close()

if __name__ == "__main__":
    main()
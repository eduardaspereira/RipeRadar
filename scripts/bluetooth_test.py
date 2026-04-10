import asyncio
from bleak import BleakClient, BleakScanner

CHARACTERISTIC_UUID = "19b10001-e8f2-537e-4f6c-d104768a1214"
DEVICE_NAME = "Nano_Camera"

CLASSES = [
    "banana_fresca", "banana_podre",
    "laranja_fresca", "laranja_podre",
    "maca_fresca", "maca_podre"
]

# Evento para manter o programa aberto em loop infinito sem gastar CPU
stop_event = asyncio.Event()

def disconnected_callback(client):
    print("\n[Aviso] A liga��o Bluetooth caiu. Reinicia o script se necess�rio.")
    stop_event.set()

def notification_handler(sender, data):
    """Ativado de forma passiva APENAS quando o Arduino envia os dados"""
    mensagem = data.decode('utf-8').strip()
    
    if not mensagem or ',' not in mensagem:
        return
        
    try:
        valores_percentuais = [int(v) for v in mensagem.split(',')]
        
        if len(valores_percentuais) == len(CLASSES):
            prob_camera = dict(zip(CLASSES, valores_percentuais))
            
            print("\n--- Pontua��es da IA (C�mara) ---")
            for fruta, prob in prob_camera.items():
                print(f"{fruta}: {prob}%")
                
            # ====================================================
            # AQUI ENTRA A TUA MATEM�TICA DE FUS�O DE SENSORES
            # ====================================================
            # Exemplo Fict�cio: Imagina que tens uma fun��o ler_sensor_gas()
            # prob_gas_podre = ler_sensor_gas()
            # pontuacao_final_laranja = (prob_camera['laranja_podre'] * 0.6) + (prob_gas_podre * 0.4)
            # print(f"Pontua��o H�brida Laranja Podre: {pontuacao_final_laranja}%")
            
    except ValueError:
        print("Pacote corrompido ou incompleto, a ignorar...")

async def run():
    print(f"\nA procurar pelo dispositivo {DEVICE_NAME}...")
    device = await BleakScanner.find_device_by_filter(
        lambda d, ad: ad.local_name == DEVICE_NAME
    )

    if not device:
        print("Arduino n�o encontrado. Tenta de novo.")
        return

    print(f"Encontrado! Tentando conectar a {device.address}...")
    
    try:
        async with BleakClient(device, disconnected_callback=disconnected_callback, timeout=30.0) as client:
            print("Conex�o estabelecida com sucesso! A subscrever imediatamente...")
            
            # 1. SUBSCREVER LOGO! (Aproveitamos a pausa inicial de 2s do Arduino)
            await client.start_notify(CHARACTERISTIC_UUID, notification_handler)
            print("Subscrito com sucesso! � escuta passiva de resultados...")
            
            # 2. FICAR PARADO AQUI.
            await stop_event.wait()
            
    except Exception as e:
        print(f"Falha na conex�o: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("\nPrograma terminado pelo utilizador.")
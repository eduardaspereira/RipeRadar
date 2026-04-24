import asyncio
from bleak import BleakClient, BleakScanner

# --- Constants & Configuration ---
CAMERA_DEVICE_NAME = "Nano_Camera"
NICLA_DEVICE_NAME = "Nicla_Sense" # Assuming your Nicla is broadcasting with this name

CAMERA_UUID = "19b10001-e8f2-537e-4f6c-d104768a1214"
# You will need to define the UUID for your Nicla Sense ME gas/temp characteristic
NICLA_UUID = "19b10002-e8f2-537e-4f6c-d104768a1214" 

CLASSES = [
    "banana_fresca", "banana_podre",
    "laranja_fresca", "laranja_podre",
    "maca_fresca", "maca_podre"
]

# Standard maximum shelf life at room temperature (in days)
MAX_LIFETIME_DAYS = {
    "banana": 7.0,
    "laranja": 14.0,
    "maca": 21.0
}

stop_event = asyncio.Event()

# Global variables to store the latest sensor readings
latest_environmental_data = {
    "temperature_c": 20.0, # Default room temp
    "voc_index": 0.0       # 0 (clean) to 100 (high ethylene/spoilage gas)
}

def calculate_shelf_life(camera_probs):
    """
    Fuses camera AI data with Nicla Sense ME environmental data to estimate lifetime.
    """
    # 1. Identify the detected fruit (e.g., 'maca', 'banana')
    detected_fruit = None
    max_prob = -1
    for fruit_class, prob in camera_probs.items():
        if prob > max_prob:
            max_prob = prob
            detected_fruit = fruit_class.split('_')[0]

    if not detected_fruit:
        return

    # 2. Extract specific probabilities
    prob_fresca = camera_probs.get(f"{detected_fruit}_fresca", 0)
    prob_podre = camera_probs.get(f"{detected_fruit}_podre", 0)
    
    # Normalize visual rottenness (ignore other fruits in the frame)
    total_fruit_prob = prob_fresca + prob_podre
    if total_fruit_prob == 0:
        return
    visual_rotten_score = (prob_podre / total_fruit_prob) * 100

    # 3. Retrieve environmental data (from Nicla Sense ME)
    temp = latest_environmental_data["temperature_c"]
    voc = latest_environmental_data["voc_index"]

    # 4. Calculate Temperature Penalty (Optimal ~15C, higher temp = faster rotting)
    optimal_temp = 15.0
    temp_penalty = max(0, (temp - optimal_temp) * 5) # 5% penalty per degree over optimal
    temp_penalty = min(temp_penalty, 100) # Cap at 100%

    # 5. Sensor Fusion Mathematics
    # Weights: 50% Vision, 35% Gas/VOCs, 15% Temperature
    w_vis = 0.50
    w_gas = 0.35
    w_tmp = 0.15

    decay_index = (w_vis * visual_rotten_score) + (w_gas * voc) + (w_tmp * temp_penalty)
    
    # 6. Estimate Remaining Days
    max_days = MAX_LIFETIME_DAYS.get(detected_fruit, 10.0)
    remaining_days = max_days * (1 - (decay_index / 100))
    remaining_days = max(0.0, round(remaining_days, 1)) # Prevent negative days

    print(f"\n================ RipeRadar Fusion Report ================")
    print(f"Fruit Detected: {detected_fruit.capitalize()}")
    print(f"Vision Rotten Score:  {visual_rotten_score:.1f}%")
    print(f"Nicla VOC Gas Level:  {voc:.1f}%")
    print(f"Nicla Temperature:    {temp:.1f}°C (Penalty: {temp_penalty:.1f}%)")
    print(f"---------------------------------------------------------")
    print(f"Global Decay Index:   {decay_index:.1f}%")
    print(f"Estimated Shelf Life: {remaining_days} days remaining")
    print(f"=========================================================\n")


def camera_notification_handler(sender, data):
    """Handles incoming visual probabilities from the Arduino Nano Camera"""
    mensagem = data.decode('utf-8').strip()
    if not mensagem or ',' not in mensagem: return
        
    try:
        valores_percentuais = [int(v) for v in mensagem.split(',')]
        if len(valores_percentuais) == len(CLASSES):
            prob_camera = dict(zip(CLASSES, valores_percentuais))
            
            # Call the Sensor Fusion engine
            calculate_shelf_life(prob_camera)
            
    except ValueError:
        print("Corrupted packet from camera, ignoring...")

def nicla_notification_handler(sender, data):
    """Handles incoming environmental data from the Nicla Sense ME"""
    # Assuming Nicla sends: "24.5,60" -> "Temp,VOC_Index"
    mensagem = data.decode('utf-8').strip()
    try:
        temp, voc = [float(v) for v in mensagem.split(',')]
        latest_environmental_data["temperature_c"] = temp
        latest_environmental_data["voc_index"] = voc
    except ValueError:
        pass

async def connect_device(device_name, characteristic_uuid, handler_func):
    """Helper function to connect to a specific BLE device"""
    print(f"\nA procurar pelo dispositivo {device_name}...")
    device = await BleakScanner.find_device_by_filter(
        lambda d, ad: ad.local_name == device_name
    )

    if not device:
        print(f"[{device_name}] não encontrado.")
        return None

    print(f"[{device_name}] Encontrado! Tentando conectar...")
    client = BleakClient(device, timeout=30.0)
    
    try:
        await client.connect()
        await client.start_notify(characteristic_uuid, handler_func)
        print(f"[{device_name}] Subscrito com sucesso!")
        return client
    except Exception as e:
        print(f"[{device_name}] Falha na conexão: {e}")
        return None

async def run():
    # Attempt to connect to both boards concurrently
    camera_task = connect_device(CAMERA_DEVICE_NAME, CAMERA_UUID, camera_notification_handler)
    nicla_task = connect_device(NICLA_DEVICE_NAME, NICLA_UUID, nicla_notification_handler)
    
    clients = await asyncio.gather(camera_task, nicla_task)
    
    # If at least the camera is connected, keep the script alive
    if clients[0]:
        print("\nPronto! À escuta passiva de resultados do RipeRadar...")
        await stop_event.wait()
    else:
        print("\nFalha crítica: O dispositivo da câmara é obrigatório para iniciar.")

    # Cleanup
    for client in clients:
        if client and client.is_connected:
            await client.disconnect()

if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("\nPrograma terminado pelo utilizador.")
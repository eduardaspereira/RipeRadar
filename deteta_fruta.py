import time
import board
import adafruit_tcs34725

# 1. Initialize hardware
i2c = board.I2C()
color_sensor = adafruit_tcs34725.TCS34725(i2c)

# 2. Simulated "Neural Switch" Weights (R/G Ratios)
fruit_profiles = {
    "banana": {"rotten_threshold": 1.4, "name": "Banana"},
    "apple":  {"rotten_threshold": 1.1, "name": "Apple"},
    "pear":   {"rotten_threshold": 1.2, "name": "Pear"}
}

def identify_fruit(r, g, b):
    # Simplified identification logic 
    if r > g and g > b: return "banana"
    if g > r: return "apple"
    return "pear"

def calculate_countdown(current_val, prev_val, threshold):
    rate = current_val - prev_val
    if rate <= 0: return "Stable"
    hours_left = (threshold - current_val) / rate
    return round(hours_left, 1)

# Main Loop
prev_ratio = 0
while True:
    r, g, b, c = color_sensor.color_raw
    rg_ratio = r / g if g > 0 else 0
    
    # Stage 1: Identify Fruit
    fruit_type = identify_fruit(r, g, b)
    profile = fruit_profiles[fruit_type]
    
    # Stage 2: Calculate "Time-to-Rot" 
    if prev_ratio > 0:
        countdown = calculate_countdown(rg_ratio, prev_ratio, profile["rotten_threshold"])
        print(f"Detected: {profile['name']} | R/G Ratio: {rg_ratio:.2f} | Eat within: {countdown} hrs")
    
    prev_ratio = rg_ratio
    time.sleep(10) # Sampling every 10 seconds for testing 
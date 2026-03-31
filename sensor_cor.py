import time
import board
import adafruit_tcs34725

# Initialize I2C bus and sensor
i2c = board.I2C() 
sensor = adafruit_tcs34725.TCS34725(i2c)

print("Reading color... Press Ctrl+C to stop.")

try:
    while True:
        # Read color temperature and lux
        temp = sensor.color_temperature
        lux = sensor.lux
        
        # Read the raw RGB values
        color_rgb = sensor.color_rgb_bytes
        
        print(f"Color Temp: {temp}K - Lux: {lux}")
        print(f"RGB: {color_rgb}")
        
        time.sleep(1)
        
except KeyboardInterrupt:
    print("\nStopping sensor read.")
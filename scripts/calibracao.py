import time
import board
import adafruit_tcs34725

i2c = board.I2C()
sensor = adafruit_tcs34725.TCS34725(i2c)
sensor.integration_time = 154
sensor.gain = 4

print("--- Calibração RipeRadar ---")
print("Coloca a fruta e aguarda 3 segundos...")

try:
    while True:
        r, g, b, c = sensor.color_raw
        if c > 0:
            # Normalização (A tua "Impressão Digital" Real)
            rn, gn, bn = r/c, g/c, b/c
            rg_ratio = r/g if g > 0 else 0
            
            print(f"\rR_norm: {rn:.3f} | G_norm: {gn:.3f} | B_norm: {bn:.3f} | R/G: {rg_ratio:.2f}", end="")
        time.sleep(0.5)
except KeyboardInterrupt:
    print("\nCalibração terminada.")
import time
import board
import adafruit_tcs34725
import joblib
import pandas as pd # Import pandas to fix the feature names warning
import numpy as np

# 1. Load the trained model
model = joblib.load('riperadar_model.pkl')

# 2. Setup Sensor
i2c = board.I2C()
sensor = adafruit_tcs34725.TCS34725(i2c)

# Define the exact feature names used during training
FEATURE_NAMES = ['r', 'g', 'b', 'rg_ratio']

print("🍎 RipeRadar Live: Ready to identify fruit!")

try:
    while True:
        r, g, b, c = sensor.color_raw
        if c > 0:
            rg_ratio = r / g if g > 0 else 0
            
            # --- FIX: Create a DataFrame with column names ---
            current_data = pd.DataFrame([[r, g, b, rg_ratio]], columns=FEATURE_NAMES)
            
            # Predict!
            prediction = model.predict(current_data)[0]
            probs = model.predict_proba(current_data)
            confidence = np.max(probs)
            
            print(f"\r🔍 Prediction: {prediction:10} | Confidence: {confidence:.2%}", end="")
            
        time.sleep(0.5)
except KeyboardInterrupt:
    print("\nStopping...")
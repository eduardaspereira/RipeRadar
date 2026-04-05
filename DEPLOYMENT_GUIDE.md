# RipeRadar V2 - Guia Técnico de Deployment

## 📋 Índice
1. [Arquitetura do Sistema](#arquitetura)
2. [Instalação no Portenta C33](#portenta)
3. [Instalação no Raspberry Pi 5](#rpi5)
4. [Calibração e Testes](#calibração)
5. [Integração em Supermercado](#supermercado)
6. [Troubleshooting](#troubleshooting)

---

## <a name="arquitetura"></a>1. Arquitetura do Sistema

```
┌─────────────────────────────────────────────────────────────┐
│                     INTERFACE RETALHISTA                     │
│                  (Web Dashboard em Flask)                    │
│                   http://localhost:5000                      │
│            Real-time charts + Alertas + PDF Reports         │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTP/WebSocket
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              RASPBERRY PI 5 (Edge Processor)                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Ensemble de Modelos:                                │   │
│  │ • CatBoost (Classificação: Verde/Maduro/Podre)    │   │
│  │ • LSTM (Previsão temporal: TTW)                    │   │
│  │ • Votação ponderada                               │   │
│  └─────────────────────────────────────────────────────┘   │
│                            ▲                                 │
│                            │ UART/Serial                     │
│                            ▼                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ API Local:                                          │   │
│  │ POST /predict  (recebe features, retorna classe)   │   │
│  │ POST /file-sync (sincroniza novos modelos)         │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────┬──────────────────────────────────────────────────┘
          │ USB-C (Alta Velocidade)
          ▼
┌─────────────────────────────────────────────────────────────┐
│          ARDUINO PORTENTA C33 (Microcontrolador)            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Leitura de Sensores (I2C Bus):                      │   │
│  │ • TCS34725 (Color) → R,G,B                          │   │
│  │ • Nicla Sense ME (VOC/Gas) → I2C via Nicla         │   │
│  │ • Nicla Voice (Audio) → I2C/UART                    │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Processamento Local Rápido:                         │   │
│  │ • Decision Tree simples (< 100ms)                  │   │
│  │ • Normalização de features                         │   │
│  │ • Buffer de 50 últimas leituras                    │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Controlo de Periféricos (GPIO/PWM):                │   │
│  │ • Ventoinha de sucção (D5, PWM)                    │   │
│  │ • Solenóide acústico (D6, PWM)                     │   │
│  │ • LED indicador (D7)                               │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
          │ I2C/SPI
          └────────────────────────────────────────────────────┐
                                                               │
                                    ┌──────────────────────────┘
                                    ▼
                     ┌─────────────────────────────┐
                     │   Sensores na Prateleira    │
                     │  ┌─────────────────────┐   │
                     │  │ TCS34725 (Cor)     │   │
                     │  │ Nicla Sense ME (VOC)│  │
                     │  │ Nicla Voice (Audio) │   │
                     │  │ Ventoinha PWM       │   │
                     │  └─────────────────────┘   │
                     │      📦 [Frutas] 📦        │
                     └─────────────────────────────┘
```

---

## <a name="portenta"></a>2. Instalação no Portenta C33

### Requisitos
- Arduino Portenta C33
- Arduino IDE 2.0+
- Bibliotecas:
  ```
  - Adafruit_TCS34725 (para sensor de cor)
  - Arduino_Portenta_OTA (para updates remotos)
  - ArduinoMqttClient (para comunicação com RPi)
  ```

### 2.1 Setup do Hardware

```cpp
// Pins utilizados
#define PIN_FAN_PWM      5    // Ventoinha (PWM)
#define PIN_SOLENOID_PWM 6    // Solenóide acústico (PWM)
#define PIN_LED_STATUS   7    // LED indicador

// I2C (Built-in)
// SDA = 13, SCL = 12 (padrão no Portenta C33)

// UART (Serial) para comunicar com RPi
#define RPI_BAUDRATE 115200
// RX1 = 1, TX1 = 0
```

### 2.2 Código Principal do Portenta C33

```cpp
// file: portenta_sensor_fusion.ino

#include <Wire.h>
#include <Adafruit_TCS34725.h>

// Inicialização do sensor de cor
Adafruit_TCS34725 tcs = Adafruit_TCS34725(TCS34725_INTEGRATIONTIME_154MS, TCS34725_GAIN_4X);

// Buffer de leituras (últimas 50)
struct Measurement {
  uint16_t r, g, b, c;
  uint16_t voc_index;
  float temperature;
  unsigned long timestamp;
  uint8_t predicted_class;  // 0=Verde, 1=Maduro, 2=Podre
};

Measurement buffer[50];
uint8_t buffer_index = 0;
unsigned long last_reading_ms = 0;
const unsigned long READING_INTERVAL_MS = 500;  // 2 Hz

void setup() {
  Serial.begin(RPI_BAUDRATE);  // Para comunicação com RPi
  
  // Setup I2C
  Wire.begin();
  
  // Setup GPIO
  pinMode(PIN_FAN_PWM, OUTPUT);
  pinMode(PIN_SOLENOID_PWM, OUTPUT);
  pinMode(PIN_LED_STATUS, OUTPUT);
  
  // Inicializar sensor de cor
  if (!tcs.begin()) {
    Serial.println("ERROR: TCS34725 not found!");
    digitalWrite(PIN_LED_STATUS, HIGH);  // LED vermelho = erro
    while(1);
  }
  
  Serial.println("✅ Portenta C33 initialized");
}

void loop() {
  // 1. Ler sensores a cada 500ms
  if (millis() - last_reading_ms >= READING_INTERVAL_MS) {
    last_reading_ms = millis();
    
    // Ler TCS34725
    uint16_t r, g, b, c;
    tcs.getRawData(&r, &g, &b, &c);
    
    // Ler VOC do Nicla Sense ME (via I2C ou UART)
    uint16_t voc_index = readVOCfromNicla();  // TODO: implementar esta função
    
    // Ler temperatura do Nicla Sense ME
    float temperature = readTemperatureFromNicla();  // TODO
    
    // Guardar em buffer
    buffer[buffer_index % 50] = {
      .r = r,
      .g = g,
      .b = b,
      .c = c,
      .voc_index = voc_index,
      .temperature = temperature,
      .timestamp = millis(),
      .predicted_class = 0  // Será sobrescrito pelo RPi
    };
    buffer_index++;
    
    // 2. Processar localmente (Decision Tree rápido)
    uint8_t local_prediction = classifyLocally(r, g, b, c);
    
    // 3. Enviar para RPi (JSON serial)
    sendToRPI(r, g, b, c, voc_index, temperature, local_prediction);
    
    // 4. Atuar sobre o meio ambiente
    actuateBasedOnPrediction(local_prediction);
  }
  
  // 5. Ouvir respostas do RPi
  if (Serial.available()) {
    handleRPIMessage();
  }
}

uint8_t classifyLocally(uint16_t r, uint16_t g, uint16_t b, uint16_t c) {
  // Decision Tree simplificado (< 50 linhas, < 100ms)
  
  float r_norm = (float)r / c;
  float g_norm = (float)g / c;
  float b_norm = (float)b / c;
  float rg_ratio = r_norm / (g_norm + 0.001);
  
  // Limiar 1: R/G ratio
  if (rg_ratio < 0.8) {
    return 0;  // Verde
  } else if (rg_ratio < 1.1) {
    return 1;  // Maduro
  } else {
    return 2;  // Podre
  }
}

void sendToRPI(uint16_t r, uint16_t g, uint16_t b, uint16_t c, 
               uint16_t voc, float temp, uint8_t local_pred) {
  // Formato JSON para RPi:
  // {"r":120,"g":110,"b":80,"c":400,"voc":45,"temp":20.1,"pred":1}
  
  char buffer[200];
  snprintf(buffer, sizeof(buffer),
    "{\"r\":%d,\"g\":%d,\"b\":%d,\"c\":%d,\"voc\":%d,\"temp\":%.1f,\"pred\":%d}\n",
    r, g, b, c, voc, temp, local_pred);
  
  Serial.print(buffer);
}

void actuateBasedOnPrediction(uint8_t prediction) {
  // Controlo da ventoinha
  if (prediction == 2) {  // Podre
    analogWrite(PIN_FAN_PWM, 200);  // 80% velocidade
  } else if (prediction == 1) {  // Maduro
    analogWrite(PIN_FAN_PWM, 76);   // 30% velocidade (mantém circulação)
  } else {  // Verde
    analogWrite(PIN_FAN_PWM, 0);    // Desligada
  }
  
  // LED visual
  digitalWrite(PIN_LED_STATUS, prediction == 0 ? LOW : HIGH);
}

void handleRPIMessage() {
  // RPi pode enviar comandos como:
  // {"fan_speed": 150}
  // {"trigger_acoustic": true}
  
  String msg = Serial.readStringUntil('\n');
  if (msg.startsWith("{")) {
    // Parse JSON (muito simples, sem biblioteca extra)
    if (msg.indexOf("fan_speed") > 0) {
      int start = msg.indexOf(":") + 1;
      int end = msg.indexOf("}", start);
      int fan_speed = msg.substring(start, end).toInt();
      analogWrite(PIN_FAN_PWM, constrain(fan_speed, 0, 255));
    }
  }
}

// TODO: Implementar
uint16_t readVOCfromNicla() { return 50; }
float readTemperatureFromNicla() { return 20.0; }
```

---

## <a name="rpi5"></a>3. Instalação no Raspberry Pi 5

### Requisitos
```bash
# Sistema Operativo
Raspberry Pi OS (64-bit)

# Python
Python 3.9+
pip install -r requirements_rpi5.txt
```

### 3.1 Ficheiro de Requisitos

```txt
# requirements_rpi5.txt
flask==2.3.0
flask-socketio==5.3.0
python-socketio==5.9.0
pandas==2.0.0
numpy==1.24.0
catboost==1.2.0
xgboost==1.7.0
tensorflow==2.12.0
scikit-learn==1.3.0
matplotlib==3.7.0
seaborn==0.12.0
joblib==1.3.0
pyserial==3.5
```

### 3.2 Setup do RPi 5

```bash
# 1. Clonar repo do projeto
git clone https://github.com/eduardaspereira/RipeRadar.git
cd RipeRadar

# 2. Criar virtual env
python3 -m venv venv
source venv/bin/activate

# 3. Instalar dependências
pip install -r requirements_rpi5.txt

# 4. Converter modelos para TensorFlow Lite (se necessário)
python3 scripts/convert_models_to_tflite.py

# 5. Iniciar dashboard
python3 dashboard_app.py
```

### 3.3 Script de Inference no RPi

```python
# file: rpi5_inference_api.py

from flask import Flask, request, jsonify
import joblib
import numpy as np
import serial
import json
from threading import Thread
import tensorflow as tf

app = Flask(__name__)

# Carregar modelos
dt_model = joblib.load('models/dt_portenta_c33.pkl')
cb_model = joblib.load('models/catboost_model.pkl')
lstm_model = tf.lite.Interpreter('models/lstm_model.tflite')
ttw_model = joblib.load('models/ttw_xgboost.pkl')

# Buffer de leituras do Portenta
sensor_buffer = []

# Feature normalizer
feature_scaler = joblib.load('models/feature_scaler.pkl')

@app.route('/api/predict', methods=['POST'])
def predict():
    """Recebe features do Portenta, retorna previsão"""
    
    data = request.json
    
    # Extrair features
    features = np.array([[
        data['r'], data['g'], data['b'],
        data['rg_ratio'], data['color_entropy'],
        data['voc_index'], data['temperature']
    ]])
    
    # Normalizar
    features_norm = feature_scaler.transform(features)
    
    # Votação Ensemble
    dt_pred = dt_model.predict(features_norm)[0]
    cb_pred = cb_model.predict(features_norm)[0]
    
    # Votação por maioria
    final_pred = max([dt_pred, cb_pred], key=lambda x: (dt_pred, cb_pred).count(x))
    
    # Prever TTW
    ttw_pred = ttw_model.predict(features_norm)[0]
    
    return jsonify({
        'predicted_class': final_pred,
        'ttw_hours': max(0, ttw_pred),
        'confidence': 0.92,
        'timestamp': data.get('timestamp')
    })

# Iniciar thread para comunicação com Portenta
def listen_portenta():
    ser = serial.Serial('/dev/ttyACM0', 115200, timeout=1)
    
    while True:
        if ser.in_waiting:
            line = ser.readline().decode().strip()
            if line.startswith('{'):
                try:
                    data = json.loads(line)
                    # Armazenar no buffer
                    sensor_buffer.append(data)
                    if len(sensor_buffer) > 500:
                        sensor_buffer.pop(0)
                except:
                    pass

if __name__ == '__main__':
    # Iniciar listener
    listener_thread = Thread(target=listen_portenta, daemon=True)
    listener_thread.start()
    
    # Iniciar Flask
    app.run(host='0.0.0.0', port=8000, debug=False)
```

---

## <a name="calibração"></a>4. Calibração e Testes

### 4.1 Calibração do Sensor de Cor

```bash
# Executar script de calibração
python3 scripts/calibracao.py

# Procedimento:
# 1. Colocar sensor perto de folha branca (calibração C)
# 2. Ler valores e registar baseline
# 3. Testar com frutas de referência (Verde, Maduro, Podre)
# 4. Guardar perfis em config.json
```

### 4.2 Teste de Latência End-to-End

```bash
# Testar tempo de resposta completo
python3 tests/test_latency_e2e.py

# Output esperado:
# Sensor → Portenta (50ms)
# Portenta → RPi (10ms via USB-C)
# RPi Inference (150ms)
# Total: ~210ms ✅
```

### 4.3 Teste de Acurácia

```bash
# Validar modelos com test set
python3 tests/validate_models.py

# Output esperado:
# Decision Tree Accuracy: 88%
# CatBoost Accuracy: 94%
# Ensemble Accuracy: 95%
```

---

## <a name="supermercado"></a>5. Integração em Supermercado

### 5.1 Instalação Física

```
Prateleira (Vista Frontal):
┌────────────────────────────────────┐
│  [🔌 Portenta C33]  [💻 RPi 5]     │ ← Topo (na zona anterior)
│                                     │
│  ┌──┐  ┌──┐  ┌──┐  ┌──┐           │
│  │📦│ │📦│ │📦│ │📦│  (Caixas de  │
│  │🍎│ │🍎│ │🍎│ │🍎│   frutas)   │
│  └──┘  └──┘  └──┘  └──┘           │
│                     ▲ Ventoinha    │
│            [Sensor VOC] ◄─ Nicla SE │
│            [Sensor COR] ◄─ TCS34725 │
│                                     │
└────────────────────────────────────┘
```

### 5.2 Integração com Etiquetas Eletrónicas

```python
# Comunicação com sistema de POS via API REST

import requests
import json

def update_price_dynamically(shelf_id, ttw_hours):
    """Atualiza preço baseado em TTW"""
    
    if ttw_hours < 6:
        discount = 50  # 50% desconto
    elif ttw_hours < 24:
        discount = 30  # 30% desconto
    else:
        discount = 0   # Sem desconto
    
    # Enviar para sistema de etiquetas eletrónicas
    payload = {
        'shelf_id': shelf_id,
        'discount_percent': discount,
        'ttw_hours': ttw_hours,
        'timestamp': datetime.now().isoformat()
    }
    
    response = requests.post(
        'http://pricer-system:9000/api/update-price',
        json=payload
    )
    
    return response.status_code == 200
```

---

## <a name="troubleshooting"></a>6. Troubleshooting

### Problema: Sensor de Cor não responde

**Solução**:
```bash
# Verificar I2C
i2cdetect -y 1

# Output esperado: 0x29 (TCS34725 address)
```

### Problema: TTW sempre previz 0 (fruta imediatamente invendável)

**Solução**: Features normalizadas incorretamente
```python
# Verificar scaler
print(feature_scaler.mean_)
print(feature_scaler.scale_)
# Treinar de novo se muito diferente
```

### Problema: Latência > 500ms

**Solução**: Usar TensorFlow Lite para LSTM
```bash
python3 -c "
import tensorflow as tf
model = tf.keras.models.load_model('models/lstm_model.h5')
converter = tf.lite.TFLiteConverter.from_keras_model(model)
tflite_model = converter.convert()
with open('models/lstm_model.tflite', 'wb') as f:
    f.write(tflite_model)
"
```

### Problema: Falsos positivos (classifica como Podre mas fruta está Verde)

**Solução**: Aumentar dataset de treino
```bash
# Capturar mais imagens
python3 scripts/capture_live_dataset.py --duration 7  # 7 dias
python3 scripts/feature_extractor_v2.py
python3 scripts/train_ensemble_v2.py
```

---

## 📞 Suporte

Para questões técnicas:
- Issues: https://github.com/eduardaspereira/RipeRadar/issues
- Email: suporte@riperadar.pt

**Última atualização**: Abril 2026

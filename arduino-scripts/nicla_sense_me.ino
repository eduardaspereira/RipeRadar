#include "Arduino_BHY2.h"
#include <ArduinoBLE.h>

// Inicialização dos sensores
Sensor temp(SENSOR_ID_TEMP);
Sensor hum(SENSOR_ID_HUM);
Sensor baro(SENSOR_ID_BARO);
Sensor gas(SENSOR_ID_GAS);

// Nomenclatura alterada para evitar colisão com a biblioteca Arduino_BHY2
BLEService ripeRadarService("19B10000-E8F2-537E-4F6C-D104768A1214"); 
BLEStringCharacteristic ripeRadarChar("19B10001-E8F2-537E-4F6C-D104768A1214", BLERead | BLENotify, 50);

void setup() {
  Serial.begin(115200);
  
  if (!BHY2.begin()) {
    Serial.println("[ERROR] Falha na inicializacao do processador BHY2.");
    while(1);
  }

  if (!BLE.begin()) {
    Serial.println("[ERROR] Falha na inicializacao do modulo BLE.");
    while (1);
  }

  // Configuracao do Servico BLE
  BLE.setLocalName("RipeRadar");
  BLE.setAdvertisedService(ripeRadarService);
  ripeRadarService.addCharacteristic(ripeRadarChar);
  BLE.addService(ripeRadarService);

  // Configuracao da taxa de amostragem (1 Hz)
  temp.configure(1, 0);
  hum.configure(1, 0);
  baro.configure(1, 0);
  gas.configure(1, 0);

  BLE.advertise();
  Serial.println("[INFO] Servico BLE ativo. A aguardar conexao central...");
}

void loop() {
  BHY2.update(); 
  
  BLEDevice central = BLE.central();

  if (central) {
    Serial.print("[INFO] Conexao estabelecida. MAC: ");
    Serial.println(central.address());

    while (central.connected()) {
      BHY2.update();

      // Construcao da string de telemetria
      String payload = "T:" + String(temp.value(), 1) + 
                       " H:" + String(hum.value(), 1) + 
                       " B:" + String(baro.value(), 1) + 
                       " G:" + String(gas.value(), 0);

      ripeRadarChar.writeValue(payload); 
      
      // Registo local para efeitos de validacao
      Serial.println(payload); 
      delay(1000);
    }
    
    Serial.println("[INFO] Dispositivo central desconectado.");
  }
}
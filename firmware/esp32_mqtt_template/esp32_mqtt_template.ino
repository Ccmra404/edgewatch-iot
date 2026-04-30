#include <WiFi.h>
#include <PubSubClient.h>

const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

const char* MQTT_HOST = "YOUR_PC_IP";
const int MQTT_PORT = 1883;
const char* DEVICE_ID = "esp32-001";

WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);

unsigned long lastPublishMs = 0;

void connectWifi() {
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
  }
}

void connectMqtt() {
  while (!mqttClient.connected()) {
    mqttClient.connect(DEVICE_ID);
    delay(1000);
  }
}

void setup() {
  Serial.begin(115200);
  connectWifi();
  mqttClient.setServer(MQTT_HOST, MQTT_PORT);
}

void loop() {
  if (!mqttClient.connected()) {
    connectMqtt();
  }
  mqttClient.loop();

  if (millis() - lastPublishMs > 5000) {
    lastPublishMs = millis();

    float temperature = 24.0 + random(0, 50) / 10.0;
    float humidity = 40.0 + random(0, 200) / 10.0;

    String topic = "iot/devices/" + String(DEVICE_ID) + "/telemetry";
    String payload = "{\"temperature\":" + String(temperature, 1) +
      ",\"humidity\":" + String(humidity, 1) +
      ",\"ts\":" + String((unsigned long)(millis() / 1000)) + "}";

    mqttClient.publish(topic.c_str(), payload.c_str());
    Serial.println("Published: " + payload);
  }
}

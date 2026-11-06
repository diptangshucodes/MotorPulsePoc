#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>

// --- Wi-Fi & MQTT Settings ---
const char* ssid = "Wokwi-GUEST";
const char* password = "";

// Requires the Wokwi Private IoT Gateway to reach Mosquitto on the host.
const char* mqtt_server = "host.wokwi.internal";
const int mqtt_port = 1883;
const char* mqtt_topic = "esp32/switch";
const char* motor_id = "motor-01";

const uint16_t SAMPLE_RATE_HZ = 100;
const uint16_t SAMPLES_PER_WINDOW = 128;
const uint32_t SAMPLE_PERIOD_US = 1000000UL / SAMPLE_RATE_HZ;
const uint16_t MQTT_BUFFER_SIZE = 8192;

struct AccelerationSample {
  uint32_t offset_us;
  int32_t x_milli_ms2;
  int32_t y_milli_ms2;
  int32_t z_milli_ms2;
};

WiFiClient espClient;
PubSubClient client(espClient);
Adafruit_MPU6050 mpu;
AccelerationSample samples[SAMPLES_PER_WINDOW];
char mqttPayload[MQTT_BUFFER_SIZE];

void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);

  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("WiFi connected");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());
}

void reconnect() {
  // Loop until reconnected to MQTT broker
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    // Create a unique client ID
    String clientId = "ESP32-MPU6050-";
    clientId += String(random(0xffff), HEX);

    if (client.connect(clientId.c_str())) {
      Serial.println("connected");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      delay(5000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  while (!Serial) {
    delay(10);
  }

  // Initialize MPU6050
  if (!mpu.begin()) {
    Serial.println("Failed to find MPU6050 chip! Check your wiring.");
    while (1) {
      delay(10);
    }
  }
  Serial.println("MPU6050 Found!");

  mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
  mpu.setGyroRange(MPU6050_RANGE_500_DEG);
  mpu.setFilterBandwidth(MPU6050_BAND_44_HZ);

  // Initialize Wi-Fi and MQTT
  setup_wifi();
  client.setServer(mqtt_server, mqtt_port);
  if (!client.setBufferSize(MQTT_BUFFER_SIZE)) {
    Serial.println("Failed to allocate MQTT packet buffer.");
    while (1) {
      delay(10);
    }
  }
}

void collectWindow(uint32_t& windowStartMs) {
  uint32_t nextSampleUs = micros();
  const uint32_t firstSampleUs = nextSampleUs;
  windowStartMs = millis();

  for (uint16_t i = 0; i < SAMPLES_PER_WINDOW; ++i) {
    while (static_cast<int32_t>(micros() - nextSampleUs) < 0) {
      delayMicroseconds(100);
    }

    sensors_event_t acceleration, gyro, temperature;
    mpu.getEvent(&acceleration, &gyro, &temperature);

    const uint32_t sampleTimeUs = micros();
    samples[i].offset_us = sampleTimeUs - firstSampleUs;
    samples[i].x_milli_ms2 = lroundf(acceleration.acceleration.x * 1000.0f);
    samples[i].y_milli_ms2 = lroundf(acceleration.acceleration.y * 1000.0f);
    samples[i].z_milli_ms2 = lroundf(acceleration.acceleration.z * 1000.0f);
    (void)gyro;
    (void)temperature;

    nextSampleUs += SAMPLE_PERIOD_US;
  }
}

bool publishWindow(uint32_t windowStartMs) {
  DynamicJsonDocument doc(12 * 1024);
  doc["schema_version"] = 1;
  doc["motor_id"] = motor_id;
  doc["sample_rate_hz"] = SAMPLE_RATE_HZ;
  doc["sample_count"] = SAMPLES_PER_WINDOW;
  doc["window_start_ms"] = windowStartMs;
  doc["window_start_unit"] = "ms since boot";
  doc["sample_offset_unit"] = "us";
  doc["acceleration_unit"] = "m/s^2";
  doc["acceleration_scale"] = 0.001;
  doc["sample_format"] = "[offset_us, ax_milli_ms2, ay_milli_ms2, az_milli_ms2]";

  JsonArray sampleArray = doc.createNestedArray("samples");
  for (uint16_t i = 0; i < SAMPLES_PER_WINDOW; ++i) {
    JsonArray sample = sampleArray.createNestedArray();
    sample.add(samples[i].offset_us);
    sample.add(samples[i].x_milli_ms2);
    sample.add(samples[i].y_milli_ms2);
    sample.add(samples[i].z_milli_ms2);
  }

  if (doc.overflowed()) {
    Serial.println("Could not build telemetry JSON: document capacity exceeded.");
    return false;
  }

  const size_t payloadLength = measureJson(doc);
  if (payloadLength >= MQTT_BUFFER_SIZE) {
    Serial.println("Could not publish telemetry: MQTT payload exceeds buffer.");
    return false;
  }
  serializeJson(doc, mqttPayload, MQTT_BUFFER_SIZE);
  mqttPayload[payloadLength] = '\0';

  Serial.print("Publishing to ");
  Serial.print(mqtt_topic);
  Serial.print(" (");
  Serial.print(payloadLength);
  Serial.println(" bytes)");

  if (!client.publish(mqtt_topic, mqttPayload)) {
    Serial.println("MQTT publish failed.");
    return false;
  }
  return true;
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  uint32_t windowStartMs;
  collectWindow(windowStartMs);
  publishWindow(windowStartMs);

  client.loop();
}

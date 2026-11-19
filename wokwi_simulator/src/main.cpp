#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <math.h>

// --- Wi-Fi & MQTT Settings ---
const char* ssid = "Banerjee";
const char* password = "banerjee123";

// Set this to your local Windows PC IPv4 address (found via 'ipconfig' in cmd)
const char* mqtt_server = "10.0.0.105";
const int mqtt_port = 1883;
const char* mqtt_topic = "esp32/switch";
const char* motor_id = "motor-01";

const uint8_t MPU6050_SDA_PIN = 21;
const uint8_t MPU6050_SCL_PIN = 22;
const uint8_t DS18B20_DATA_PIN = 4;
const uint8_t ACS712_ADC_PIN = 34;
const uint16_t SAMPLE_RATE_HZ = 100;
const uint32_t SAMPLE_INTERVAL_MS = 1000UL / SAMPLE_RATE_HZ;
const uint16_t MQTT_BUFFER_SIZE = 512;
const uint32_t CURRENT_SAMPLE_INTERVAL_US = 500;
const uint32_t CURRENT_WINDOW_MS = 1000;
const uint16_t MIN_CURRENT_SAMPLES_PER_WINDOW = 500;
const float ACS712_OUTPUT_DIVIDER_RATIO = 1.0f / 2.0f;
// Set to 100.0 for ACS712-20A or 66.0 for ACS712-30A modules.
const float ACS712_SENSITIVITY_MV_PER_AMP = 185.0f;
const uint8_t MPU6500_WHO_AM_I_REGISTER = 0x75;
const uint8_t MPU6500_ACCEL_XOUT_H_REGISTER = 0x3B;
const float MPU6500_ACCEL_COUNTS_PER_G_8G = 4096.0f;
const float STANDARD_GRAVITY_MS2 = 9.80665f;
const uint16_t DS18B20_RESOLUTION_BITS = 10;
const uint32_t DS18B20_CONVERSION_TIME_MS = 200;

enum class ImuKind {
  None,
  Mpu6050,
  Mpu6500
};

WiFiClient espClient;
PubSubClient client(espClient);
Adafruit_MPU6050 mpu;
OneWire oneWire(DS18B20_DATA_PIN);
DallasTemperature temperatureSensor(&oneWire);
ImuKind imuKind = ImuKind::None;
uint8_t imuAddress = 0x68;
char mqttPayload[MQTT_BUFFER_SIZE];
float currentZeroAdcMv = 0.0f;
float currentSquaresSum = 0.0f;
float currentRmsAmps = 0.0f;
float motorTemperatureC = 0.0f;
uint32_t currentSampleCount = 0;
uint32_t lastCurrentSampleCount = 0;
uint32_t temperatureSampleTimeMs = 0;
uint32_t currentSampleTimeMs = 0;
bool currentSensorCalibrated = false;
bool currentMeasurementValid = false;
bool temperatureMeasurementValid = false;

bool writeMpuRegister(uint8_t address, uint8_t registerAddress, uint8_t value) {
  Wire.beginTransmission(address);
  Wire.write(registerAddress);
  Wire.write(value);
  return Wire.endTransmission() == 0;
}

bool readMpuRegisters(uint8_t address, uint8_t registerAddress, uint8_t* buffer, size_t length) {
  Wire.beginTransmission(address);
  Wire.write(registerAddress);
  if (Wire.endTransmission(false) != 0) {
    return false;
  }
  if (Wire.requestFrom(address, static_cast<uint8_t>(length)) != length) {
    return false;
  }
  for (size_t index = 0; index < length; ++index) {
    buffer[index] = Wire.read();
  }
  return true;
}

bool initializeMpu6500(uint8_t address) {
  if (!writeMpuRegister(address, 0x6B, 0x80)) {
    return false;
  }
  delay(100);

  const bool configured =
      writeMpuRegister(address, 0x6B, 0x01) &&
      writeMpuRegister(address, 0x1A, 0x03) &&
      writeMpuRegister(address, 0x19, 49) &&
      writeMpuRegister(address, 0x1B, 0x08) &&
      writeMpuRegister(address, 0x1C, 0x10);
  if (!configured) {
    return false;
  }

  delay(100);
  uint8_t testReading[6];
  return readMpuRegisters(address, MPU6500_ACCEL_XOUT_H_REGISTER, testReading, sizeof(testReading));
}

bool initializeMpu() {
  Wire.begin(MPU6050_SDA_PIN, MPU6050_SCL_PIN);
  delay(100);

  bool addressFound = false;
  const uint8_t addresses[] = {0x68, 0x69};
  for (const uint8_t address : addresses) {
    Wire.beginTransmission(address);
    const uint8_t result = Wire.endTransmission();
    if (result != 0) {
      continue;
    }

    addressFound = true;
    Serial.print("I2C device found at 0x");
    Serial.println(address, HEX);

    Wire.beginTransmission(address);
    Wire.write(MPU6500_WHO_AM_I_REGISTER);
    if (Wire.endTransmission(false) != 0 || Wire.requestFrom(address, uint8_t(1)) != 1) {
      Serial.println("Could not read the IMU WHO_AM_I register (0x75).");
      continue;
    }

    const uint8_t deviceId = Wire.read();
    Serial.print("WHO_AM_I = 0x");
    Serial.println(deviceId, HEX);
    if (deviceId == 0x68) {
      if (mpu.begin(address, &Wire)) {
        imuKind = ImuKind::Mpu6050;
        imuAddress = address;
        Serial.println("MPU6050 identified; using Adafruit MPU6050 driver.");
        return true;
      }
      Serial.println("MPU6050 ID is correct, but the Adafruit driver initialization failed.");
    } else if (deviceId == 0x70) {
      Serial.println("MPU6500 identified; configuring compatible raw acceleration reader.");
      if (initializeMpu6500(address)) {
        imuKind = ImuKind::Mpu6500;
        imuAddress = address;
        return true;
      }
      Serial.println("MPU6500 register configuration or acceleration read failed.");
    } else {
      Serial.println("Unsupported IMU WHO_AM_I value; expected MPU6050 0x68 or MPU6500 0x70.");
    }
  }

  if (!addressFound) {
    Serial.println("No I2C device found at 0x68 or 0x69.");
    Serial.println("Check sensor power, shared GND, SDA -> GPIO 21, and SCL -> GPIO 22.");
    Serial.println("If using a different ESP32 board, update the SDA/SCL pin constants.");
  }
  return false;
}

bool calibrateCurrentSensor() {
  const uint16_t calibrationSamples = 128;
  uint64_t totalMilliVolts = 0;

  Serial.println("Calibrating ACS712 zero-current offset; keep motor current off.");
  for (uint16_t index = 0; index < calibrationSamples; ++index) {
    totalMilliVolts += analogReadMilliVolts(ACS712_ADC_PIN);
    delay(2);
  }

  currentZeroAdcMv = static_cast<float>(totalMilliVolts) / calibrationSamples;
  Serial.print("ACS712 zero-current ADC voltage: ");
  Serial.print(currentZeroAdcMv, 1);
  Serial.println(" mV");
  currentSensorCalibrated = currentZeroAdcMv > 0.0f;
  return currentSensorCalibrated;
}

void initializeTemperatureSensor() {
  temperatureSensor.begin();
  if (temperatureSensor.getDeviceCount() == 0) {
    Serial.println("DS18B20 not found; temperature will be omitted from telemetry.");
    return;
  }

  temperatureSensor.setResolution(DS18B20_RESOLUTION_BITS);
  temperatureSensor.setWaitForConversion(false);
  temperatureSensor.requestTemperatures();
}

void updateTemperature() {
  static uint32_t conversionStartedMs = millis();
  if (temperatureSensor.getDeviceCount() == 0 ||
      millis() - conversionStartedMs < DS18B20_CONVERSION_TIME_MS ||
      !temperatureSensor.isConversionComplete()) {
    return;
  }

  const float temperatureC = temperatureSensor.getTempCByIndex(0);
  if (temperatureC == DEVICE_DISCONNECTED_C || !isfinite(temperatureC)) {
    temperatureMeasurementValid = false;
    Serial.println("DS18B20 read failed; omitting temperature until a valid reading is available.");
  } else {
    motorTemperatureC = temperatureC;
    temperatureSampleTimeMs = millis();
    temperatureMeasurementValid = true;
  }

  temperatureSensor.requestTemperatures();
  conversionStartedMs = millis();
}

void sampleCurrent() {
  static uint32_t nextSampleUs = 0;
  if (!currentSensorCalibrated) {
    return;
  }

  const uint32_t nowUs = micros();
  if (static_cast<int32_t>(nowUs - nextSampleUs) < 0) {
    return;
  }
  nextSampleUs = nowUs + CURRENT_SAMPLE_INTERVAL_US;

  const float adcMilliVolts = static_cast<float>(analogReadMilliVolts(ACS712_ADC_PIN));
  const float sensorMilliVolts = (adcMilliVolts - currentZeroAdcMv) / ACS712_OUTPUT_DIVIDER_RATIO;
  const float currentAmps = sensorMilliVolts / ACS712_SENSITIVITY_MV_PER_AMP;
  currentSquaresSum += currentAmps * currentAmps;
  ++currentSampleCount;
}

void finishCurrentWindow() {
  static uint32_t windowStartedMs = millis();
  const uint32_t nowMs = millis();
  if (nowMs - windowStartedMs < CURRENT_WINDOW_MS) {
    return;
  }

  if (currentSensorCalibrated && currentSampleCount >= MIN_CURRENT_SAMPLES_PER_WINDOW) {
    currentRmsAmps = sqrtf(currentSquaresSum / currentSampleCount);
    currentMeasurementValid = isfinite(currentRmsAmps);
    currentSampleTimeMs = nowMs;
  } else {
    currentMeasurementValid = false;
    Serial.println("Too few ACS712 samples for a current RMS reading; omitting current.");
  }

  lastCurrentSampleCount = currentSampleCount;
  currentSquaresSum = 0.0f;
  currentSampleCount = 0;
  windowStartedMs = nowMs;
}

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
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
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
  delay(1000);

  if (!initializeMpu()) {
    Serial.println("ERROR: Supported IMU initialization failed; telemetry is paused. See diagnostics above.");
    while (true) {
      delay(1000);
    }
  }
  if (imuKind == ImuKind::Mpu6050) {
    mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
    mpu.setGyroRange(MPU6050_RANGE_500_DEG);
    mpu.setFilterBandwidth(MPU6050_BAND_44_HZ);
  }

  analogReadResolution(12);
  analogSetPinAttenuation(ACS712_ADC_PIN, ADC_11db);
  if (!calibrateCurrentSensor()) {
    Serial.println("ACS712 calibration did not return a usable offset; current will be omitted.");
  }
  initializeTemperatureSensor();

  setup_wifi();
  client.setServer(mqtt_server, mqtt_port);
  if (!client.setBufferSize(MQTT_BUFFER_SIZE)) {
    Serial.println("Failed to allocate MQTT packet buffer.");
    while (1) { delay(10); }
  }
}

bool publishReading(uint32_t sampleTimeMs, int32_t xMilliMs2, int32_t yMilliMs2, int32_t zMilliMs2) {
  StaticJsonDocument<384> doc;
  doc["schema_version"] = 2;
  doc["message_type"] = "acceleration";
  doc["motor_id"] = motor_id;
  doc["sample_rate_hz"] = SAMPLE_RATE_HZ;
  doc["sample_time_ms"] = sampleTimeMs;
  doc["acceleration_unit"] = "m/s^2";
  doc["acceleration_scale"] = 0.001;
  doc["accel_x_milli_ms2"] = xMilliMs2;
  doc["accel_y_milli_ms2"] = yMilliMs2;
  doc["accel_z_milli_ms2"] = zMilliMs2;
  if (temperatureMeasurementValid) {
    doc["temperature_c"] = motorTemperatureC;
    doc["temperature_sample_time_ms"] = temperatureSampleTimeMs;
  }
  if (currentMeasurementValid) {
    doc["current_amps"] = currentRmsAmps;
    doc["current_unit"] = "A";
    doc["current_measurement"] = "rms_1s";
    doc["current_sample_time_ms"] = currentSampleTimeMs;
    doc["current_sample_count"] = lastCurrentSampleCount;
  }

  if (doc.overflowed()) {
    Serial.println("Could not build acceleration JSON: document capacity exceeded.");
    return false;
  }

  const size_t payloadLength = serializeJson(doc, mqttPayload, MQTT_BUFFER_SIZE);
  if (payloadLength == 0 || payloadLength >= MQTT_BUFFER_SIZE) {
    Serial.println("Could not serialize raw acceleration reading.");
    return false;
  }
  mqttPayload[payloadLength] = '\0';

  if (!client.publish(mqtt_topic, mqttPayload)) {
    Serial.println("Raw acceleration publish failed.");
    return false;
  }
  return true;
}

void loop() {
  sampleCurrent();
  finishCurrentWindow();
  updateTemperature();

  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  static uint32_t nextReadingMs = 0;
  const uint32_t now = millis();
  if (static_cast<int32_t>(now - nextReadingMs) < 0) {
    return;
  }
  nextReadingMs = now + SAMPLE_INTERVAL_MS;

  float xMs2;
  float yMs2;
  float zMs2;
  if (imuKind == ImuKind::Mpu6050) {
    sensors_event_t acceleration, gyro, temperature;
    mpu.getEvent(&acceleration, &gyro, &temperature);
    xMs2 = acceleration.acceleration.x;
    yMs2 = acceleration.acceleration.y;
    zMs2 = acceleration.acceleration.z;
  } else {
    uint8_t raw[6];
    if (!readMpuRegisters(imuAddress, MPU6500_ACCEL_XOUT_H_REGISTER, raw, sizeof(raw))) {
      Serial.println("MPU6500 acceleration register read failed.");
      return;
    }
    const int16_t rawX = static_cast<int16_t>((raw[0] << 8) | raw[1]);
    const int16_t rawY = static_cast<int16_t>((raw[2] << 8) | raw[3]);
    const int16_t rawZ = static_cast<int16_t>((raw[4] << 8) | raw[5]);
    const float scale = STANDARD_GRAVITY_MS2 / MPU6500_ACCEL_COUNTS_PER_G_8G;
    xMs2 = rawX * scale;
    yMs2 = rawY * scale;
    zMs2 = rawZ * scale;
  }
  const int32_t xMilliMs2 = lroundf(xMs2 * 1000.0f);
  const int32_t yMilliMs2 = lroundf(yMs2 * 1000.0f);
  const int32_t zMilliMs2 = lroundf(zMs2 * 1000.0f);

  publishReading(millis(), xMilliMs2, yMilliMs2, zMilliMs2);
  client.loop();
}

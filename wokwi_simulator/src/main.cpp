#include <WiFi.h>
#include <PubSubClient.h>

// Wokwi provides this open access point; use your real network credentials
// only when flashing the ESP32 hardware.
const char* ssid = "Wokwi-GUEST";
const char* password = "";

// --- MQTT Broker Settings ---
// Requires the Wokwi Private IoT Gateway to reach Mosquitto on the host.
const char* mqtt_server = "host.wokwi.internal";
const int mqtt_port = 1883;
const char* mqtt_topic = "esp32/switch";

// --- Push Button Pin ---
const int buttonPin = 4; // Change to the GPIO pin connected to your button

WiFiClient espClient;
PubSubClient client(espClient);

// Variables for handling button debounce & edge detection
int lastButtonReading = HIGH;
int debouncedButtonState = HIGH;
unsigned long lastDebounceTime = 0;
const unsigned long debounceDelay = 50;
unsigned long lastMqttAttempt = 0;
const unsigned long mqttRetryDelay = 5000;
bool mqttAttempted = false;

bool setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);

  WiFi.begin(ssid, password, 6);

  const unsigned long startTime = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - startTime < 20000) {
    delay(250);
    Serial.print(".");
  }

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("\nWi-Fi connection timed out. Check that the Wokwi simulator is running.");
    return false;
  }

  Serial.println("");
  Serial.println("WiFi connected");
  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());
  return true;
}

void reconnect() {
  if (client.connected() ||
      (mqttAttempted && millis() - lastMqttAttempt < mqttRetryDelay)) {
    return;
  }

  mqttAttempted = true;
  lastMqttAttempt = millis();
  Serial.print("Attempting MQTT connection...");

  String clientId = "ESP32Client-";
  clientId += String(random(0xffff), HEX);
  if (client.connect(clientId.c_str())) {
    Serial.println("connected");
  } else {
    Serial.print("failed, rc=");
    Serial.println(client.state());
  }
}

void setup() {
  Serial.begin(115200);

  // Configure button pin with internal pull-up resistor
  // Connect the other side of the push button to GND
  pinMode(buttonPin, INPUT_PULLUP);

  client.setServer(mqtt_server, mqtt_port);
  setup_wifi();
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    setup_wifi();
    if (WiFi.status() != WL_CONNECTED) {
      delay(1000);
      return;
    }
  }

  client.loop();
  reconnect();

  // Read button state (LOW = pressed because of INPUT_PULLUP)
  int reading = digitalRead(buttonPin);

  if (reading != lastButtonReading) {
    lastDebounceTime = millis();
    lastButtonReading = reading;
  }

  if (millis() - lastDebounceTime >= debounceDelay &&
      reading != debouncedButtonState) {
    debouncedButtonState = reading;

    if (debouncedButtonState == LOW) {
      Serial.println("Button pressed.");
      if (client.connected()) {
        if (client.publish(mqtt_topic, "hi")) {
          Serial.println("Published 'hi' to MQTT.");
        } else {
          Serial.println("MQTT publish failed.");
        }
      } else {
        Serial.println("MQTT is disconnected; button was read but not published.");
      }
    }
  }
}

import paho.mqtt.client as mqtt


def on_connect(client, userdata, flags, reason_code, properties):
    print(f"Connected to MQTT broker: {reason_code}")
    client.subscribe("esp32/switch")


def on_message(client, userdata, message):
    payload = message.payload.decode("utf-8")
    print(f"{message.topic}: {payload}")


client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id="windows-mqtt-receiver",
)
client.on_connect = on_connect
client.on_message = on_message

client.connect("localhost", 1883, keepalive=60)
print("Listening for telemetry. Press Ctrl+C to stop.")
client.loop_forever()
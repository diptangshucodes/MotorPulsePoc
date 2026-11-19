# MotorPulse fleet dashboard

A React prototype for the MotorPulse motor-health monitoring and predictive-maintenance demo. The prototype screens follow the six layouts in `motorFleet_screen_draft.pdf`: Fleet overview, Motor detail, Control panel, Alerts & maintenance, Energy, and ROI & cost savings. A Live sensor page displays raw readings from the local MQTT telemetry API.

## Run the dashboard and live sensor view

```powershell
npm install
npm start
```

The app opens at `http://localhost:3000`. Fleet overview and other prototype screens use local synthetic demo data. The **Live sensor** screen instead reads the latest `motor-01` acceleration reading and recent raw history from the MQTT logger API.

Start the MQTT broker (for example, `docker compose up -d mqtt`) and, from a separate repository-root terminal, run:

```powershell
python mqtt_client.py
```

This serves the read-only local telemetry API at `http://127.0.0.1:8002` and connects to the MQTT broker to subscribe to `esp32/switch`. The API stays available and retries the broker connection if Mosquitto is temporarily offline. Raw readings are stored in the root `telemetry.sqlite3`; the ESP32 publishes one reading per MQTT message at a nominal 20 Hz. Open **Live sensor** in the dashboard to see the 3D vector follow the latest reading; the page polls the local API every 100 ms and backs off to a 3-second retry if the API is unavailable. The API can use another origin via `REACT_APP_TELEMETRY_API_URL`; the default is `http://127.0.0.1:8002`.

The chart displays raw acceleration in m/s². It does not display vibration velocity in mm/s or a real motor-health assessment. Telemetry is marked simulated by default; set `MQTT_DATA_SOURCE=real` in the logger terminal when it is receiving real equipment data.

## Generate the backend API contract

The TypeSpec source and OpenAPI output are maintained in `../backend`:

```powershell
cd ..\backend
npm install
npm run openapi
```

The generated OpenAPI 3.0 document is written to `backend/openapi/openapi.yaml`. It is a contract for the planned Python backend; the existing Express sample server is not wired to the dashboard.

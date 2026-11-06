# MotorPulse fleet dashboard

A React prototype for the MotorPulse motor-health monitoring and predictive-maintenance demo. The prototype screens follow the six layouts in `motorFleet_screen_draft.pdf`: Fleet overview, Motor detail, Control panel, Alerts & maintenance, Energy, and ROI & cost savings. A Live sensor page displays actual windows from the local MQTT telemetry API.

## Run the dashboard and live sensor view

```powershell
npm install
npm start
```

The app opens at `http://localhost:3000`. Fleet overview and other prototype screens use local synthetic demo data. The **Live sensor** screen instead reads the latest `motor-01` sample window and acceleration history from the MQTT logger API.

Start the MQTT broker (for example, `docker compose up -d mqtt`) and, from a separate repository-root terminal, run:

```powershell
python mqtt_client.py
```

This subscribes to `esp32/switch`, stores windows in the root `telemetry.sqlite3`, and serves the read-only local telemetry API at `http://localhost:8002`. Start or restart the Wokwi simulation to publish new windows, then open **Live sensor** in the dashboard. The page polls every 1.5 seconds. The API can use another origin via `REACT_APP_TELEMETRY_API_URL`; the default is `http://localhost:8002`.

The chart displays raw acceleration in m/s² and mean-centered acceleration RMS. It does not display vibration velocity in mm/s or a real motor-health assessment. Telemetry is marked simulated by default; only set `MQTT_DATA_SOURCE=real` when the logger is receiving real equipment data.

## Generate the backend API contract

The TypeSpec source and OpenAPI output are maintained in `../backend`:

```powershell
cd ..\backend
npm install
npm run openapi
```

The generated OpenAPI 3.0 document is written to `backend/openapi/openapi.yaml`. It is a contract for the planned Python backend; the existing Express sample server is not wired to the dashboard.

# MotorPulse edge AI prototype

This is a small Python service for experimenting with vibration anomaly detection. The first detector learns a per-motor healthy baseline from sensor windows, then compares new windows with that baseline. It is an explainable statistical prototype, not a trained fault classifier or a remaining-life prediction model.

## Run in Docker Desktop

1. Start Docker Desktop and wait for its engine to become available.
2. From the repository root, run:

   ```powershell
   docker compose up --build
   ```

3. Open `http://localhost:8001/docs` for the interactive API, or check `http://localhost:8001/health`.
4. Stop the service with `Ctrl+C`; use `docker compose down` to remove its container. The named `motorpulse-ai-data` volume preserves learned baselines.

The same Dockerfile can be built for a Raspberry Pi after its OS architecture is confirmed. The Windows installation of Python is used only for local tests; Docker installs its own Linux Python runtime and dependencies into the image.

The service's TypeSpec definition is in `specs/main.tsp`; from `backend`, run `npm run openapi:ai` to generate `openapi/edge-ai/openapi.yaml`.

## Capture MQTT telemetry locally

From the repository root, run `python mqtt_client.py` while the Mosquitto broker is running. The client validates each firmware window and stores its receive time, topic, motor ID, sample rate, window metadata, original JSON payload, and calculated acceleration features in `telemetry.sqlite3` at the repository root. Set `MQTT_DATABASE_PATH` to choose another database file, `MQTT_HOST` and `MQTT_PORT` to connect to a different broker, or `MQTT_DATA_SOURCE=real` when recording a real motor. The source defaults to `simulated`; existing windows are migrated and backfilled with acceleration features as the client starts. Invalid windows are reported and skipped.

The logger converts the scaled X/Y/Z samples to m/s^2, calculates each axis's mean acceleration, mean-centered RMS, and peak-to-peak range, plus a combined mean-centered vector RMS. For example, a stationary sensor may report about 9.81 m/s^2 mean acceleration on Z due to gravity, while its Z-axis dynamic RMS remains zero after subtracting that mean. These are acceleration features, not vibration velocity (mm/s), and must not be sent to the current AI API as velocity features. Mark simulated and real recordings separately; simulated windows are for exercising the pipeline, not for a real motor's healthy baseline or fault model.

Query the saved windows by source to avoid mixing simulations with physical equipment:

```sql
SELECT received_at, motor_id, accel_x_rms_ms2, accel_y_rms_ms2,
       accel_z_rms_ms2, accel_vector_rms_ms2
FROM telemetry_windows
WHERE data_source = 'simulated'
ORDER BY id DESC
LIMIT 10;
```

Run the logger tests with `python -m unittest -v test_mqtt_client.py`.

## Learn and use a baseline

The ESP32 firmware publishes raw, timestamped MPU6050 acceleration windows (128 samples at a nominal 100 Hz) to MQTT. These are acceleration measurements in m/s^2, not the vibration velocity samples this API expects, so they cannot be submitted directly. Convert and validate the captured signals before calling this API. The MPU6050's on-chip temperature is not motor temperature; RPM, motor temperature, and current also require separate sources before they can be included in API requests.

For each real motor, collect at least five vibration windows while that motor is operating normally and steadily. Submit those windows to `POST /v1/motors/{motor_id}/baseline`. The service persists each baseline in `/data`.

Then send a new window to `POST /v1/motors/{motor_id}/analyze`. Each window must include vibration samples, their sample rate, motor RPM, temperature, and current. A window needs at least 16 samples; 128 or more samples is a better starting point for the demo. Sample rate and window length determine which vibration frequencies can be distinguished.

The response includes the calculated vibration RMS, peak-to-peak value, dominant frequency, anomaly score, status, and the feature that deviated most from the baseline. This service does not issue motor commands. Do not use prototype scores as a safety system or as a claim of remaining useful life.

Run local tests without Docker from the repository root:

```powershell
python -m unittest discover -s backend\ai-service -p "test_*.py" -v
```

## Two real motors plus demo data

Learn a separate baseline for each physical motor. Keep the remaining eight synthetic motors in the dashboard/demo data source; do not train their baselines on simulated readings unless they are clearly separated from real equipment in the UI and API.

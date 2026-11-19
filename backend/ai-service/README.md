# MotorPulse edge AI prototype

This is a small Python service for experimenting with motor anomaly detection. It learns a per-motor healthy baseline from acceleration, temperature, and current windows, then compares new windows with that baseline. It is an explainable statistical prototype, not a trained fault classifier or a remaining-life prediction model.

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

From the repository root, run `python mqtt_client.py` while Mosquitto is running. The client stores raw acceleration and optional sensor readings in `telemetry_readings`, and creates non-overlapping 128-sample `telemetry_sensor_windows` when vibration samples are continuous and fresh temperature/current readings are available. Legacy batch windows remain in `telemetry_windows`.

The collector defaults to `MQTT_DATA_SOURCE=simulated`; set it to `real` before starting it for physical motor data. Simulated and real windows must not be mixed for baseline learning. `MQTT_DATABASE_PATH`, `MQTT_HOST`, and `MQTT_PORT` can be set to change the database or broker. Invalid MQTT messages are reported and skipped. Prepared windows that are missing fresh temperature/current data or have large acceleration gaps are not created.

The telemetry API starts before the MQTT connection and remains available while the client retries a broker connection. Check `http://127.0.0.1:8002/health` for the API and its `mqtt_connected` status. If it reports `false`, check that Mosquitto is running and that `MQTT_HOST`/`MQTT_PORT` point to the broker.

For a physical expo motor, use a separate PowerShell terminal and mark the collector source as real before starting it:

```powershell
$env:MQTT_DATA_SOURCE = "real"
python mqtt_client.py
```

Keep the MQTT logger running while capturing and labeling windows. The environment variable applies only to that PowerShell process.

Raw readings retain each X/Y/Z value in m/s^2. The collector converts the firmware's integer milli-m/s^2 axes to SI units when it assembles a window. Temperature and current retain their own sample timestamps; repeated values on acceleration messages are not treated as new measurements. The AI API now consumes `acceleration_samples` with named X/Y/Z axes in m/s^2, so raw acceleration is never mislabeled as velocity. The ESP32 does not currently measure RPM; RPM is optional in the request, so keep the demo motor at a consistent speed/load and do not claim speed-compensated analysis.

Query raw readings by source to avoid mixing simulations with physical equipment:

```sql
SELECT received_at, motor_id, sample_time_ms, accel_x_milli_ms2,
       accel_y_milli_ms2, accel_z_milli_ms2, temperature_c,
       current_amps, current_sample_time_ms, current_sample_count
FROM telemetry_readings
WHERE data_source = 'simulated'
ORDER BY id DESC
LIMIT 10;
```

List windows and labels for a motor at `http://127.0.0.1:8002/api/motors/motor-01/windows?source=real`. Filter by `label=healthy` to prepare a baseline set. The logger keeps the latest 5,000 prepared windows per motor.

Run the logger tests with `python -m unittest -v test_mqtt_client.py`.

## Mark, learn, and test a baseline

The current ESP32 publishes MPU6050 X/Y/Z acceleration at a nominal 100 Hz, plus valid DS18B20 temperature and ACS712 one-second RMS current fields. The collector groups 128 acceleration samples (about 1.28 seconds at 100 Hz) and associates recent temperature/current values. It discards windows with sample gaps or stale/missing slow-sensor readings. The AI API removes the per-axis mean (including the static gravity offset) and calculates acceleration vector RMS, maximum axis peak-to-peak, dominant frequency, temperature, and current.

The MQTT collector exposes local labeling and window APIs:

- `GET /api/motors/{motor_id}/windows?source=real&limit=100` lists captured windows and their labels. New windows start as `unknown`.
- `POST /api/motors/{motor_id}/windows/{window_id}/label` accepts `{"label":"healthy","notes":"..."}` or a reviewed `suspected_fault` / `confirmed_fault` label. `fault_type` is required for `confirmed_fault`. Only mark a window healthy after checking that the motor was operating normally; an AI alert by itself is not a fault label.

Example PowerShell label command:

```powershell
$labelBody = @{ label = "healthy"; notes = "Inspected; steady operation." } | ConvertTo-Json
$windowId = 123 # Replace with the window_id from the windows listing endpoint.
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8002/api/motors/motor-01/windows/$windowId/label" `
  -Method Post -ContentType "application/json" -Body $labelBody
```

Collect a healthy baseline with the same motor mounting, speed, and load. The API requires at least five healthy windows (a code minimum, not a reliability target) and accepts at most 500 per request. Fetch only real, manually verified healthy windows and send them to the edge AI:

```powershell
$healthy = Invoke-RestMethod `
  -Uri "http://127.0.0.1:8002/api/motors/motor-01/windows?label=healthy&source=real&limit=100"
$windows = @($healthy.windows | ForEach-Object { $_.sensor_window })
if ($windows.Count -lt 5) { throw "At least five labeled healthy windows are required." }
$baselineBody = @{ windows = $windows } | ConvertTo-Json -Depth 20
Invoke-RestMethod `
  -Uri "http://localhost:8001/v1/motors/motor-01/baseline" `
  -Method Post -ContentType "application/json" -Body $baselineBody
```

Test a later, separate window against the learned baseline:

```powershell
$captured = Invoke-RestMethod `
  -Uri "http://127.0.0.1:8002/api/motors/motor-01/windows?label=unknown&source=real&limit=1"
$testWindow = $captured.windows[-1].sensor_window
$testBody = $testWindow | ConvertTo-Json -Depth 20
Invoke-RestMethod `
  -Uri "http://localhost:8001/v1/motors/motor-01/analyze" `
  -Method Post -ContentType "application/json" -Body $testBody
```

Review the returned status, anomaly score, feature values, explanation, and the physical motor together. A warning/critical result means a feature deviated from that motor's learned baseline; it is not a diagnosis. Use separate runs for testing rather than training and testing on neighboring windows from the same capture. The RPM field is optional because the current firmware does not measure it; keep operating conditions consistent until a tachometer/encoder is added.

The baseline feature schema now uses acceleration in m/s^2. Any baseline JSON created with the earlier velocity-named feature schema must be relearned before analysis.

For fault-classifier training later, retain technician-confirmed labels and safe, representative examples for each fault class. The current detector does not train on fault labels or identify fault types. Do not create real mechanical damage for the expo; use safe operating variations or clearly labeled synthetic demonstrations, and keep simulated data out of a real-motor baseline.

Run local tests without Docker from the repository root:

```powershell
python -m unittest discover -s backend\ai-service -p "test_*.py" -v
```

## Two real motors plus demo data

Learn a separate baseline for each physical motor. Keep the remaining eight synthetic motors in the dashboard/demo data source; do not train their baselines on simulated readings unless they are clearly separated from real equipment in the UI and API.

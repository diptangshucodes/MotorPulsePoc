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

## Learn and use a baseline

For each real motor, collect at least five vibration windows while that motor is operating normally and steadily. Submit those windows to `POST /v1/motors/{motor_id}/baseline`. The service persists each baseline in `/data`.

Then send a new window to `POST /v1/motors/{motor_id}/analyze`. Each window must include vibration samples, their sample rate, motor RPM, temperature, and current. A window needs at least 16 samples; 128 or more samples is a better starting point for the demo. Sample rate and window length determine which vibration frequencies can be distinguished.

The response includes the calculated vibration RMS, peak-to-peak value, dominant frequency, anomaly score, status, and the feature that deviated most from the baseline. This service does not issue motor commands. Do not use prototype scores as a safety system or as a claim of remaining useful life.

Run local tests without Docker from the repository root:

```powershell
python -m unittest discover -s backend\ai-service -p "test_*.py" -v
```

## Two real motors plus demo data

Learn a separate baseline for each physical motor. Keep the remaining eight synthetic motors in the dashboard/demo data source; do not train their baselines on simulated readings unless they are clearly separated from real equipment in the UI and API.

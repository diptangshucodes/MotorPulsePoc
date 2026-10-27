# MotorPulse fleet dashboard

A React prototype for the MotorPulse motor-health monitoring and predictive-maintenance demo. The screens follow the six layouts in `motorFleet_screen_draft.pdf`: Fleet overview, Motor detail, Control panel, Alerts & maintenance, Energy, and ROI & cost savings.

## Run the dashboard

```powershell
npm install
npm start
```

The app opens at `http://localhost:3000`. The Expo Demo Mode switch runs a local synthetic telemetry simulator for ten motors. Navigation, charts, alert acknowledgement, work-order creation, ROI inputs, speed settings, and confirmation dialogs work locally in the browser. No backend connection is configured; simulator state is session-only.

## Generate the backend API contract

The TypeSpec source and OpenAPI output are maintained in `../backend`:

```powershell
cd ..\backend
npm install
npm run openapi
```

The generated OpenAPI 3.0 document is written to `backend/openapi/openapi.yaml`. It is a contract for the planned Python backend; the existing Express sample server is not wired to the dashboard.

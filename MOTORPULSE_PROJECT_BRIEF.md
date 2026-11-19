# MotorPulse AI: project and use-case brief

## Executive summary

MotorPulse AI is an edge-first predictive-maintenance proof of concept for rotating industrial assets such as motors, pumps, fans, compressors, and conveyor drives. It explores how vibration and related operating signals can help a maintenance team notice equipment changes earlier, investigate the cause, and schedule an inspection before a developing problem becomes an unplanned interruption.

The proposed demonstration follows a ten-motor facility. Sensors on a motor feed an ESP32; a local Raspberry Pi is intended to host the plant-side services; MQTT provides a path for device messages; an edge anomaly service compares new sensor windows with a motor-specific healthy baseline; and a React fleet dashboard presents condition, alerts, and maintenance workflows. The prototype is designed to explain this pathway and its potential business value. It is not yet a connected, validated predictive-maintenance deployment.

**Product idea:** turn machine signals into earlier, explainable, human-reviewed maintenance decisions.

**Short brand line:** Sense. Detect. Plan.

**Primary users:** maintenance engineers and technicians, facility and reliability managers, industrial operators, and leadership evaluating uptime and asset-care initiatives.

## The operational problem

Rotating equipment can degrade between fixed maintenance intervals. A motor or driven component may show changes in vibration, temperature, current, speed, or power before a visible breakdown. If the change is not noticed or acted upon, an organization may face:

- Unplanned downtime and lost production contribution.
- Emergency repair premiums, expedited parts, and overtime.
- Disruption to dependent production lines and delivery schedules.
- Missed opportunities to plan work around operating schedules.
- Energy or efficiency losses that can be difficult to identify without a trustworthy baseline.

These are plausible value levers, not quantified Ontario-wide motor-failure statistics. The project has not established a defensible public total for the dollars Ontario organizations lose specifically to motor failures. A real business case needs facility-level maintenance records, production economics, repair history, and energy data.

## Proposed solution and user workflow

1. **Sense:** collect condition and operating measurements from a motor or asset.
2. **Establish a baseline:** record known-healthy operating windows for that specific motor, under reasonably comparable operating conditions.
3. **Detect a deviation:** calculate signal features and compare new data with the asset's baseline.
4. **Explain and triage:** show the status, contributing feature, and a concise explanation so a technician can decide what to inspect.
5. **Plan work:** acknowledge an alert, create a work order, and schedule an inspection or repair.
6. **Verify value:** compare confirmed stops and repair outcomes with the site's own historical baseline; calculate avoided cost only where the evidence supports it.

MotorPulse AI is intended to assist people, not to replace technician diagnosis or plant safety systems. Autonomous stopping, derating, or speed control is not part of the implemented edge-AI service.

## Proposed system architecture

```text
Motor / driven equipment
  -> vibration and other condition sensors
  -> ESP32 sensor node over Wi-Fi
  -> MQTT broker (Mosquitto)
  -> edge anomaly-analysis API (FastAPI / Python)
  -> fleet dashboard (React)
  -> technician review, work planning, and site validation
```

The Raspberry Pi is the intended local host for the broker, edge AI service, and eventually the dashboard. The development setup also supports local Docker Desktop. The services are intended to remain close to the equipment and can be evaluated without assuming that plant telemetry is sent to a cloud service.

### Connection and integration status

| Component | Purpose | Current project status |
|---|---|---|
| Motor / asset | Equipment whose condition should be monitored | Ten illustrative assets are defined in the dashboard. |
| Sensors | Measure vibration and, where instrumented, temperature, current, RPM, or power | The ESP32 sketch reads an MPU6050, DS18B20, and ACS712. Physical wiring, sensor calibration, mounting, and motor-on tests still need verification. The Wokwi diagram currently shows only the MPU6050. |
| ESP32 | Read sensors and send device messages over Wi-Fi | Publishes one raw X/Y/Z acceleration reading per MQTT message at a nominal 100 Hz, with the most recent valid motor temperature and one-second current RMS as optional fields. It omits unavailable temperature/current readings rather than substituting dummy values. |
| Mosquitto | Local MQTT message broker | Included in `docker-compose.yml`; the configured port is 1883. |
| MQTT telemetry logger | Validate, retain, label, and prepare motor telemetry | `mqtt_client.py` stores sensor fields, assembles 128-sample windows when sensor readings are fresh, and exposes local window-label/list endpoints. It does not automatically forward windows to the AI API. |
| Edge AI service | Learn a per-motor baseline and analyze a sensor window | Implemented as a standalone FastAPI service with `/health`, baseline, and analysis endpoints. Window bodies can be submitted from the telemetry API; the service is not automatically wired to MQTT or the React dashboard. |
| Node / Express service | Basic backend example | `backend/server.js` exposes only `/api/hello` on port 5000; it is not the dashboard data or command API. |
| React dashboard | Demonstrate fleet condition, diagnostics, alerts, controls, energy, and ROI workflows | Six interactive screens are implemented. Their values and actions are local demo state; telemetry and controls are not connected to the broker or physical motors. |
| Raspberry Pi | Intended edge host | Intended deployment target, subject to confirming OS and CPU architecture and testing the containers there. |

`docker-compose.yml` currently starts Mosquitto and the FastAPI edge-AI service. The React frontend is a separate application and is not included as a service in that Compose file.

## Edge-AI behavior today

The service in `backend/ai-service/main.py` is an explainable statistical anomaly detector, not a trained fault classifier or remaining-useful-life model.

- A sensor window includes three-axis acceleration samples in m/s^2, sample rate, temperature, and one-second RMS current. RPM is optional because the current firmware does not measure it.
- The service removes each axis mean and extracts acceleration vector RMS, maximum axis peak-to-peak, dominant frequency, temperature, and current.
- A motor-specific baseline is learned from at least five known-healthy windows. The service stores baseline medians and median absolute deviations in its data directory.
- For each new window, the service measures feature deviations from that motor's baseline and returns a status (`normal`, `warning`, or `critical`), an anomaly score, the strongest contributing feature, and a plain-language explanation.
- The API accepts windows with at least 16 and up to 8,192 three-axis acceleration samples. The MQTT logger currently creates 128-sample windows at a nominal 100 Hz. Sample rate and window length affect which frequencies can be distinguished.
- The current API is `POST /v1/motors/{motor_id}/baseline` and `POST /v1/motors/{motor_id}/analyze`. Interactive API documentation is available at `/docs` when the service is running.

**What the edge AI does not do:** identify a confirmed mechanical fault, calculate a validated failure probability or failure date, prove that a machine is safe, or issue motor commands. Prototype scores must not be used as a safety function or represented as a validated remaining-life prediction.

The telemetry logger creates prepared windows and allows a user to mark individual windows as `healthy`, `unknown`, `suspected_fault`, or `confirmed_fault`. Only technician-verified healthy windows should train the current baseline. The three sensor types provide complementary condition context, but adding sensors alone does not establish improved accuracy. At 100 Hz, the MPU6050 is suitable only for lower-frequency demonstration signals, not comprehensive bearing-fault detection. Hold speed/load constant until RPM is measured and incorporated into operating-condition handling.

## Dashboard experience

The React app in `frontend/src/App.js` has six navigable screens. They are useful as a concept and workflow demonstration; they do not represent connected plant data.

### 1. Fleet overview

- Ten pre-seeded motor cards with status, health score, RPM, temperature, vibration, and current.
- Fleet KPI cards for online count, condition categories, energy, and a running savings figure.
- Motor selection opens the detail view.
- A timer changes the seeded readings slightly every 2.5 seconds while demo simulation is enabled.

### 2. Motor detail

- Example condition summary, health gauge, anomaly score, and illustrative fault-probability bars.
- Trend visuals for vibration/temperature and current, plus FFT-style and frequency-waterfall-style graphics.
- Event/command history and fault-injection buttons for imbalance, bearing wear, and overheating.
- Fault injection changes local demo state and adds an alert; it does not stimulate a physical motor or run the edge-AI API.
- The detail view contains example statements such as confidence, fault probability, and days to failure. These are static illustrative copy, not model outputs, and must not be presented as validated findings.

### 3. Control panel

- Demo controls for Manual, Scheduled, and AI-assisted labels; a speed setpoint; per-motor start/stop; and an emergency-stop-all interaction.
- Confirmation dialogs and a local audit-style log demonstrate a safety-conscious workflow.
- All commands update browser state only. The interface does not send commands to an ESP32, PLC, VFD, or real motor. The UI's safety labels are not a certified or implemented safety interlock.

### 4. Alerts and maintenance

- Seeded alerts can be acknowledged; a work-order flow updates demo state.
- The page shows an illustrative maintenance calendar, recommendations, parts notice, and history.
- These records and recommendations are not connected to a CMMS or maintenance database.

### 5. Energy

- Illustrative fleet power, consumption, cost, efficiency, and carbon views.
- Calculations use seeded motor values and fixed example assumptions, not metered energy or verified efficiency measurements.

### 6. ROI savings

- Inputs represent downtime cost per hour, planned and unplanned repair costs, replacement cost, energy tariff, and technician rate.
- The screen contains hard-coded headline metrics and example charts. Although input controls update a prototype calculation, the displayed scenario is not a validated customer result or connected financial report.

The React app has tests for the ten-motor overview, navigation to motor detail, command confirmation, emergency-stop demo behavior, and demo fault injection. The presence of these tests verifies UI interactions only; it does not verify physical connectivity.

## Sensors and hardware direction

The current ESP32 proof-of-concept sketch is configured for:

- **Vibration:** MPU6050 acceleration on I2C SDA GPIO 21 / SCL GPIO 22. It publishes raw X/Y/Z acceleration in m/s^2 at a nominal 100 Hz. The accelerometer is configured for ±8 g with a 44 Hz filter bandwidth; this is suitable for a low-frequency expo demonstration, not high-frequency bearing-fault diagnosis. Rigid mounting and higher-rate, calibrated acquisition may be needed for a real asset.
- **Temperature:** DS18B20 data on GPIO 4. The sketch requests asynchronous 10-bit conversions and adds `temperature_c` and its sample timestamp when a valid reading is available. The probe should be attached securely to the motor casing at a repeatable point; it measures surface temperature, not winding temperature.
- **Current:** ACS712 output is read on ADC1 GPIO 34. The sketch calculates one-second RMS current from ADC samples, using a zero-current offset captured during startup. The configured sensitivity is 185 mV/A (ACS712-5A); change it to 100 mV/A for the 20 A version or about 66 mV/A for the 30 A version, and calibrate against a suitable reference. The example assumes a 1/2 output divider ratio (10 kΩ from module output to ADC, 10 kΩ from ADC to ground) to leave margin below the ESP32 input limit for a 5 V sensor output. Verify the module, divider, ADC readings, and actual current before relying on the result.
- **Speed / RPM:** not currently measured by the sketch. It is optional in the prototype API and is not currently used as a model feature; keep speed/load steady for comparisons and add a tachometer, encoder, or trusted drive measurement before handling variable-speed operation.
- **ESP32 and edge host:** the ESP32 publishes to the configured MQTT topic. Mosquitto, the telemetry logger, AI API, and React dashboard are not yet a complete end-to-end live pipeline.

### ESP32 MQTT message

The sketch publishes one JSON message for each acceleration sample on `esp32/switch`. The acceleration timestamp is milliseconds since ESP32 boot. `temperature_c` and its timestamp appear only after a valid DS18B20 reading; `current_amps` and its timestamp/count appear only after a valid one-second current window.

```json
{
  "schema_version": 2,
  "message_type": "acceleration",
  "motor_id": "motor-01",
  "sample_rate_hz": 100,
  "sample_time_ms": 12345,
  "acceleration_unit": "m/s^2",
  "acceleration_scale": 0.001,
  "accel_x_milli_ms2": 120,
  "accel_y_milli_ms2": -45,
  "accel_z_milli_ms2": 9810,
  "temperature_c": 31.5,
  "temperature_sample_time_ms": 12340,
  "current_amps": 0.42,
  "current_unit": "A",
  "current_measurement": "rms_1s",
  "current_sample_time_ms": 12300,
  "current_sample_count": 1980
}
```

The values above are illustrative. Acceleration axes are integer milli-m/s^2 values; divide by 1,000 to get m/s^2. The current is a one-second RMS estimate, not an instantaneous reading. These messages are raw telemetry and are not submitted directly to the edge-AI API.

Use the ACS712 only with an appropriately rated, isolated low-voltage expo motor circuit and a correctly rated module. Do not connect ESP32 pins or a hobby breakout directly to hazardous mains. Have qualified personnel review any current-sensing installation on mains-powered equipment. The motor must have no current flowing while the firmware calibrates the ACS712 zero offset at startup.

### Office expo: next steps

1. **Wire and inspect with power off.** Keep the MPU6050 on GPIO 21/22, connect the DS18B20 data line to GPIO 4 with a 4.7 kΩ pull-up to 3.3 V, and route the ACS712 output through the documented divider to GPIO 34. Confirm common ground for the low-voltage sensor circuit and check the ESP32 input voltage before powering it.
2. **Bring up one sensor at a time.** Confirm the MPU6050 is detected, the DS18B20 produces plausible casing temperatures, and the ACS712 reports near zero with no current and a plausible RMS value under a known low-voltage load. Keep the motor off during firmware startup/current-offset calibration.
3. **Verify MQTT before the demo.** Start Mosquitto and the telemetry logger, set `MQTT_DATA_SOURCE=real` for physical readings, and confirm messages arrive on `esp32/switch`. Each acceleration message is sent at a nominal 100 Hz; valid temperature and the latest one-second current RMS are additional JSON fields. Temperature/current are currently retained in the raw payload, but are not yet queryable as dedicated telemetry fields or shown by the dashboard.
4. **Make the mechanical setup repeatable.** Secure the motor and sensor, keep the same sensor position and motor speed/load during healthy captures, and use a guarded low-voltage setup. Do not create real damaged bearings or unsafe imbalance for the expo; use clearly labeled simulated/test data for anomaly demonstrations.
5. **Label and prepare windows.** The MQTT logger now creates 128-sample windows, stores the sensor values, and exposes endpoints to label/list them. Mark `healthy` only after a normal operation has been verified; leave unverified windows as `unknown`. Keep speed/load steady because RPM is not currently measured.
6. **Establish and evaluate the baseline.** Fetch at least five verified healthy, real-source windows, submit them to the edge AI baseline endpoint, and test with later windows from a separate run. Review alerts with a human. Keep simulated and physical data separate. For a meaningful fault classifier, gather correctly labeled, representative data using a safe training rig; the current baseline detector does not learn fault categories or predict failure dates.

## Ontario / Canada context

Statistics Canada's 2023 provincial GDP release reported that Ontario's real GDP grew **1.6% in 2023** and that Ontario was the largest provincial contributor to Canada's economic growth, accounting for almost half of the 1.2% national increase. This is general economic context only. It is not a measure of industrial motor-failure losses, downtime costs, or potential MotorPulse AI savings.

**Source:** Statistics Canada, [“Gross domestic product by industry: Provinces and territories, 2023”](https://www150.statcan.gc.ca/n1/daily-quotidien/240501/dq240501a-eng.htm), released May 1, 2024.

## Transparent illustrative financial scenario

The project’s client-projection deck models a 25-motor facility using the following assumptions. The poster scales event count linearly to a 10-motor scenario. None of these inputs are claimed to be measured Ontario averages.

### Assumptions

| Input | Assumption |
|---|---:|
| Reference fleet size in internal scenario | 25 motors |
| Reference unplanned failures | 6 events/year |
| Unplanned downtime per event | 8 hours |
| Production contribution at risk per downtime hour | CAD $1,500 |
| Emergency repair cost | CAD $4,500/event |
| Planned repair cost | CAD $850/event |
| Early-planning conversion sensitivity | 20% / 30% / 40% |

### 10-motor arithmetic

- Expected events: `6 x (10 / 25) = 2.4 events/year`.
- Production contribution at risk: `2.4 x 8 x $1,500 = $28,800/year`.
- Emergency repair premium: `2.4 x ($4,500 - $850) = $8,760/year`.
- Modeled annual exposure: `$28,800 + $8,760 = $37,560/year`.
- Gross opportunity at 20%: `$37,560 x 20% = $7,512/year`.
- Gross opportunity at 30%: `$37,560 x 30% = $11,268/year`.
- Gross opportunity at 40%: `$37,560 x 40% = $15,024/year`.
- Potential production capacity recovered at 30%: `2.4 x 8 x 30% = 5.76 hours/year` (about 5.8 hours).

The gross opportunity is **not net savings, ROI, or guaranteed cash savings**. It assumes capacity made available by avoiding downtime can be recovered as saleable production. It excludes MotorPulse deployment and operating costs, energy savings, and labor savings. For the original 25-motor model, the internal deck separately illustrates an $18,000 year-one program-cost assumption; that assumption is not product pricing and has not been applied to the poster's 10-motor scenario.

### How to validate a facility case

1. Select the assets where a stop materially constrains production.
2. Review at least 12 months of stop records, work orders, repair invoices, parts, overtime, and production schedules.
3. Agree on what “downtime cost per hour” means: contribution margin or genuinely avoidable cost, not automatically gross revenue.
4. Separate planned work from unplanned failures; account for repeat incidents and shared downtime.
5. Confirm whether recovered production can be made up, sold, and delivered.
6. Record implementation, sensor, support, and maintenance costs before calculating net value, ROI, or payback.
7. Run a read-only pilot and let site staff label alerts and verify outcomes before any savings claim.

## Pilot plan and proof points

The client-projection deck suggests a staged pilot; this remains a proposal rather than a completed site deployment.

1. **Qualify (weeks 0-2):** select two critical motors, identify owners, inspect sensor mounting options, agree on downtime definitions, and collect 12 months of CMMS and production records.
2. **Baseline (weeks 2-4):** connect real sensors, validate timestamps and operating state, and learn at least five known-healthy windows for each physical motor.
3. **Shadow operation (weeks 5-12):** operate read-only; have technicians review alerts and record actionability, false positives, diagnosis effort, and lead time. Do not automate control.
4. **Evaluate:** compare sensor data coverage and alert usefulness with real stops, repairs, and planned work. Calculate site-specific value after all program costs.
5. **Scale or stop:** expand only if signal quality is reliable, maintenance staff trust and verify the alerts, and customer-specific net ROI is positive.

Suggested measures include data coverage, sensor fault rate, alerts reviewed, actionable-alert rate, false-positive rate, time from alert to inspection, diagnosis labor, planned-versus-emergency work, unplanned stop hours, repair cost, and verified recovered production.

## Key risks and guardrails

- **Data quality:** vibration signatures vary with speed, load, sensor placement, and operating state; compare like with like and retain data-quality visibility.
- **Model scope:** describe the current output as anomaly detection against a baseline, not a named fault diagnosis or failure prediction.
- **Human oversight:** keep the initial pilot read-only; have a qualified technician verify the physical condition and decide what work to perform.
- **Physical controls:** never represent browser UI controls as physical control. Any later control integration requires a separate, qualified controls-engineering and safety assessment.
- **Financial claims:** distinguish exposure, gross opportunity, net savings, and ROI; show assumptions and sources beside the figures.
- **Privacy and operations:** use customer-approved access, networking, data retention, and change-management practices before a site pilot.

## Project assets

- `frontend/src/App.js` and `frontend/src/App.css` — React dashboard and its visual design.
- `frontend/src/App.test.js` — focused dashboard interaction tests.
- `frontend/motorFleet_screen.md` — original dashboard-use-case requirements and design brief.
- `backend/ai-service/main.py` — baseline/anomaly API implementation.
- `backend/ai-service/README.md` — API workflow, operating caveats, Docker instructions, and local test command.
- `backend/ai-service/test_main.py` — edge-AI API tests.
- `backend/ai-service/specs/main.tsp` — TypeSpec definition for the edge-AI API.
- `backend/server.js` — separate minimal Express hello-world endpoint.
- `docker-compose.yml` — Mosquitto and edge-AI services.
- `mosquitto/config/mosquitto.conf` — local broker configuration.
- `wokwi_simulator/src/main.cpp` — ESP32/Wokwi button-to-MQTT sample.
- `MotorPulse_Motor_Connection_Diagram.png` — current architecture and connectivity-status diagram.
- `MotorPulse_Physical_AI_Pitch.pptx` — concept pitch.
- `MotorPulse_Physical_AI_Client_Projection.pptx` — client discussion and explicitly illustrative financial scenario.
- `MotorPulse_AI_Ontario.png` — Ontario 10-motor infographic based on the scenario above.
- `profilePic.jpg` — provided portrait, used in the infographic.

## Naming

Use **MotorPulse AI** as the presentation/product name. “MotorPulse” is also used for the prototype code and service name. The owner/presenter name supplied for the infographic is **Diptangshu Dolui**.

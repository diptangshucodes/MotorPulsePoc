# MotorPulse motor monitoring: research and product direction

**Prepared:** 25 November 2026  
**Scope:** Industrial motor and driven-equipment condition monitoring, sensing, ML, product design, and a practical MotorPulse roadmap.

## Executive recommendation

MotorPulse should be designed as an **asset- and operating-condition-aware condition-monitoring system**, not as one universal “motor fault AI.” Motors differ in construction and control, while the connected pump, fan, gearbox, or process can create signals that look like motor faults. Record what the asset is, how it is operated, how it is sensed, and what was physically verified before interpreting a model result.

For the current proof of concept:

1. Keep the product **read-only and technician-led**.
2. Keep the existing per-motor healthy-baseline detector as an **anomaly flag**, not a fault classifier or remaining-life predictor.
3. First improve signal quality and operating context: confirm sensor mounting/calibration, add motor speed and run/load state, reconcile sample-rate documentation, and retain raw vibration windows.
4. Pilot on two real, important motors under a controlled shadow-mode process. Separate real and simulated telemetry.
5. Add fault classification only after collecting enough independently verified examples. Treat remaining useful life (RUL) as a later research program requiring run-to-failure or well-characterized degradation histories.

An anomaly means “this measurement differs from this asset’s learned normal behavior.” It does **not** by itself establish the cause, severity, or time to failure.

## 1. What “different kinds of motors” means for the product

The first decision is not merely the motor technology; it is the **asset being monitored**: motor, coupling, driven machine, mounting, and operating process together.

| Motor / drive family | Common use | Useful context and signal differences |
|---|---|---|
| Three-phase induction (squirrel-cage or wound-rotor) | Pumps, fans, compressors, conveyors | A strong first industrial target. Capture bearing-housing vibration, speed, load/current, and ideally phase electrical measurements. Relevant mechanisms include bearing wear, imbalance, misalignment, looseness, rotor/stator electrical issues, and supply imbalance. |
| Synchronous / permanent-magnet (PMSM) | Efficient drives, pumps, machine tools | Speed can change rapidly under drive control. Use encoder/VFD speed and operating state; drive current and torque/position telemetry can be valuable. Do not compare measurements from different speeds as if they were equivalent. |
| Brushless DC (BLDC) | Fans, pumps, appliances, light industrial equipment | Commutation and PWM affect current/acoustic signatures. Capture controller/commutation state where available; mechanical and bearing monitoring still applies. |
| Brushed DC / universal | Small machinery, portable or legacy equipment | Brush and commutator wear can produce electrical noise, current ripple, and acoustic changes. These signatures differ from induction-machine assumptions. |
| Stepper | Positioning and indexing systems | Missed steps, stall, excessive load, overheating, and position error may matter more than conventional rotating-machine vibration thresholds. Controller and position feedback are useful. |
| Servo motor and drive | Robotics, CNC, automated machinery | The drive’s speed, torque/current, following error, and alarm history are high-value contextual signals; vibration is complementary. Follow the machine builder’s control and safety requirements. |

These are not mutually exclusive diagnostic taxonomies. Create an asset record that includes at minimum: motor type, manufacturer/model, rated power, rated voltage/current, poles or rated speed, bearing/coupling details when known, drive/VFD type and speed range, driven equipment, mounting orientation, sensor locations, and process/load regime. Unknown fields should remain explicitly unknown, not be guessed.

### How MotorPulse should classify and use an asset

“Classifying the motor” is **asset identification and metadata**, not the same task as classifying a fault. MotorPulse needs to know what equipment it is observing so it can select suitable sensors, features, operating ranges, and baseline conditions. The model should not infer a definitive motor type or fault from a vibration score alone.

Use a small, hierarchical asset profile rather than one flat label:

1. **Motor construction:** induction, synchronous/PMSM, BLDC, brushed DC, stepper, or other/unknown. Some industry terms overlap; for example, BLDC and PMSM can describe related permanent-magnet machines, so allow manufacturer/model and verified drive details to refine the record.
2. **Electrical/control setup:** phase count and supply where known; direct-on-line, VFD/inverter, servo drive, or other control; fixed-speed or variable-speed operation.
3. **Driven asset:** pump, fan, compressor, conveyor, gearbox, spindle, or other load. Record process regime where it changes vibration or load.
4. **Installation and sensing profile:** bearing/sensor locations, axes, sensor model/bandwidth, mounting, sample rate, and calibration.
5. **Current operating state:** measured speed, run/stop/transient state, and a load/process proxy. These values change over time and should be telemetry, not static motor identity fields.

**Why it changes the analysis:**

- An induction motor’s supply/rotor behavior is not interchangeable with the commutation/PWM behavior of a permanent-magnet motor and its inverter.
- A variable-speed motor’s vibration frequencies move with shaft speed; order-based comparisons need measured speed. A speed setpoint alone may not equal actual speed.
- A stepper or servo may be better monitored with controller state, position error, or torque/current telemetry alongside vibration.
- A pump, fan, or gearbox can create condition changes that appear at the motor sensor. The driven asset and process regime help avoid blaming the motor for a load/process change.
- Sensor bandwidth and sampling requirements depend on the target condition and mounting, not just the motor’s nameplate category.

**Recommended onboarding workflow:**

1. A technician creates the asset and enters or scans the nameplate. A future OCR integration may suggest values, but a person confirms them.
2. The technician selects the drive/control and driven-equipment profile, records sensor placement, and marks uncertain values as `unknown`.
3. MotorPulse checks that the installed sensor and measured sample rate are appropriate for the selected monitoring profile. If not, it reports the limitation rather than enabling unsupported fault claims.
4. The system captures operating context and learns a healthy baseline **for that individual motor and comparable operating regime**.
5. Analysis routes to features/model capabilities that are supported by the asset metadata and sensor quality. A shared model may support a compatible motor cohort, but each asset still has its own baseline and validation history.
6. If the type or operating regime is unknown, the system can still show raw telemetry and conservative generic deviations; it should label the asset as unclassified and avoid type-specific diagnosis.

Store identity/configuration separately from telemetry. A practical first schema is `motor_type`, `phase_count`, `drive_type`, `variable_speed`, `rated_speed_rpm`, `driven_equipment_type`, `sensor_profile`, `classification_source`, `verified_by`, and `verified_at`; keep actual `rpm`, `run_state`, and `load_proxy` on timestamped measurements. Version this metadata and keep historical values when equipment, drive, sensors, or mounting change, because each change can invalidate a baseline.

For the current prototype, this means adding asset metadata and operating-state capture before building a multi-motor classifier. The existing API baseline is keyed only by motor ID and its features do not use motor type or RPM; until that changes, use it only under controlled, comparable operating conditions. Never combine unrelated motors’ windows into one baseline merely because their nameplates look similar.

### Faults and events worth representing

- **Mechanical motor/rotor:** imbalance, shaft/coupling misalignment, looseness, resonance, rub, bearing/lubrication wear, rotor eccentricity, and (where relevant) rotor-bar issues.
- **Electrical:** phase/current imbalance, abnormal supply, winding/insulation problems, and drive-related behavior.
- **Driven equipment:** pump cavitation or blockage, fan/blade issues, gearbox wear, belt/coupling problems, compressor/process changes, and external vibration transmitted through the structure.
- **Non-fault operating events:** start/stop, speed ramp, load/process change, maintenance, sensor movement, sensor dropout, and nearby machine operation.

Many mechanisms can produce overlapping patterns. For example, a change near running-speed harmonics is a clue, not a unique diagnosis. Show candidate evidence and ask for inspection rather than mapping one peak directly to one fault.

## 2. Sensor plan: start with reliable measurements

### Recommended signals

| Signal | What it can add | Important limitations / requirements |
|---|---|---|
| Triaxial accelerometer near a bearing | Broad mechanical condition, impacts, imbalance/misalignment clues, trends | Bandwidth, noise floor, range, mounting stiffness, orientation, and sampling rate must fit the fault bands of interest. Low-cost MEMS can be useful for low-frequency demonstrations but may not support high-frequency bearing analysis. |
| Industrial accelerometer (often IEPE/ICP) | Higher bandwidth and better repeatability for vibration diagnostics | Requires a suitable signal conditioner/DAQ, careful installation, and a target-specific measurement plan. |
| Shaft speed / tachometer / encoder | Converts frequency to running-speed orders; supports variable-speed analysis | Essential context for changing speed. VFD setpoint is not always measured shaft speed. |
| Temperature at repeatable bearing/casing points | Slow thermal trend and corroborating evidence | Surface temperature is not winding temperature; account for ambient, load, airflow, thermal lag, and sensor placement. |
| Motor current, ideally per phase; voltage and power where feasible | Load/energy context and electrical fault clues; high-rate waveforms can enable motor-current signature analysis | A one-second RMS value is useful as a coarse load/health trend but cannot preserve line-frequency sidebands or detailed current signatures. Electrical installation must be performed with appropriately rated, isolated equipment by qualified personnel. |
| Drive/VFD telemetry | Commanded and actual speed, torque/current, alarms, starts, duty, and operating mode | Prefer approved read-only interfaces. Drive values are contextual data, not automatically independent sensor truth. |
| Acoustic / ultrasound | Airborne changes, leakage, friction, and machine-sound anomalies | Background noise and microphone placement can dominate. Treat as a separate modality and validate at the target site. |
| Oil/debris or process sensors (selected assets) | Lubrication and driven-process condition | Appropriate for certain gearboxes, hydraulic systems, pumps, and compressors; not a universal motor sensor. |

### Acquisition and installation rules

1. Decide the fault/condition bands and the highest frequency to observe **before** choosing the accelerometer, ADC, and sample rate. Apply anti-alias filtering; sample comfortably above the highest analysis frequency, not just at the Nyquist boundary.
2. Use a rigid, repeatable mounting point close to a bearing. Record sensor axis/orientation and mounting method. Re-mounting can change readings enough to invalidate a baseline.
3. Preserve calibrated raw acceleration with units, device/sensor identity, sample rate, timestamps, quality flags, and operating context. Keep derived features linked to the source window.
4. Align measurements by time, but retain each sensor’s actual measurement timestamp and cadence. Do not make a repeated slow sensor value look like a new measurement on every vibration sample.
5. Track saturation/clipping, dropped samples, gaps, sensor detach/movement, clock drift, stale slow sensors, and device resets. Exclude or flag invalid windows; do not score them as healthy.
6. Measure speed and a useful load/process proxy, or constrain the pilot to a stable, documented operating regime. Condition monitoring must compare like operating conditions.

### Assessment of the current MotorPulse prototype

The project brief and firmware describe an ESP32 with an MPU6050-class accelerometer at a nominal **100 Hz**, a **44 Hz** filter setting, a DS18B20 casing-temperature probe, and an ACS712 producing **one-second RMS current**. The edge service builds **128-sample windows** (about 1.28 seconds at 100 Hz) and calculates five features: acceleration vector RMS, maximum axis peak-to-peak, dominant frequency, temperature, and current.

That is a reasonable low-frequency demonstration path, but it is not enough to claim comprehensive bearing diagnosis:

- The nominal 100 Hz stream has a 50 Hz Nyquist limit before practical filter/edge effects; a 44 Hz accelerometer filter further limits useful bandwidth. High-frequency bearing-impact/envelope analysis needs an appropriately specified sensor and acquisition chain.
- A 1.28-second window has coarse spectral resolution (about 0.78 Hz for an unpadded FFT) and may contain too few rotations for stable statistics at lower motor speeds.
- One-second RMS current does not retain the waveform needed for motor-current signature sidebands.
- RPM is optional and is not included in the current feature schema. Varying speed/load can therefore look like a health change.
- A single dominant spectral bin discards harmonics, bands, sidebands, and transient structure.
- The DS18B20 reads casing/surface temperature, not winding temperature.
- The product brief reports 100 Hz firmware sampling, while the frontend README describes nominal 20 Hz. Resolve this documentation/configuration mismatch and verify measured device cadence before using a sample rate in analysis.

These limits do not invalidate the current MVP. They set an honest boundary: use it to demonstrate data capture, per-motor baseline deviation, and technician workflow at a controlled operating point.

## 3. Feature engineering for condition monitoring

Retain raw windows and calculate features at several time scales. A single scalar “vibration” value will not distinguish many faults.

### How the current sensors become the current ML features

The sensor does not directly output “bearing wear,” “health,” or an ML feature. It produces a physical measurement. The firmware and software turn those measurements into timestamped samples, group samples into a window, calculate numeric summaries (features), and compare those features with a baseline.

```text
physical vibration / temperature / current
  -> sensor electrical or digital output
  -> calibrated engineering units + sample timestamps
  -> quality checks and aligned time window
  -> feature calculations
  -> per-motor baseline comparison
  -> anomaly flag and explanation for technician review
```

#### 1. Vibration: MPU6050 acceleration

The accelerometer measures acceleration along X, Y, and Z. It senses both gravity and vibration. At rest, one axis will usually contain a gravity component (about 9.81 m/s², depending on orientation); the motor vibration is the changing component superimposed on that offset.

In the current firmware:

- The device is configured for ±8 g and a 44 Hz filter bandwidth, and is read at a nominal 100 samples/second.
- The firmware converts the driver’s acceleration values to m/s², rounds them into integer milli-m/s² fields, and publishes them with a device timestamp and sample-rate field.
- The collector converts milli-m/s² back to m/s², checks sample continuity, and groups 128 samples per axis into a non-overlapping window. At exactly 100 Hz, that window is 1.28 seconds. The collector also requires fresh temperature/current readings for its prepared sensor windows.
- The edge API receives named X/Y/Z samples in m/s². It assumes samples are uniformly spaced at the supplied sample rate; it does not use per-sample timestamps in the feature calculation.

The edge API currently calculates:

| Feature | Current calculation | Interpretation / limitation |
|---|---|---|
| `acceleration_vector_rms_m_s2` | First subtract the mean of each axis in the window. For each sample calculate `x² + y² + z²`; average those values across the window and take the square root. | A single measure of overall dynamic acceleration across the three axes. Mean removal removes static gravity/axis offset, but also removes any true DC component. It does not say which axis or fault caused the change. |
| `acceleration_peak_to_peak_m_s2` | Calculate `max(sample) - min(sample)` separately for each axis over the window; return the largest of the three ranges. | Captures the largest axis swing, but is sensitive to one spike and loses which axis supplied the maximum. |
| `dominant_frequency_hz` | Run an FFT on the mean-centered samples for each axis; ignore the zero-frequency bin; return the frequency bin with the largest absolute FFT magnitude across all axes. | Gives only one strongest frequency. Current implementation does not apply a window function, normalize amplitudes, preserve multiple peaks, or distinguish a motor harmonic from another vibration source. |

For an FFT window, the nominal frequency-bin spacing is `sample_rate_hz / sample_count`, and the Nyquist limit is `sample_rate_hz / 2`. With 100 Hz and 128 samples, the spacing is about 0.78 Hz and the theoretical Nyquist limit is 50 Hz; the configured 44 Hz sensor filter further constrains useful content. These settings are therefore for low-frequency trend/demo use, not high-frequency bearing-envelope features.

#### 2. Temperature: DS18B20

The DS18B20 digitally reports its local temperature. The firmware publishes the valid reading in °C with its own measurement timestamp; it does not measure winding temperature. The collector associates a recent reading with the acceleration window, and the AI API uses the supplied `temperature_c` scalar directly as the `temperature_c` feature. The edge model does not calculate a temperature trend from a single window.

For a useful thermal feature set, keep a repeatable sensor location and also capture ambient temperature and operating load. Across multiple windows calculate temperature rise above ambient, slope over time, persistence, and change at comparable load. Do not treat repeated copies of one slow temperature reading as new independent samples.

#### 3. Current: ACS712

The ACS712 produces an analog voltage that changes with current. The ESP32 ADC measures the voltage. At startup, the firmware averages ADC readings to estimate a zero-current offset; this calibration must occur with motor current off. It then accounts for the configured voltage divider and ACS712 sensitivity to convert ADC millivolts to an estimated current in amps.

The firmware samples the analog input at a nominal 2 kHz, accumulates squared current samples for about one second, and calculates `sqrt(mean(current²))`. It publishes this single one-second RMS value and its own timestamp. The edge API uses that scalar directly as the `current_amps` feature; it does not receive the 2 kHz waveform.

This is a coarse current/load trend. It cannot support motor-current signature analysis because the waveform and its frequency/phase detail have already been discarded. Phase imbalance needs separate phase measurements; electrical analysis also depends on sensor bandwidth, ADC quality, isolation, wiring, and calibration.

#### 4. Operating context and quality

The request schema accepts optional RPM, but the current edge feature extractor does not use it. RPM must be measured by a tachometer/encoder or read from a trusted drive interface before calculating speed-normalized orders such as `frequency / (RPM / 60)`. Similarly, a load proxy, run/stop state, drive mode, and transient state should be recorded with each window so that unlike conditions are not compared as though they were alike.

Before feature extraction, also retain quality values: expected/actual sample count, gaps and timing jitter, clipping, stale temperature/current, saturation, sensor/firmware identity, units, calibration, and source. A poor-quality window should produce a data-quality state rather than a normal/healthy motor score.

#### 5. How motor type selects features

The sensor does **not** recognize the motor type or change its reading based on that type. An accelerometer always reports acceleration; a temperature sensor reports temperature; a current sensor reports current. MotorPulse first gets the motor/drive profile from a technician or verified equipment data, then software selects feature calculations that are valid for that profile and for the sensors actually installed.

```text
technician selects motor + drive + driven equipment
  -> system checks which sensors and operating data are available
  -> profile enables only supported feature calculations
  -> sensor samples are converted into those features
  -> features are compared with this asset's baseline
  -> unsupported or missing inputs are marked unavailable, not filled with zero
```

Examples:

| Asset profile | Measurements needed | Example features the software could derive |
|---|---|---|
| Induction motor, fixed speed | Bearing vibration, actual speed, and (for electrical analysis) sufficiently fast current waveform; line frequency and motor details improve interpretation | Shared vibration RMS/peak/spectrum; running-speed orders; and, only with suitable current data, current-spectrum/slip-related indicators. |
| VFD-driven induction motor | Vibration plus actual shaft speed and VFD frequency/load/state; optional synchronized phase-current waveforms | Speed-normalized vibration orders and condition trends separated by drive regime. The commanded VFD speed alone may not equal actual shaft RPM. |
| PMSM / BLDC | Vibration plus drive/commutation context; encoder/drive RPM; phase-current data if electrical features are desired | Shared vibration and thermal features plus drive/commutation-aware current features. Do not apply induction-motor slip features as though this were the same motor/drive behavior. |
| Servo | Vibration plus actual speed and available servo-drive torque/current, following error, and alarm data | Mechanical vibration features combined with position/following-error and drive-load trends. Those drive values must be captured from the drive; the accelerometer cannot provide them. |
| Stepper | Vibration and temperature; controller commands and position feedback if available | Stall/missed-step or following-error features require position feedback or reliable controller evidence. Without it, vibration/current changes alone cannot confirm a missed step. |
| Pump or fan driven by any motor type | Motor signals plus relevant process measurements when process diagnosis is desired | Pressure/flow or airflow trends can distinguish a process/load change from a motor condition change. |

Most assets can share basic features such as vibration RMS and temperature trend, but they should not automatically share the same fault features, model, or healthy baseline. A motor type is also not enough by itself: drive type, speed/load regime, driven equipment, sensor bandwidth, and the question being monitored determine what is meaningful. For the current MotorPulse API, every motor receives the same five-feature calculation and RPM is ignored; type-specific feature selection is a future capability, not something the existing model already does.

#### 6. How the current baseline turns features into an alert

For each feature, the current API calculates the median of the known-healthy baseline windows and the median absolute deviation (MAD). For a new window, it computes an absolute robust deviation roughly as:

```text
deviation = abs(current_feature - baseline_median)
            / max(1.4826 * baseline_MAD, scale_floor)
```

It takes the largest deviation across the five features. The current thresholds are `warning` at 3 or more robust deviations and `critical` at 6 or more; the returned score is capped at 1.0. This is a deterministic statistical baseline detector, not a trained fault classifier or a calibrated probability. Its thresholds and the current shared numeric scale floor are prototype choices and need per-feature, per-regime validation before operational use.

#### 7. How baselines handle different motors

The same feature can have very different healthy values on two motors. That is expected: a baseline is a reference for **one specific asset**, not a universal “normal motor” value. MotorPulse should not compare Motor A’s raw vibration RMS with Motor B’s raw RMS, or pool their healthy readings just because both are motors.

| Asset / condition | Baseline to compare against |
|---|---|
| Motor A, induction, fixed speed and steady load | Motor A’s verified-healthy windows at that speed/load and with that sensor mounting |
| Motor B, PMSM, different speed and load | Motor B’s own verified-healthy windows; do not use Motor A’s baseline |
| Motor A after a VFD speed or load change | A separate Motor A operating-regime baseline, or a validated model that conditions expected values on measured speed/load |
| Motor A after sensor replacement, remounting, repair, or major configuration change | Mark the old baseline version and commission/relearn a new one after the asset is verified healthy |
| New/unseen speed, load, or motor configuration | Show “baseline unavailable/out of range” until enough valid healthy data is collected; do not silently select an unrelated baseline |

For a fixed-speed pilot, the simplest approach is one healthy baseline per physical motor while keeping speed/load and sensor mounting stable. For variable-speed assets, record actual RPM and load/drive state, then either:

1. collect separate healthy baselines for a few well-defined operating regimes, with enough verified data in each; or
2. later fit a condition-dependent expected-value model (for example, expected vibration as a function of RPM/load) and score the residual from that expectation.

Do not create a separate bucket for every tiny speed change; it will leave too little data in each bucket. Choose meaningful regimes with a reliability/maintenance specialist. Until there is enough coverage, constrain comparisons to known operating conditions and explicitly show when the current condition is not covered.

**Baseline commissioning procedure:**

1. Record motor/drive/load identity, sensor model/location/orientation, calibration, firmware, units, and sample rate.
2. Capture multiple healthy operating sessions across the normal conditions the pilot intends to monitor. Windows should be valid and representative; many adjacent overlapping windows from one short recording do not equal many independent operating sessions.
3. Have a technician verify healthy status from inspection/maintenance context. Exclude known faults, start/stop transients (unless separately modeled), sensor movement, clipping, stale sensors, and invalid timestamps.
4. Calculate and review feature distributions per asset/regime. Check that normal day-to-day variation is understood and choose alert thresholds using separate validation data and an acceptable alert burden.
5. Version and freeze the baseline used for live alerts. Record when, why, and by whom it is replaced; do not automatically absorb every new window into the healthy baseline, because a gradual fault could then be learned as normal.

The API’s minimum of five healthy windows is only a request-validation/code minimum, **not a recommended sample size or evidence of a reliable baseline**. There is no single correct count for all assets: the needed coverage depends on operating variability, fault risk, feature stability, and the alert performance required. Use repeated sessions and validation rather than relying on a large count of highly correlated windows.

Motor type helps decide which features and interpretations are appropriate; it does not supply the baseline values. Even two motors of the same model can have different healthy signatures because of mounting, load, installation, and sensor differences. A fleet-level model may eventually share learned patterns among compatible assets, but it should still retain asset-specific calibration and be evaluated on motors not used for training.

#### 8. Useful additional features to calculate later

Calculate these from properly sampled raw windows—not from the existing 1-second current summary or one FFT peak:

- **Per-axis vibration:** RMS, standard deviation, peak, peak-to-peak, crest factor (`peak / RMS`), kurtosis, and band-limited RMS. Store axis identity and units.
- **Spectrum:** windowed FFT/PSD with calibrated amplitudes, multiple peaks, harmonics, frequency-band energy, and sidebands. Use RPM to express peaks as running-speed orders.
- **Bearing analysis:** high-frequency resonance/envelope features only after installing a sensor and acquisition chain with sufficient bandwidth and validating the relevant band.
- **Temperature:** rise above ambient, rate of change, and persistence across time-aligned windows.
- **Electrical:** per-phase current/voltage RMS and imbalance; power/phase metrics where actually measured; line-frequency/sideband features only from sufficiently fast raw waveforms.
- **Context:** RPM, run state, load, VFD frequency/mode, start/stop/transient labels, sensor quality, and baseline/model version. These may be model inputs or conditions used to select the right baseline.

Each feature definition should specify input sensor, unit, formula, sample rate, filter, window duration, missing-data behavior, and software version. Validate that a feature changes repeatably under the condition it is intended to monitor, and verify its false-alert rate on later data before using it for maintenance decisions.

### Time-domain vibration features

- Per-axis and vector RMS, standard deviation, peak, peak-to-peak, crest factor, skewness, kurtosis, and robust quantiles.
- Impulsiveness measures such as impulse/clearance factor, used cautiously because noise and sensor mounting can inflate them.
- Band-limited RMS or energy, computed from the calibrated signal.
- Window quality: sample count, gaps, clipping/saturation, DC/gravity component, and sensor noise floor.

### Frequency and time-frequency features

- Windowed FFT/PSD peak locations and amplitudes; band energies; harmonic ratios; spectral entropy; and sideband energy where justified.
- Running-speed orders (1x, 2x, etc.) using measured RPM; order tracking or resampling when speed varies.
- Bearing-envelope/demodulation features only with enough sensor bandwidth and a validated resonance band.
- STFT/spectrogram or wavelet features for transients and changing conditions. These are more expensive and require more data than simple statistics.
- Compare frequency components against machine geometry only when bearing/gear specifications and speed are known; present them as evidence, not proof.

### Electrical, thermal, and contextual features

- Current/voltage RMS and imbalance, real/reactive power where measured, phase relationships, and line-frequency/sideband features from sufficiently fast waveforms.
- Temperature level, rise above ambient, slope, persistence, and relationship to load/speed.
- Actual RPM, commanded speed, torque/load proxy, start/stop state, direction, VFD mode/frequency, duty cycle, and process conditions.
- Cross-sensor relationships, such as a persistent vibration increase coincident with a temperature/current change, after timestamp and operating-state alignment.

Every feature must document units, calculation window, filter, sample rate, sensor, and software version. Normalize or stratify by operating regime rather than hiding speed/load variation inside a global threshold.

## 4. ML strategy: add complexity only when evidence supports it

| Stage | Method | Fit for MotorPulse | What it can claim |
|---|---|---|---|
| 0. Data quality and engineering limits | Range/quality checks, rules, persistence, operating-state gates | Do this immediately | “Data is missing/stale/out of range” or “a configured limit was crossed.” |
| 1. Asset-specific healthy baseline | Robust median/MAD or quantile limits per motor and regime; persistence/hysteresis | Current edge service is here | “This window deviates from this motor’s healthy reference.” |
| 2. Unsupervised / semi-supervised novelty | PCA/robust covariance, Isolation Forest, One-Class SVM on scaled features; evaluate an autoencoder only if data volume and edge budget justify it | Useful after collecting varied healthy operation and verified sensor quality | “This pattern is unusual relative to training data.” It still does not name a fault. |
| 3. Supervised fault classification | Start with interpretable feature models (e.g. gradient-boosted trees / random forest); consider CNNs on waveform/spectrogram when there is enough representative labeled data | Later, with technician-verified outcomes and coverage across assets/conditions | Candidate fault-class probabilities within defined classes, with an “unknown/other” path and human review. |
| 4. Degradation / RUL | Survival analysis, state-space/degradation models, or validated sequence models using censored and run-to-failure histories | Not supported by current data | Only a carefully validated, uncertainty-qualified estimate for a defined population and use case. |

### Build recommendations

- Keep a simple baseline as a transparent benchmark even if a more complex model is introduced.
- Learn by **asset and operating regime**. A hierarchy can use motor family as a prior, then adapt a motor-specific baseline; do not assume one model transfers to all motors.
- Add alarm persistence, hysteresis, cooldown, and alert aggregation so a noisy stream does not create one alert per window.
- Provide a quality/coverage state distinct from health: `healthy`, `watch`, `investigate`, `data unavailable`, `sensor quality issue`, and `not yet baselined` are more honest than a single green/red score.
- Keep anomaly score, fault class, confidence/calibration, and maintenance recommendation as separate outputs.
- Return the model/baseline version, feature schema version, operating regime, quality flags, and the strongest supporting features with every inference.
- For new assets, require a commissioning/baseline workflow; never silently borrow another motor’s baseline.
- Avoid training a deep model just because a synthetic dataset contains many rows. Synthetic rows teach the generator’s assumptions, not necessarily real motor behavior.

### Data and labeling

Create a durable event-centered schema containing:

- Asset and device IDs; motor/drive/load metadata; sensor type, serial/calibration, location/orientation, and firmware.
- UTC wall-clock plus device monotonic/sample time; sequence number; raw sample rate and units; window boundaries and data-quality flags.
- Speed/load/process state, run/stop/transient state, environment where relevant, and source (`real`, `simulated`, `public_dataset`, or `test_rig`).
- Raw signal or immutable reference to it; feature values and feature-pipeline version.
- Label, label author/time, evidence/source, confidence, maintenance event ID, inspection result, repair/action, and whether the fault was confirmed, ruled out, or unknown.

Use labels such as `unknown`, `healthy_verified`, `suspected`, `confirmed_fault`, `sensor_issue`, and `operating_change`. A maintenance work order does not automatically prove a fault class. Preserve ambiguous outcomes and avoid converting an alert into its own ground-truth label.

## 5. Data sets: useful for learning, not proof of deployment performance

| Resource | Potential use | Main caveat |
|---|---|---|
| [Case Western Reserve University Bearing Data Center](https://engineering.case.edu/bearingdatacenter) | Benchmark bearing vibration data with documented test conditions, loads/speeds, and seeded inner-race, outer-race, and rolling-element faults | A 2 hp laboratory motor and seeded faults are not representative of every installed motor, sensor mounting, process, or naturally progressing fault. |
| [MAFAULDA Machinery Fault Database](https://www02.smt.ufrj.br/~offshore/mfs/page_01.html) | Multisensor rotating-machinery experiments including normal, imbalance, misalignment, and bearing conditions; useful for feature/code experiments | Laboratory fault-simulator and acquisition conditions differ from MotorPulse hardware and customer assets. The dataset includes a DC motor; domain shift remains. |
| [MIMII dataset (Zenodo)](https://zenodo.org/records/3384388) | Acoustic anomaly experiments across pumps, fans, valves, and slide rails; useful if MotorPulse explores microphone/audio monitoring | Sound data is not accelerometer data; do not treat its labels/model performance as vibration-model evidence. Large download and license/attribution requirements apply. |

Use public sets to test parsers, feature extraction, and model prototypes. For fair evaluation, split by physical machine/run and preferably by time—not randomly by adjacent windows. Document the dataset’s sensor, machine, fault-seeding method, speed/load range, license, and train/test split. Expect to retrain/recalibrate on MotorPulse’s own sensors and site assets.

### Current MotorPulse data assets

The workspace includes an empty real-test CSV template, a 1,000-row and 50,000-row physics-inspired synthetic CSV, and a simpler synthetic CSV. The two physics-inspired files contain only window-level RMS acceleration, temperature, current, fault status/type, and notes—not raw waveforms or RPM. The 1,000-row file has an even 500/500 binary split; the 50,000-row file has 12,514 positive rows and several synthetic event types, including cooldown. Every row is explicitly marked as mathematical simulation rather than verified physical data.

These files are useful for interface/schema tests and demo simulations. They should not be used to claim field accuracy, diagnose faults, establish an asset baseline, or validate lead time. Keep their source and labels visible in the UI and API.

## 6. Evaluation: prove usefulness at the event and maintenance level

### Data / instrumentation gates

- Valid-window coverage, sample cadence and jitter, packet loss/gap rate, clock alignment, sensor uptime, calibration status, clipping/noise, and stale-sensor rate.
- Verify sensor readings against a suitable reference and confirm physical mounting before model comparisons.

### Model and alert metrics

- Event-level recall for confirmed events; precision/actionable-alert rate; false alerts per motor-month; missed events; detection lead time; alert persistence and latency.
- Precision-recall metrics and confusion matrices at a threshold selected on validation data. Report confidence intervals where event counts allow.
- Breakdown by asset, operating speed/load regime, fault type, sensor location, and source. Report “unknown / not classifiable” cases.
- Drift: changes in operating regime, sensor replacement/remounting, firmware, calibration, model version, and baseline age.
- Operational costs: alerts reviewed, technician time, time-to-inspection, planned-vs-emergency work, data outages, and alert fatigue.

Do not use overall accuracy alone, especially when faults are rare. Do not split randomly across neighboring windows from the same recording: that leaks almost identical signal into train and test. Freeze thresholds before the final test and use an untouched holdout by asset/run/time where possible.

### Recommended pilot

1. Choose two high-value, mechanically accessible assets with a maintenance owner; record nameplate, driven load, drive, normal operating states, and existing maintenance history.
2. Install sensors safely and repeatably. Verify signal quality and timestamps. Start in read-only mode; record simulated and real data separately.
3. Capture representative verified-healthy data across normal operating regimes. Build an asset/regime baseline; track transients separately.
4. Run shadow monitoring for 8–12 weeks or long enough to include representative operations. Technicians review and disposition alerts without seeing model output as “truth.”
5. Compare alerts with inspection/work-order outcomes and event timing. Tune only on training/validation periods, then test on a later holdout.
6. Decide to scale only when data quality is reliable, alert burden is acceptable, operators find alerts actionable, and site-specific cost/benefit is supported by records.

## 7. Product features that fit the real workflow

### MVP: sense, explain, review

- **Asset registry:** motor type, driven equipment, nameplate/drive details, location, sensor map, criticality, and operating regimes.
- **Connection and data health:** online/offline, last sample, valid-window percentage, sample rate, gaps, stale sensors, calibration/firmware, and source badge (`REAL` vs `SIMULATED`).
- **Condition view:** trend by operating regime, raw/derived vibration view, speed/load context, temperature/current, baseline range, and alert timeline.
- **Explainable alert:** what changed, when, versus which baseline, supporting feature(s), data quality, operating conditions, and how persistent the deviation is.
- **Human triage:** acknowledge, assign, add notes, label outcome, link inspection/work order, and mark false alarm/sensor issue/unknown.
- **Model management:** baseline creation date, data window count and provenance, feature/model version, operating range learned, threshold history, and retraining audit.
- **Maintenance planning:** technician-reviewed inspection suggestions and work-order draft. Do not present generic AI recommendations as confirmed repair instructions.
- **ROI evidence:** show assumptions and source records; separate gross exposure, recovered production opportunity, costs, and net verified benefit. Avoid live “$ saved” counters without measured evidence.

### Motor-aware features to build

These features make the asset classification useful in the application without pretending that the software can identify every motor or fault automatically.

| Priority | Feature | User experience / behavior |
|---|---|---|
| MVP | **Add motor wizard** | Enter a motor name/ID, motor family (`induction`, `PMSM/synchronous`, `BLDC`, `brushed DC`, `stepper`, `other`, `unknown`), rated details if known, drive type, driven equipment, and location. Permit unknown values; require a person to confirm the profile. |
| MVP | **Drive and operating profile** | Mark fixed/variable speed, select the VFD/servo/direct-on-line arrangement, and record expected operating modes. Show that actual RPM/load are telemetry and capture them when available. |
| MVP | **Sensor setup and compatibility check** | Record sensor model, mounting point/axis, bandwidth, calibration, and sample rate. Show `ready`, `limited`, or `not configured` with a plain-language reason, such as “RPM unavailable: only compare at stable speed.” |
| MVP | **Per-motor baseline workflow** | Capture known-healthy data, choose the operating regime, show how many usable windows exist, and save a versioned baseline tied to asset/sensor configuration. Require relearning or explicit review after a sensor/mounting/drive change. |
| MVP | **Motor-aware fleet and detail views** | Show motor family, driven equipment, drive, RPM availability, data quality, baseline state, and latest alert. Filter the fleet by type or equipment. Do not use motor type alone to assign health status. |
| MVP | **Capability-aware alerts** | Explain what the installed sensor/profile supports. Flag “anomaly” or “insufficient data”; do not show unsupported fault probabilities or RUL. Include the operating state and baseline used. |
| Next | **Nameplate capture and assisted setup** | Photograph/scan a nameplate and suggest structured values. Require human confirmation and retain the source/verification record; OCR output is not ground truth. |
| Next | **Drive telemetry integration** | Read actual RPM, drive mode, current/torque proxy, alarms, and run state using an approved interface. Keep integration read-only for the pilot. |
| Next | **Condition-specific profiles** | Offer separately validated monitoring profiles, for example low-frequency trend monitoring versus higher-bandwidth bearing diagnostics. Explain required sensor and acquisition upgrades before enabling a profile. |
| Later | **Validated model routing** | Route supported data to a model for a compatible motor/drive/use-case cohort, then use an asset-specific baseline/calibration. Display model coverage and an `unsupported/unknown` outcome when outside that coverage. |
| Later | **Fault-class suggestions** | Add only after collecting independently verified examples for the target motor/drive/sensor cohorts. Present calibrated candidate classes for technician review, never as an automatic diagnosis. |

For the first release, prioritize the add-motor wizard, profile completeness, sensor/data compatibility checks, RPM/run-state capture, and a per-motor baseline workflow. These will improve the quality of every later model more than adding a complex classifier before the measurements and labels are ready.

### Later, after validation

- Fault-specific model with “unknown/other,” calibrated probabilities, and per-class validation.
- Cross-sensor fusion, drive/VFD integration, phase-level electrical monitoring, and high-bandwidth vibration options.
- CMMS integration, notification routing, fleet-level model monitoring, signed firmware/OTA, and site-managed multi-user access.
- Remaining-life estimates only for narrowly defined assets with adequate run-to-failure/degradation data and uncertainty bounds.

### Do not include in an initial ML MVP

- AI start/stop/speed control or an AI “emergency stop.” Keep protection and safety functions in appropriately engineered, approved hardware/control systems.
- Fixed “days to failure,” guaranteed savings, or diagnosis certainty inferred from an anomaly score.
- A universal fault score or one threshold for unlike motor types, loads, speeds, and sensor placements.
- An automatic “healthy” label from the model’s own low anomaly score.

## 8. Suggested architecture and data flow

```text
Motor + driven asset
  -> calibrated sensors and drive context
  -> edge acquisition with timestamps, sequence, and quality checks
  -> authenticated local broker / store-and-forward
  -> immutable raw windows + versioned feature pipeline
  -> per-asset / per-regime baseline or model
  -> alert service with deduplication and human disposition
  -> fleet UI, maintenance workflow, and evidence-based reporting
```

Keep local inference available during internet outages where practical. Define retention and access controls before connecting a customer network. For device and broker security, plan unique device identity, authenticated and encrypted transport where supported, broker topic ACLs, network segmentation, managed secrets (never source-controlled credentials), signed/verified firmware updates, least privilege, audit logs, and tested recovery/backup. Get the site’s OT/cybersecurity and controls teams involved before deployment.

## 9. Standards, safety, and governance

- [ISO 17359:2018](https://www.iso.org/standard/71194.html) gives general guidelines for setting up machine condition-monitoring programs; ISO confirms it remains current after its 2023 review.
- [ISO 20816-3:2026](https://www.iso.org/standard/89922.html), published in October 2026, covers in-situ vibration evaluation for specified industrial machine groups and operating speeds. It is not a universal fault-diagnosis algorithm; its scope and machine-specific exclusions matter. It explicitly does not provide diagnostic evaluation of bearing/gear condition. Check the applicable current part and consult a qualified vibration practitioner before adopting acceptance/alarm limits.
- [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework) is voluntary guidance for managing AI trustworthiness risks. NIST notes the AI RMF is being revised and released a 2026 concept note for a critical-infrastructure profile; track the current publication if this project enters operational infrastructure.
- Standards are not a substitute for equipment manufacturer instructions, electrical codes, site risk assessment, or professional controls engineering. A monitoring prototype is not a safety-rated protective device.

This project should remain monitor-only. Any future actuator/control connection requires a separate hazard analysis, authorized control-system design, independent interlocks, cybersecurity review, and site approval. The existing browser control concepts are not physical controls.

## 10. MotorPulse-specific next actions

### First (instrumentation and trustworthy data)

1. Decide whether the pilot target is a low-frequency educational demo or real industrial bearing/rotor monitoring. Select sensors and acquisition hardware to that requirement.
2. Confirm current firmware cadence, accelerometer bandwidth/filter configuration, axis scale/calibration, timestamps, mounting, and temperature/current calibration on the actual device. Resolve the 20 Hz vs 100 Hz documentation mismatch.
3. Add a tachometer/encoder or trusted drive-reported actual speed and a motor run-state/load proxy. Include these in captured windows and baseline conditioning.
4. Store raw vibration windows before feature extraction; introduce a versioned feature schema and sensor-quality status. Add enough samples/window for the chosen speed and frequency range.
5. Improve broker/device security before any network beyond a controlled local demonstration. Remove source-controlled credentials and rotate them if they have ever been real.

### Then (pilot and learning)

6. Select two motors and collect verified healthy data over their actual operating regimes; preserve start/stop and load-change events as separate conditions.
7. Baseline the current robust detector against a later, separate capture. Add persistence/hysteresis and alert disposition before changing the model.
8. Use public datasets for code experiments only. Build a safe, instrumented test-rig dataset if fault-specific classification is a goal; never deliberately damage production equipment.
9. Run a read-only shadow pilot and report data quality, false alerts per motor-month, actionable rate, confirmed event recall, and technician outcomes.
10. Decide after the pilot whether the next investment should be higher-bandwidth sensing, drive telemetry, more labeled data, or model development. The bottleneck may be measurement quality—not algorithm choice.

## Sources and project materials

- ISO, [ISO 17359:2018 — Condition monitoring and diagnostics of machines: General guidelines](https://www.iso.org/standard/71194.html).
- ISO, [ISO 20816-3:2026 — Mechanical vibration measurement and evaluation](https://www.iso.org/standard/89922.html).
- NIST, [AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework) and [NIST AI 100-1](https://doi.org/10.6028/NIST.AI.100-1).
- Case Western Reserve University, [Bearing Data Center](https://engineering.case.edu/bearingdatacenter).
- Universidade Federal do Rio de Janeiro, [MAFAULDA Machinery Fault Database](https://www02.smt.ufrj.br/~offshore/mfs/page_01.html).
- Purohit et al., [MIMII dataset record and description](https://zenodo.org/records/3384388), DCASE 2019.
- MotorPulse project context: [project brief](./MOTORPULSE_PROJECT_BRIEF.md), [edge-AI implementation](./backend/ai-service/main.py), [edge-AI operating guide](./backend/ai-service/README.md), [real-data CSV template](./motorpulse_real_test_template.csv), and [synthetic datasets](./motorpulse_scientific_synthetic_1000.csv), [50,000-row synthetic set](./motorpulse_scientific_synthetic_50000.csv).

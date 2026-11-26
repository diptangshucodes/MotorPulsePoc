# MotorPulse feature engineering: a beginner-friendly guide

**Purpose:** explain how raw IoT sensor readings become useful numbers for a motor-monitoring model.  
**Audience:** developers, technicians, project owners, and anyone new to machine learning.

## The short version

A sensor does not send “motor health” or “bearing fault.” It measures something physical. Feature engineering is the set of clear, repeatable steps that turns those measurements into useful numbers.

```text
motor + sensors
  -> raw, timestamped readings
  -> check whether readings are trustworthy
  -> group readings into short time windows
  -> calculate features (simple summaries)
  -> add motor and operating context
  -> compare with that motor's healthy baseline
  -> show evidence for a person to review
```

For example, the accelerometer sends many X/Y/Z acceleration readings. Instead of asking a model to interpret a long stream immediately, software can calculate the vibration RMS, peak-to-peak range, and strongest frequency in a window. Those numbers are called **features**.

## First, keep three ideas separate

| Term | Plain-language meaning | MotorPulse example |
|---|---|---|
| Raw measurement | What a sensor actually measured | Acceleration on X/Y/Z in m/s²; a temperature reading in °C; current in A |
| Feature | A number calculated from one or more measurements | Vibration RMS in a 1.28-second window |
| Target / label | The answer used to teach or evaluate a supervised model | An independently reviewed `confirmed_fault` or `confirmed_no_fault` label |

`motor_type`, such as induction or stepper, is asset information entered or verified by a person. It is not a sensor feature and does not prove a fault. A measured change is not automatically a fault either.

## Step-by-step process

### Step 1: Decide what question the model is supposed to answer

Start with one clear question:

> “Has this particular motor changed from its own healthy behavior when it is operating under comparable conditions?”

That is **anomaly detection**. It is the right first goal for MotorPulse.

Other questions need different evidence:

- “Is it a bearing fault?” requires confirmed examples of bearing faults and other conditions that can look similar.
- “Is it healthy or faulty?” requires independently checked fault and no-fault labels.
- “How long until failure?” requires suitable degradation histories and often run-to-failure data.

Do not ask one feature or one model to answer all of these questions.

### Step 2: Describe each motor and its sensor installation

Create an asset record before collecting a baseline. Record what is known and mark unknown values as unknown.

**Motor and machine details**

- Stable `asset_id`
- Verified motor family/type and nameplate details
- Drive type: direct-on-line, VFD, servo drive, PWM controller, stepper driver, or other
- Driven equipment: pump, fan, conveyor, axis, etc.
- Rated speed and power, if verified

**Sensor and installation details**

- Sensor ID/model and measurement range
- Sensor location and orientation (for example, drive-end bearing, radial axis)
- Mounting method
- Calibration date/status
- Firmware, filter, sample rate, and units

Two motors of the same type can have different healthy measurements. A sensor moved to a different position can also change the signal. Therefore, a baseline belongs to a specific asset and sensor arrangement.

### Step 3: Capture raw readings and their timestamps

Keep the sensor readings before turning them into summaries.

| Signal | Example raw measurement | Context to keep |
|---|---|---|
| Vibration | `sample_time, accel_x, accel_y, accel_z` for each sample | Actual sample rate, units, sensor location, sequence number |
| Temperature | `measurement_time, temperature_c` | Sensor location; ambient temperature if available |
| Current | Raw current waveform if available, or a clearly identified RMS measurement | Measurement interval, sensor location, phase, calibration |
| Speed | Measured RPM readings | Tachometer/encoder or drive source; timestamp |
| Operating state | Run, start, steady, stop, drive mode | Source of state and time of change |
| Load/process | Measured torque, drive load, pressure, flow, or other proxy | What was actually measured; never guess from current without validation |

Each sensor has its own measurement rate. A temperature value measured once a second must keep that timestamp; do not make it appear to be a new temperature reading at every 100 Hz vibration sample.

For the current MotorPulse demo, the described vibration stream is nominally 100 Hz, the collector forms 128-sample windows, the DS18B20 supplies slower casing temperature, and the ESP32 sends one-second RMS current. The actual capture cadence must be checked on the device; a configured rate is not proof that samples arrived at that rate.

### Step 4: Check the readings before using them

Before calculating features, check:

- Are timestamps present and in order?
- Did the expected number of vibration samples arrive?
- Are there large gaps or timing irregularities?
- Are values within the sensor range, or is the sensor saturated/clipped?
- Are temperature and current readings recent enough for this window?
- Is calibration known and does the sensor appear connected?
- Was the motor running steadily, starting, stopping, or changing speed/load?

If the data is missing or unreliable, mark the window as `insufficient` or `sensor_issue`. **Do not replace missing readings with zero**: zero may be a real measurement, and the model could learn the wrong thing.

### Step 5: Split the stream into windows

A **window** is a short block of consecutive samples analyzed together. For example, 128 samples at an actual uniform 100 samples/second represent:

```text
window duration = sample count / sample rate
                = 128 / 100
                = 1.28 seconds
```

Use the same window definition for baseline and later analysis. Keep the start/end timestamps, sample count, sample rate, and windowing configuration with every feature row.

Window length is a design choice:

- Very short windows react quickly but can give unstable statistics and coarse frequency information.
- Longer windows provide more samples and finer frequency spacing, but average over a longer time and can hide short events.
- The appropriate choice depends on speed, target condition, sensor bandwidth, and sample rate.

At 100 Hz, the theoretical highest representable frequency is 50 Hz (the Nyquist limit). The current MPU6050 configuration also uses a 44 Hz filter. These settings support a limited low-frequency demonstration, not high-frequency bearing analysis.

### Step 6: Prepare vibration samples consistently

An accelerometer can measure gravity as well as vibration. When the sensor is stationary, gravity can appear as an offset on one or more axes. For vibration features, the current MotorPulse service subtracts the average value of each axis within the window:

```text
centered_x[n] = x[n] - mean(x)
centered_y[n] = y[n] - mean(y)
centered_z[n] = z[n] - mean(z)
```

This removes a steady offset for these calculations. It also removes a true constant component, so preserve raw samples and document the preprocessing. Use the same calibration, filters, and preprocessing during baseline and live analysis.

Do not add filters just because they sound useful. A filter changes the signal; choose and document it for the target frequency range. Filtering cannot recover frequencies the sensor never captured.

### Step 7: Calculate basic vibration features

These features summarize different parts of the vibration signal. They are measurements of signal behavior—not fault names.

#### A. RMS: overall vibration level

RMS is similar to an average vibration strength while giving larger movements more influence.

For one axis with `N` centered samples:

```text
axis_rms = square_root( (x[1]^2 + x[2]^2 + ... + x[N]^2) / N )
```

For three synchronized axes:

```text
vector_rms = square_root( mean(x[n]^2 + y[n]^2 + z[n]^2) )
```

Example: if the three per-axis RMS values are 0.20, 0.10, and 0.30 m/s², the vector RMS is:

```text
sqrt(0.20^2 + 0.10^2 + 0.30^2) = sqrt(0.14) ≈ 0.374 m/s²
```

Higher RMS means more measured vibration in that window. It does not say why.

#### B. Peak-to-peak: largest swing

For each axis:

```text
peak_to_peak = largest sample - smallest sample
```

MotorPulse’s current API calculates the peak-to-peak range for X, Y, and Z, then returns the largest of the three. A single shock or bad sample can make this value large, so quality checks matter.

#### C. Peak and crest factor: unusually large movements

The absolute peak is the largest absolute centered sample. Crest factor compares that peak with the axis RMS:

```text
crest_factor = largest_absolute_sample / axis_rms
```

A higher value can indicate sharp peaks compared with the average level. It can also result from noise, a loose sensor, or a transient; it is not a diagnosis.

#### D. Frequency: how quickly a vibration repeats

The FFT (Fast Fourier Transform) is a calculation that summarizes repeating frequencies in a window. The current service returns only the frequency bin with the largest magnitude, called the **dominant frequency**.

With `N` uniform samples at `sample_rate_hz`:

```text
frequency spacing = sample_rate_hz / N
highest theoretical frequency = sample_rate_hz / 2
```

At 100 Hz and 128 samples, the frequency-bin spacing is about 0.78 Hz. The current implementation’s single strongest bin does not identify a fault. A useful spectrum may require windowing, calibrated amplitudes, multiple peaks/bands, suitable sensor bandwidth, and measured RPM.

### Step 8: Turn slower sensor readings into features

#### Temperature

The current service uses the temperature reading for a window directly. A surface-mounted DS18B20 measures the temperature at its location, not the motor winding temperature.

Useful features across multiple time-aligned windows can include:

```text
temperature rise = casing temperature - ambient temperature
temperature slope = change in temperature / elapsed time
```

Temperature changes slowly. Keep its true measurement timestamp and compare readings under similar load and airflow conditions.

#### Current

If raw current samples exist, RMS current is:

```text
current_rms = square_root( mean(current_sample^2) )
```

MotorPulse’s current ESP32 sends a one-second RMS value, so the edge service uses it as a scalar. It does not receive the original current waveform. That summary can provide coarse load/current context, but detailed electrical frequency analysis requires suitable raw, sufficiently fast current measurements and safe, properly rated instrumentation.

### Which sensor readings are needed for each dataset column?

The accelerometer provides raw acceleration samples. Software calculates the vibration summary columns from those samples. Temperature and current sensors provide their own measurements; some temperature/current features need extra sensors or a calculation. The motor type does not change these formulas, but the sensor bandwidth, mounting, sample rate, speed, and load determine whether the values are useful.

| Feature column | Sensor input needed | How the value is obtained | Current MotorPulse API |
|---|---|---|---|
| `accel_x_rms_m_s2` | Raw X-axis acceleration samples | Software calculates X-axis RMS over a window. | Not returned separately. |
| `accel_y_rms_m_s2` | Raw Y-axis acceleration samples | Software calculates Y-axis RMS over a window. | Not returned separately. |
| `accel_z_rms_m_s2` | Raw Z-axis acceleration samples | Software calculates Z-axis RMS over a window. | Not returned separately. |
| `accel_vector_rms_m_s2` | Synchronized raw X/Y/Z acceleration samples | Software removes each axis's window mean, combines squared axes per sample, averages, then takes the square root. | Yes. |
| `accel_peak_to_peak_max_m_s2` | Raw X/Y/Z acceleration samples | Software finds max-minus-min for each axis and returns the largest range. | Yes, named `acceleration_peak_to_peak_m_s2`. |
| `accel_crest_factor_max` | Raw X/Y/Z acceleration samples | Software calculates absolute peak divided by RMS for each axis and returns the largest. | No. |
| `dominant_frequency_hz` | Time-ordered vibration samples plus measured sample rate | Software calculates an FFT and selects the strongest non-zero frequency bin. | Yes. |
| `temperature_c` | Temperature sensor reading, such as the DS18B20 casing reading | Read from the sensor in °C with its own timestamp; it is not calculated from acceleration. | Yes; passed into analysis as a scalar. |
| `temperature_rise_c` | Motor-surface temperature **and** ambient-temperature sensor | Software subtracts aligned ambient temperature from casing temperature. | No; ambient temperature is not currently included. |
| `current_rms_a` | Raw current samples, or an RMS value computed by the sensor/device | Calculate `sqrt(mean(current_sample²))` if raw samples are available. | Yes; the ESP32 sends a one-second RMS scalar, which the API uses directly. |

These are not all values a sensor reports directly. In particular, the four vibration-summary types are calculated from raw accelerometer samples. For real data, keep the raw samples so the feature calculations can be reproduced and checked. The current 100 Hz / 44 Hz-filter demo has limited frequency coverage; choosing a feature name does not make the hardware capable of measuring every fault-related frequency.

### Step 9: Attach operating context; do not confuse it with calculated features

The feature row should carry context that helps interpret its measurements:

- `motor_type`, `drive_type`, `driven_equipment`: verified asset metadata
- `actual_rpm`: measured by tachometer/encoder or trusted drive feedback
- `load_pct`: measured load or documented proxy
- `run_state`: stopped, starting, steady, stopping, etc.
- `sensor_profile`, `sensor_mount_location`: installation metadata
- `quality_status`: collector’s data-quality decision

These values may help choose the right baseline or model. They do not all come from the accelerometer. In particular, actual RPM cannot be calculated reliably from a single vibration RMS value.

### Step 10: Save one feature row per window

Keep a link from every feature row back to its raw samples. Store:

- Asset/session/window IDs and timestamps
- Motor, drive, sensor, and operating context
- Feature values, units, and feature-pipeline version
- Data-quality status and missing-value reasons
- Data source: real, test rig, public, or synthetic
- Label, reviewer, and evidence reference where available

The [mixed-motor CSV](./motorpulse_mixed_motor_synthetic_v1.csv) is a feature-level table. It contains no raw accelerometer waveform. Its numbers were generated directly by a script, so they cannot be recalculated from raw sensor samples.

### Step 11: Create labels from independent evidence

For an actual binary fault classifier, an inspection or maintenance outcome—not the model—must establish the label:

| `fault_status` | Meaning | Use in supervised training? |
|---|---|---|
| `confirmed_fault` | A qualified inspection/diagnosis found a fault and linked it to the relevant asset/time period. Record `fault_type_confirmed` when known. | Yes, for the matching verified period/class. |
| `confirmed_no_fault` | Inspection reviewed the relevant period and found no fault. | Yes, if the inspection scope and time match the data. |
| `unknown` | No inspection, unclear result, or uncertain time alignment. | No; retain it for review, but do not pretend it is a negative example. |
| `sensor_issue` | The measurement system was faulty or data was unusable. | Use for a separate sensor-quality task, not as a motor fault. |
| `operating_change` | Speed, load, or process changed. | Treat as context/event, not automatically a motor fault. |

No alert does not prove `confirmed_no_fault`; a sensor deviation does not prove `confirmed_fault`. Preserve the evidence source, reviewer, inspection date, and maintenance event ID.

The synthetic file has `scenario_label` values such as `synthetic_vibration_deviation`. This target teaches only the synthetic generator’s scenarios. `fault_status` and `fault_type_confirmed` are `not_assessed_synthetic` in every row.

### Step 12: Build a baseline for each motor

For the first MotorPulse version:

1. Capture multiple sessions where a technician has verified that the motor is healthy.
2. Keep the sensor mounting consistent and record speed/load/run state.
3. Use only valid windows and separate meaningfully different operating regimes.
4. Calculate the same features with the same code and settings on every window.
5. Summarize this motor’s healthy feature values and variation. The current service uses median and median absolute deviation (MAD).
6. Freeze/version the baseline. Do not automatically add every new reading to it; a slowly developing issue could otherwise become the new “normal.”
7. Test on a later capture from the same motor and compare alerts with technician review.

Do not compare one motor’s raw vibration threshold directly with another motor’s. Motor type helps choose supported analysis; each physical motor still needs its own healthy reference. For variable-speed equipment, compare within measured RPM/load ranges or use a separately validated model that accounts for those conditions.

### Step 13: Select model inputs and evaluate fairly

For a model, `X` means the input columns (calculated features and any carefully chosen context). `y` means the target label. Never include the target or post-inspection answer inside `X`.

For MotorPulse’s current detector, the computed feature inputs are:

- `acceleration_vector_rms_m_s2`
- `acceleration_peak_to_peak_m_s2`
- `dominant_frequency_hz`
- `temperature_c`
- `current_amps`

The API accepts optional `rpm` but currently does not use it. It also does not currently use motor type, drive type, or load to select feature calculations.

When testing a future model:

- Split by complete asset and/or later acquisition session, not randomly by adjacent windows.
- Report results per motor family and operating regime.
- Measure false alerts per motor-day/month and technician actionability, not just row-level accuracy.
- If real confirmed faults are absent, report only data-quality or anomaly experiments. Do not claim real fault-classification performance.

## What the current synthetic dataset can teach

Use it to practice:

- Loading a feature table and checking column types/null values
- Selecting `scenario_label` as a **synthetic scenario** target
- Excluding IDs, timestamps, `fault_status`, and `fault_type_confirmed` from model inputs
- Grouping train/test splits by `split_group_asset_id`
- Showing that the model output is limited to the training labels

Do not use it to create real baselines, prove fault/non-fault performance, or make maintenance decisions.

## Current MotorPulse implementation vs. future work

| Capability | Current prototype | Future feature-engineering work |
|---|---|---|
| Vibration input | Three-axis acceleration samples in m/s² | Add raw-data retention, measured cadence/quality checks, and validated sensor profiles |
| Window | API accepts 16–8,192 samples; MQTT collector currently creates 128-sample windows | Select window lengths by monitoring objective and sensor bandwidth |
| Vibration features | Vector RMS, maximum axis peak-to-peak, dominant FFT bin | Per-axis RMS/peak/crest factor, calibrated spectrum/bands, speed orders, and other features only where acquisition supports them |
| Temperature/current | One temperature scalar and one current scalar per API window | Time-aligned trends, ambient correction, and raw electrical analysis only with appropriate measurement hardware |
| Motor context | Motor ID; optional RPM accepted but ignored | Verified motor/drive profile, actual RPM, load/run state, and condition-specific baselines |
| Model result | Per-motor robust-baseline deviation flag | Independently validated fault classification only after verified real labels |

## Plain-language glossary

- **Sample:** one reading from a sensor.
- **Window:** a group of nearby samples analyzed together.
- **Feature:** a number summarizing a window.
- **Baseline:** a verified reference describing one motor’s normal features under specified conditions.
- **Anomaly:** a measurement outside the expected baseline; not necessarily a fault.
- **Label/target:** an answer used to train or evaluate a supervised model.
- **Feature schema/version:** the documented names, units, and formulas used to calculate features.
- **Out of coverage:** a motor or operating condition the system has not learned or validated.

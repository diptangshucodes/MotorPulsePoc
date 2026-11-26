import csv
import math
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).parent
OUTPUT = ROOT / "motorpulse_mixed_motor_synthetic_v1.csv"
TEMPLATE = ROOT / "motorpulse_mixed_motor_real_capture_template.csv"
RANDOM_SEED = 2601126
WINDOWS_PER_SCENARIO = 20

SCENARIOS = (
    "synthetic_healthy",
    "synthetic_vibration_deviation",
    "synthetic_thermal_deviation",
    "synthetic_current_deviation",
    "synthetic_operating_change",
    "synthetic_sensor_quality_issue",
)

ASSETS = (
    {
        "motor_type": "induction",
        "drive_type": "vfd",
        "driven_equipment": "pump",
        "rated_power_kw": 1.5,
        "supply_phase_count": 3,
        "rated_voltage_v": 400,
        "rated_speed_rpm": 1475,
        "nominal_rpm": 1450,
        "nominal_current_a": 3.2,
        "base_vibration": (0.10, 0.13, 0.17),
        "base_temperature_rise_c": 13.0,
        "load_pct": 55,
    },
    {
        "motor_type": "induction",
        "drive_type": "direct_on_line",
        "driven_equipment": "fan",
        "rated_power_kw": 2.2,
        "supply_phase_count": 3,
        "rated_voltage_v": 400,
        "rated_speed_rpm": 1475,
        "nominal_rpm": 1470,
        "nominal_current_a": 4.7,
        "base_vibration": (0.15, 0.12, 0.20),
        "base_temperature_rise_c": 17.0,
        "load_pct": 70,
    },
    {
        "motor_type": "induction",
        "drive_type": "vfd",
        "driven_equipment": "conveyor",
        "rated_power_kw": 0.75,
        "supply_phase_count": 3,
        "rated_voltage_v": 400,
        "rated_speed_rpm": 1475,
        "nominal_rpm": 1100,
        "nominal_current_a": 1.8,
        "base_vibration": (0.12, 0.10, 0.16),
        "base_temperature_rise_c": 11.0,
        "load_pct": 45,
    },
    {
        "motor_type": "pmsm",
        "drive_type": "servo_drive",
        "driven_equipment": "machine_axis",
        "rated_power_kw": 1.0,
        "supply_phase_count": 3,
        "rated_voltage_v": 230,
        "rated_speed_rpm": 3000,
        "nominal_rpm": 1800,
        "nominal_current_a": 3.5,
        "base_vibration": (0.08, 0.10, 0.12),
        "base_temperature_rise_c": 10.0,
        "load_pct": 40,
    },
    {
        "motor_type": "pmsm",
        "drive_type": "servo_drive",
        "driven_equipment": "robot_joint",
        "rated_power_kw": 2.0,
        "supply_phase_count": 3,
        "rated_voltage_v": 400,
        "rated_speed_rpm": 3000,
        "nominal_rpm": 2400,
        "nominal_current_a": 5.2,
        "base_vibration": (0.11, 0.09, 0.14),
        "base_temperature_rise_c": 14.0,
        "load_pct": 60,
    },
    {
        "motor_type": "pmsm",
        "drive_type": "vfd",
        "driven_equipment": "compressor",
        "rated_power_kw": 3.0,
        "supply_phase_count": 3,
        "rated_voltage_v": 400,
        "rated_speed_rpm": 3000,
        "nominal_rpm": 2700,
        "nominal_current_a": 7.0,
        "base_vibration": (0.14, 0.12, 0.18),
        "base_temperature_rise_c": 16.0,
        "load_pct": 75,
    },
    {
        "motor_type": "bldc",
        "drive_type": "electronic_commutator",
        "driven_equipment": "fan",
        "rated_power_kw": 0.4,
        "supply_phase_count": 3,
        "rated_voltage_v": 48,
        "rated_speed_rpm": 3000,
        "nominal_rpm": 2400,
        "nominal_current_a": 8.0,
        "base_vibration": (0.07, 0.08, 0.10),
        "base_temperature_rise_c": 9.0,
        "load_pct": 50,
    },
    {
        "motor_type": "bldc",
        "drive_type": "electronic_commutator",
        "driven_equipment": "pump",
        "rated_power_kw": 0.6,
        "supply_phase_count": 3,
        "rated_voltage_v": 48,
        "rated_speed_rpm": 4000,
        "nominal_rpm": 3200,
        "nominal_current_a": 12.0,
        "base_vibration": (0.09, 0.07, 0.11),
        "base_temperature_rise_c": 12.0,
        "load_pct": 65,
    },
    {
        "motor_type": "bldc",
        "drive_type": "electronic_commutator",
        "driven_equipment": "conveyor",
        "rated_power_kw": 0.25,
        "supply_phase_count": 3,
        "rated_voltage_v": 24,
        "rated_speed_rpm": 2500,
        "nominal_rpm": 1900,
        "nominal_current_a": 10.0,
        "base_vibration": (0.06, 0.08, 0.09),
        "base_temperature_rise_c": 8.0,
        "load_pct": 35,
    },
    {
        "motor_type": "brushed_dc",
        "drive_type": "pwm_controller",
        "driven_equipment": "conveyor",
        "rated_power_kw": 0.3,
        "supply_phase_count": 1,
        "rated_voltage_v": 24,
        "rated_speed_rpm": 1800,
        "nominal_rpm": 1400,
        "nominal_current_a": 7.0,
        "base_vibration": (0.12, 0.10, 0.15),
        "base_temperature_rise_c": 15.0,
        "load_pct": 50,
    },
    {
        "motor_type": "brushed_dc",
        "drive_type": "pwm_controller",
        "driven_equipment": "pump",
        "rated_power_kw": 0.5,
        "supply_phase_count": 1,
        "rated_voltage_v": 24,
        "rated_speed_rpm": 2400,
        "nominal_rpm": 2000,
        "nominal_current_a": 11.0,
        "base_vibration": (0.15, 0.13, 0.17),
        "base_temperature_rise_c": 18.0,
        "load_pct": 65,
    },
    {
        "motor_type": "brushed_dc",
        "drive_type": "pwm_controller",
        "driven_equipment": "fan",
        "rated_power_kw": 0.2,
        "supply_phase_count": 1,
        "rated_voltage_v": 12,
        "rated_speed_rpm": 1500,
        "nominal_rpm": 1100,
        "nominal_current_a": 5.0,
        "base_vibration": (0.09, 0.11, 0.12),
        "base_temperature_rise_c": 9.0,
        "load_pct": 40,
    },
    {
        "motor_type": "stepper",
        "drive_type": "stepper_driver",
        "driven_equipment": "indexer",
        "rated_power_kw": 0.15,
        "supply_phase_count": 2,
        "rated_voltage_v": 24,
        "rated_speed_rpm": 600,
        "nominal_rpm": 300,
        "nominal_current_a": 2.0,
        "base_vibration": (0.15, 0.17, 0.20),
        "base_temperature_rise_c": 20.0,
        "load_pct": 35,
    },
    {
        "motor_type": "stepper",
        "drive_type": "stepper_driver",
        "driven_equipment": "positioning_axis",
        "rated_power_kw": 0.2,
        "supply_phase_count": 2,
        "rated_voltage_v": 24,
        "rated_speed_rpm": 900,
        "nominal_rpm": 450,
        "nominal_current_a": 2.5,
        "base_vibration": (0.18, 0.15, 0.21),
        "base_temperature_rise_c": 23.0,
        "load_pct": 45,
    },
    {
        "motor_type": "stepper",
        "drive_type": "stepper_driver",
        "driven_equipment": "feeder",
        "rated_power_kw": 0.1,
        "supply_phase_count": 2,
        "rated_voltage_v": 12,
        "rated_speed_rpm": 500,
        "nominal_rpm": 250,
        "nominal_current_a": 1.5,
        "base_vibration": (0.13, 0.16, 0.18),
        "base_temperature_rise_c": 17.0,
        "load_pct": 30,
    },
)

FIELDS = (
    "window_id",
    "session_id",
    "recorded_at_utc",
    "data_source",
    "asset_id",
    "motor_type",
    "drive_type",
    "driven_equipment",
    "rated_power_kw",
    "supply_phase_count",
    "rated_voltage_v",
    "rated_speed_rpm",
    "sensor_profile",
    "sensor_mount_location",
    "sample_rate_hz",
    "window_duration_s",
    "actual_rpm",
    "load_pct",
    "run_state",
    "accel_x_rms_m_s2",
    "accel_y_rms_m_s2",
    "accel_z_rms_m_s2",
    "accel_x_peak_abs_m_s2",
    "accel_y_peak_abs_m_s2",
    "accel_z_peak_abs_m_s2",
    "accel_vector_rms_m_s2",
    "accel_peak_to_peak_max_m_s2",
    "accel_crest_factor_max",
    "dominant_frequency_hz",
    "temperature_c",
    "ambient_temperature_c",
    "temperature_rise_c",
    "current_rms_a",
    "quality_status",
    "scenario_label",
    "fault_status",
    "fault_type_confirmed",
    "label_source",
    "split_group_asset_id",
)


def rounded(value: float, places: int = 4) -> float:
    return round(value, places)


def create_record(
    rng: random.Random,
    asset: dict[str, object],
    asset_index: int,
    scenario: str,
    sample_index: int,
    recorded_at: datetime,
) -> dict[str, object]:
    asset_id = f"{asset['motor_type'].upper()}-{asset_index:02d}"
    session_id = f"SIM-{asset_id}-{scenario.upper()}"
    nominal_load = float(asset["load_pct"])
    load_pct = nominal_load + rng.gauss(0, 3)
    actual_rpm = float(asset["nominal_rpm"]) * (1 + rng.gauss(0, 0.003))

    if scenario == "synthetic_operating_change":
        load_pct = min(95, nominal_load + 22 + rng.gauss(0, 3))
        if asset["drive_type"] == "direct_on_line":
            actual_rpm *= 0.995
        else:
            actual_rpm *= 0.88

    load_fraction = max(0.1, min(load_pct, 100) / 100)
    current_factor = 0.25 + 0.75 * load_fraction
    current = float(asset["nominal_current_a"]) * current_factor * (1 + rng.gauss(0, 0.025))
    vibration_scale = 1.0 + 0.25 * load_fraction
    axes = [float(value) * vibration_scale * (1 + rng.gauss(0, 0.06)) for value in asset["base_vibration"]]
    temperature_rise = float(asset["base_temperature_rise_c"]) * load_fraction + rng.gauss(0, 0.7)
    ambient = 22.0 + rng.gauss(0, 1.0)

    if scenario == "synthetic_vibration_deviation":
        axes = [value * rng.uniform(1.8, 2.8) for value in axes]
    elif scenario == "synthetic_thermal_deviation":
        temperature_rise += rng.uniform(12, 20)
    elif scenario == "synthetic_current_deviation":
        current *= rng.uniform(1.5, 2.0)

    peaks = [value * rng.uniform(1.6, 2.5) for value in axes]
    vector_rms = math.sqrt(sum(value * value for value in axes))
    peak_to_peak = max(2 * value for value in peaks)
    crest_factor = max(peak / axis_rms for peak, axis_rms in zip(peaks, axes))
    dominant_frequency = (actual_rpm / 60) * rng.uniform(0.9, 1.1)
    temperature = ambient + temperature_rise
    quality_status = "valid"

    if scenario == "synthetic_sensor_quality_issue":
        quality_status = "synthetic_invalid_sensor_data"
        axes = [None, None, None]
        peaks = [None, None, None]
        vector_rms = None
        peak_to_peak = None
        crest_factor = None
        dominant_frequency = None
        temperature = None
        temperature_rise = None
        current = None

    return {
        "window_id": f"SIM-{asset_index:02d}-{SCENARIOS.index(scenario) + 1:02d}-{sample_index:03d}",
        "session_id": session_id,
        "recorded_at_utc": recorded_at.isoformat().replace("+00:00", "Z"),
        "data_source": "synthetic_generator_v1",
        "asset_id": asset_id,
        "motor_type": asset["motor_type"],
        "drive_type": asset["drive_type"],
        "driven_equipment": asset["driven_equipment"],
        "rated_power_kw": asset["rated_power_kw"],
        "supply_phase_count": asset["supply_phase_count"],
        "rated_voltage_v": asset["rated_voltage_v"],
        "rated_speed_rpm": asset["rated_speed_rpm"],
        "sensor_profile": "illustrative_triaxial_100hz_temperature_current",
        "sensor_mount_location": "drive_end_bearing_simulated",
        "sample_rate_hz": 100,
        "window_duration_s": 1.28,
        "actual_rpm": rounded(actual_rpm, 1),
        "load_pct": rounded(load_pct, 1),
        "run_state": "steady",
        "accel_x_rms_m_s2": "" if axes[0] is None else rounded(axes[0]),
        "accel_y_rms_m_s2": "" if axes[1] is None else rounded(axes[1]),
        "accel_z_rms_m_s2": "" if axes[2] is None else rounded(axes[2]),
        "accel_x_peak_abs_m_s2": "" if peaks[0] is None else rounded(peaks[0]),
        "accel_y_peak_abs_m_s2": "" if peaks[1] is None else rounded(peaks[1]),
        "accel_z_peak_abs_m_s2": "" if peaks[2] is None else rounded(peaks[2]),
        "accel_vector_rms_m_s2": "" if vector_rms is None else rounded(vector_rms),
        "accel_peak_to_peak_max_m_s2": "" if peak_to_peak is None else rounded(peak_to_peak),
        "accel_crest_factor_max": "" if crest_factor is None else rounded(crest_factor),
        "dominant_frequency_hz": "" if dominant_frequency is None else rounded(dominant_frequency, 3),
        "temperature_c": "" if temperature is None else rounded(temperature, 2),
        "ambient_temperature_c": "" if temperature is None else rounded(ambient, 2),
        "temperature_rise_c": "" if temperature_rise is None else rounded(temperature_rise, 2),
        "current_rms_a": "" if current is None else rounded(current, 3),
        "quality_status": quality_status,
        "scenario_label": scenario,
        "fault_status": "not_assessed_synthetic",
        "fault_type_confirmed": "not_assessed_synthetic",
        "label_source": "synthetic_generator_rule",
        "split_group_asset_id": asset_id,
    }


def main() -> None:
    rng = random.Random(RANDOM_SEED)
    rows = []
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    counter = 0
    for asset_index, asset in enumerate(ASSETS, start=1):
        for scenario in SCENARIOS:
            for sample_index in range(1, WINDOWS_PER_SCENARIO + 1):
                timestamp = start + timedelta(seconds=counter * 1.28)
                rows.append(
                    create_record(
                        rng,
                        asset,
                        asset_index,
                        scenario,
                        sample_index,
                        timestamp,
                    )
                )
                counter += 1

    with OUTPUT.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    with TEMPLATE.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()

    print(f"Wrote {len(rows)} synthetic windows to {OUTPUT}")
    print(f"Wrote real-data capture header to {TEMPLATE}")


if __name__ == "__main__":
    main()

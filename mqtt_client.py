import json
import math
import os
import re
import sqlite3
from collections import deque
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from typing import Optional
from urllib.parse import parse_qs, urlsplit

import paho.mqtt.client as mqtt

MQTT_HOST = os.environ.get("MQTT_HOST", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
API_HOST = os.environ.get("TELEMETRY_API_HOST", "127.0.0.1")
API_PORT = int(os.environ.get("TELEMETRY_API_PORT", "8002"))
MQTT_TOPIC = "esp32/switch"
DATA_SOURCE = os.environ.get("MQTT_DATA_SOURCE", "simulated").strip().lower()
DATABASE_PATH = Path(
    os.environ.get("MQTT_DATABASE_PATH", Path(__file__).resolve().parent / "telemetry.sqlite3")
).expanduser()

_MOTOR_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_MAX_SAMPLES_PER_WINDOW = 8192
_MAX_RAW_READINGS = 1200
_RAW_READING_RETENTION_LIMIT = 12_000
_AI_WINDOW_SAMPLE_COUNT = 128
_AI_WINDOW_RETENTION_LIMIT = 5_000
_ACCELERATION_SCALE = 0.001
_LABELS = {"healthy", "unknown", "suspected_fault", "confirmed_fault"}


@dataclass(frozen=True)
class TelemetryWindow:
    schema_version: int
    motor_id: str
    sample_rate_hz: float
    sample_count: int
    window_start_ms: int
    payload_json: str


@dataclass(frozen=True)
class TelemetryReading:
    motor_id: str
    sample_rate_hz: float
    sample_time_ms: int
    accel_x_milli_ms2: int
    accel_y_milli_ms2: int
    accel_z_milli_ms2: int
    temperature_c: Optional[float]
    temperature_sample_time_ms: Optional[int]
    current_amps: Optional[float]
    current_sample_time_ms: Optional[int]
    current_sample_count: Optional[int]
    payload_json: str


@dataclass(frozen=True)
class AccelerationFeatures:
    accel_x_mean_ms2: float
    accel_y_mean_ms2: float
    accel_z_mean_ms2: float
    accel_x_rms_ms2: float
    accel_y_rms_ms2: float
    accel_z_rms_ms2: float
    accel_x_peak_to_peak_ms2: float
    accel_y_peak_to_peak_ms2: float
    accel_z_peak_to_peak_ms2: float
    accel_vector_rms_ms2: float


_FEATURE_COLUMNS = tuple(AccelerationFeatures.__dataclass_fields__)
_DATA_SOURCES = {"simulated", "real"}
_raw_readings_since_cleanup = 0
_sensor_windows_since_cleanup = 0
_mqtt_connected = False
_window_buffers: dict[str, deque[TelemetryReading]] = {}


def parse_reading(payload: bytes) -> TelemetryReading:
    try:
        payload_json = payload.decode("utf-8")
        data = json.loads(payload_json)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"payload is not valid UTF-8 JSON: {error}") from error

    if not isinstance(data, dict):
        raise ValueError("payload must be a JSON object")
    if data.get("message_type") != "acceleration":
        raise ValueError('message_type must be "acceleration"')
    if type(data.get("schema_version")) is not int or data["schema_version"] != 2:
        raise ValueError("schema_version must be 2 for raw acceleration readings")

    motor_id = data.get("motor_id")
    if not isinstance(motor_id, str) or not _MOTOR_ID_PATTERN.fullmatch(motor_id):
        raise ValueError("motor_id must contain 1-64 letters, numbers, underscores, or hyphens")

    sample_rate_hz = data.get("sample_rate_hz")
    if (
        isinstance(sample_rate_hz, bool)
        or not isinstance(sample_rate_hz, (int, float))
        or not math.isfinite(sample_rate_hz)
        or sample_rate_hz <= 0
    ):
        raise ValueError("sample_rate_hz must be a positive finite number")

    sample_time_ms = data.get("sample_time_ms")
    if type(sample_time_ms) is not int or sample_time_ms < 0:
        raise ValueError("sample_time_ms must be a non-negative integer")
    if data.get("acceleration_unit") != "m/s^2":
        raise ValueError('acceleration_unit must be "m/s^2"')
    if (
        isinstance(data.get("acceleration_scale"), bool)
        or not isinstance(data.get("acceleration_scale"), (int, float))
        or data["acceleration_scale"] != _ACCELERATION_SCALE
    ):
        raise ValueError(f"acceleration_scale must be {_ACCELERATION_SCALE}")

    axes = ("accel_x_milli_ms2", "accel_y_milli_ms2", "accel_z_milli_ms2")
    if any(type(data.get(axis)) is not int for axis in axes):
        raise ValueError("acceleration axis values must be integers in milli-m/s^2")

    temperature_fields = ("temperature_c", "temperature_sample_time_ms")
    temperature_present = [field in data for field in temperature_fields]
    if any(temperature_present) and not all(temperature_present):
        raise ValueError("temperature_c and temperature_sample_time_ms must be provided together")
    temperature_c = None
    temperature_sample_time_ms = None
    if all(temperature_present):
        raw_temperature = data["temperature_c"]
        temperature_sample_time_ms = data["temperature_sample_time_ms"]
        if (
            isinstance(raw_temperature, bool)
            or not isinstance(raw_temperature, (int, float))
            or not math.isfinite(raw_temperature)
            or not -55 <= raw_temperature <= 125
        ):
            raise ValueError("temperature_c must be a finite DS18B20 temperature from -55 to 125 C")
        if type(temperature_sample_time_ms) is not int or temperature_sample_time_ms < 0:
            raise ValueError("temperature_sample_time_ms must be a non-negative integer")
        if temperature_sample_time_ms > sample_time_ms:
            raise ValueError("temperature_sample_time_ms cannot be later than sample_time_ms")
        temperature_c = float(raw_temperature)

    current_fields = (
        "current_amps",
        "current_unit",
        "current_measurement",
        "current_sample_time_ms",
        "current_sample_count",
    )
    current_present = [field in data for field in current_fields]
    if any(current_present) and not all(current_present):
        raise ValueError("all current measurement fields must be provided together")
    current_amps = None
    current_sample_time_ms = None
    current_sample_count = None
    if all(current_present):
        raw_current = data["current_amps"]
        current_sample_time_ms = data["current_sample_time_ms"]
        current_sample_count = data["current_sample_count"]
        if (
            isinstance(raw_current, bool)
            or not isinstance(raw_current, (int, float))
            or not math.isfinite(raw_current)
            or raw_current < 0
        ):
            raise ValueError("current_amps must be a non-negative finite RMS current")
        if data["current_unit"] != "A" or data["current_measurement"] != "rms_1s":
            raise ValueError('current must use unit "A" and measurement "rms_1s"')
        if type(current_sample_time_ms) is not int or current_sample_time_ms < 0:
            raise ValueError("current_sample_time_ms must be a non-negative integer")
        if current_sample_time_ms > sample_time_ms:
            raise ValueError("current_sample_time_ms cannot be later than sample_time_ms")
        if type(current_sample_count) is not int or current_sample_count < 500:
            raise ValueError("current_sample_count must be an integer of at least 500")
        current_amps = float(raw_current)

    return TelemetryReading(
        motor_id=motor_id,
        sample_rate_hz=float(sample_rate_hz),
        sample_time_ms=sample_time_ms,
        accel_x_milli_ms2=data[axes[0]],
        accel_y_milli_ms2=data[axes[1]],
        accel_z_milli_ms2=data[axes[2]],
        temperature_c=temperature_c,
        temperature_sample_time_ms=temperature_sample_time_ms,
        current_amps=current_amps,
        current_sample_time_ms=current_sample_time_ms,
        current_sample_count=current_sample_count,
        payload_json=payload_json,
    )


def build_sensor_window(readings: list[TelemetryReading]) -> Optional[dict[str, object]]:
    if len(readings) != _AI_WINDOW_SAMPLE_COUNT:
        raise ValueError(f"sensor window requires exactly {_AI_WINDOW_SAMPLE_COUNT} readings")

    sample_rate_hz = readings[0].sample_rate_hz
    expected_period_ms = 1000 / sample_rate_hz
    maximum_gap_ms = max(1, round(expected_period_ms * 3))
    for previous, current in zip(readings, readings[1:]):
        if not math.isclose(current.sample_rate_hz, sample_rate_hz, rel_tol=0, abs_tol=0.01):
            return None
        gap_ms = current.sample_time_ms - previous.sample_time_ms
        if gap_ms <= 0 or gap_ms > maximum_gap_ms:
            return None

    window_end_ms = readings[-1].sample_time_ms
    window_duration_ms = readings[-1].sample_time_ms - readings[0].sample_time_ms
    fresh_sensor_age_ms = max(2000, window_duration_ms * 2)
    temperature_readings = [
        reading
        for reading in readings
        if reading.temperature_c is not None and reading.temperature_sample_time_ms is not None
    ]
    current_readings = [
        reading
        for reading in readings
        if reading.current_amps is not None and reading.current_sample_time_ms is not None
    ]
    if not temperature_readings or not current_readings:
        return None

    temperature = temperature_readings[-1]
    current = current_readings[-1]
    temperature_sample_time_ms = temperature.temperature_sample_time_ms
    current_sample_time_ms = current.current_sample_time_ms
    if (
        temperature.temperature_c is None
        or temperature_sample_time_ms is None
        or current.current_amps is None
        or current_sample_time_ms is None
    ):
        return None
    if (
        temperature_sample_time_ms > window_end_ms
        or current_sample_time_ms > window_end_ms
        or window_end_ms - temperature_sample_time_ms > fresh_sensor_age_ms
        or window_end_ms - current_sample_time_ms > fresh_sensor_age_ms
    ):
        return None

    acceleration_samples = [
        {
            "x_m_s2": reading.accel_x_milli_ms2 * _ACCELERATION_SCALE,
            "y_m_s2": reading.accel_y_milli_ms2 * _ACCELERATION_SCALE,
            "z_m_s2": reading.accel_z_milli_ms2 * _ACCELERATION_SCALE,
        }
        for reading in readings
    ]
    return {
        "acceleration_samples": acceleration_samples,
        "sample_rate_hz": sample_rate_hz,
        "temperature_c": temperature.temperature_c,
        "current_amps": current.current_amps,
    }


def append_reading_to_sensor_window(
    reading: TelemetryReading,
) -> Optional[tuple[list[TelemetryReading], dict[str, object]]]:
    buffer = _window_buffers.setdefault(
        reading.motor_id,
        deque(maxlen=_AI_WINDOW_SAMPLE_COUNT),
    )
    if buffer:
        previous = buffer[-1]
        expected_period_ms = 1000 / previous.sample_rate_hz
        maximum_gap_ms = max(1, round(expected_period_ms * 3))
        gap_ms = reading.sample_time_ms - previous.sample_time_ms
        if (
            gap_ms <= 0
            or gap_ms > maximum_gap_ms
            or not math.isclose(
                reading.sample_rate_hz,
                previous.sample_rate_hz,
                rel_tol=0,
                abs_tol=0.01,
            )
        ):
            buffer.clear()

    buffer.append(reading)
    if len(buffer) < _AI_WINDOW_SAMPLE_COUNT:
        return None

    readings = list(buffer)
    buffer.clear()
    sensor_window = build_sensor_window(readings)
    if sensor_window is None:
        return None
    return readings, sensor_window


def parse_window(payload: bytes) -> TelemetryWindow:
    try:
        payload_json = payload.decode("utf-8")
        data = json.loads(payload_json)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"payload is not valid UTF-8 JSON: {error}") from error

    if not isinstance(data, dict):
        raise ValueError("payload must be a JSON object")
    if type(data.get("schema_version")) is not int or data["schema_version"] != 1:
        raise ValueError("schema_version must be 1")

    motor_id = data.get("motor_id")
    if not isinstance(motor_id, str) or not _MOTOR_ID_PATTERN.fullmatch(motor_id):
        raise ValueError("motor_id must contain 1-64 letters, numbers, underscores, or hyphens")

    sample_rate_hz = data.get("sample_rate_hz")
    if (
        isinstance(sample_rate_hz, bool)
        or not isinstance(sample_rate_hz, (int, float))
        or not math.isfinite(sample_rate_hz)
        or sample_rate_hz <= 0
    ):
        raise ValueError("sample_rate_hz must be a positive finite number")

    sample_count = data.get("sample_count")
    if (
        type(sample_count) is not int
        or sample_count < 1
        or sample_count > _MAX_SAMPLES_PER_WINDOW
    ):
        raise ValueError(f"sample_count must be an integer from 1 to {_MAX_SAMPLES_PER_WINDOW}")

    window_start_ms = data.get("window_start_ms")
    if type(window_start_ms) is not int or window_start_ms < 0:
        raise ValueError("window_start_ms must be a non-negative integer")

    if data.get("window_start_unit") != "ms since boot":
        raise ValueError('window_start_unit must be "ms since boot"')
    if data.get("sample_offset_unit") != "us":
        raise ValueError('sample_offset_unit must be "us"')
    if data.get("acceleration_unit") != "m/s^2":
        raise ValueError('acceleration_unit must be "m/s^2"')
    if data.get("sample_format") != "[offset_us, ax_milli_ms2, ay_milli_ms2, az_milli_ms2]":
        raise ValueError("sample_format does not match the firmware payload format")

    acceleration_scale = data.get("acceleration_scale")
    if (
        isinstance(acceleration_scale, bool)
        or not isinstance(acceleration_scale, (int, float))
        or acceleration_scale != _ACCELERATION_SCALE
    ):
        raise ValueError(f"acceleration_scale must be {_ACCELERATION_SCALE}")

    samples = data.get("samples")
    if not isinstance(samples, list) or len(samples) != sample_count:
        raise ValueError("samples must contain exactly sample_count entries")

    previous_offset_us = -1
    for index, sample in enumerate(samples):
        if not isinstance(sample, list) or len(sample) != 4:
            raise ValueError(f"samples[{index}] must contain offset, X, Y, and Z values")
        offset_us, accel_x, accel_y, accel_z = sample
        if type(offset_us) is not int or offset_us < 0 or offset_us <= previous_offset_us:
            raise ValueError(f"samples[{index}] offset must be a strictly increasing non-negative integer")
        if any(type(axis_value) is not int for axis_value in (accel_x, accel_y, accel_z)):
            raise ValueError(f"samples[{index}] acceleration values must be integers")
        previous_offset_us = offset_us

    return TelemetryWindow(
        schema_version=1,
        motor_id=motor_id,
        sample_rate_hz=float(sample_rate_hz),
        sample_count=sample_count,
        window_start_ms=window_start_ms,
        payload_json=payload_json,
    )


def calculate_acceleration_features(window: TelemetryWindow) -> AccelerationFeatures:
    samples = json.loads(window.payload_json)["samples"]
    axes = [
        [sample[axis_index] * _ACCELERATION_SCALE for sample in samples]
        for axis_index in range(1, 4)
    ]
    means = [sum(axis) / len(axis) for axis in axes]
    centered_axes = [
        [value - mean for value in axis]
        for axis, mean in zip(axes, means)
    ]
    axis_rms = [
        math.sqrt(sum(value * value for value in centered) / len(centered))
        for centered in centered_axes
    ]
    axis_peak_to_peak = [
        max(axis) - min(axis)
        for axis in axes
    ]
    vector_rms = math.sqrt(
        sum(
            sum(centered_axes[axis_index][sample_index] ** 2 for axis_index in range(3))
            for sample_index in range(window.sample_count)
        )
        / window.sample_count
    )

    return AccelerationFeatures(
        accel_x_mean_ms2=means[0],
        accel_y_mean_ms2=means[1],
        accel_z_mean_ms2=means[2],
        accel_x_rms_ms2=axis_rms[0],
        accel_y_rms_ms2=axis_rms[1],
        accel_z_rms_ms2=axis_rms[2],
        accel_x_peak_to_peak_ms2=axis_peak_to_peak[0],
        accel_y_peak_to_peak_ms2=axis_peak_to_peak[1],
        accel_z_peak_to_peak_ms2=axis_peak_to_peak[2],
        accel_vector_rms_ms2=vector_rms,
    )


def initialize_database(database_path: Path) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(database_path)) as connection:
        with connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS telemetry_windows (
                    id INTEGER PRIMARY KEY,
                    received_at TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    motor_id TEXT NOT NULL,
                    schema_version INTEGER NOT NULL,
                    sample_rate_hz REAL NOT NULL,
                    sample_count INTEGER NOT NULL,
                    window_start_ms INTEGER NOT NULL,
                    payload_json TEXT NOT NULL,
                    data_source TEXT NOT NULL DEFAULT 'simulated',
                    accel_x_mean_ms2 REAL,
                    accel_y_mean_ms2 REAL,
                    accel_z_mean_ms2 REAL,
                    accel_x_rms_ms2 REAL,
                    accel_y_rms_ms2 REAL,
                    accel_z_rms_ms2 REAL,
                    accel_x_peak_to_peak_ms2 REAL,
                    accel_y_peak_to_peak_ms2 REAL,
                    accel_z_peak_to_peak_ms2 REAL,
                    accel_vector_rms_ms2 REAL
                )
                """
            )
            existing_columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info(telemetry_windows)")
            }
            added_columns = {
                "data_source": "TEXT NOT NULL DEFAULT 'simulated'",
                **{column: "REAL" for column in _FEATURE_COLUMNS},
            }
            for column, sql_type in added_columns.items():
                if column not in existing_columns:
                    connection.execute(
                        f"ALTER TABLE telemetry_windows ADD COLUMN {column} {sql_type}"
                    )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_telemetry_windows_motor_received
                ON telemetry_windows (motor_id, received_at)
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_telemetry_windows_source_motor
                ON telemetry_windows (data_source, motor_id, received_at)
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS telemetry_readings (
                    id INTEGER PRIMARY KEY,
                    received_at TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    motor_id TEXT NOT NULL,
                    sample_rate_hz REAL NOT NULL,
                    sample_time_ms INTEGER NOT NULL,
                    accel_x_milli_ms2 INTEGER NOT NULL,
                    accel_y_milli_ms2 INTEGER NOT NULL,
                    accel_z_milli_ms2 INTEGER NOT NULL,
                    temperature_c REAL,
                    temperature_sample_time_ms INTEGER,
                    current_amps REAL,
                    current_sample_time_ms INTEGER,
                    current_sample_count INTEGER,
                    data_source TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            reading_columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info(telemetry_readings)")
            }
            added_reading_columns = {
                "temperature_c": "REAL",
                "temperature_sample_time_ms": "INTEGER",
                "current_amps": "REAL",
                "current_sample_time_ms": "INTEGER",
                "current_sample_count": "INTEGER",
            }
            for column, sql_type in added_reading_columns.items():
                if column not in reading_columns:
                    connection.execute(
                        f"ALTER TABLE telemetry_readings ADD COLUMN {column} {sql_type}"
                    )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_telemetry_readings_motor_id
                ON telemetry_readings (motor_id, id DESC)
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS telemetry_sensor_windows (
                    id INTEGER PRIMARY KEY,
                    received_at TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    motor_id TEXT NOT NULL,
                    sample_rate_hz REAL NOT NULL,
                    sample_count INTEGER NOT NULL,
                    window_start_ms INTEGER NOT NULL,
                    window_end_ms INTEGER NOT NULL,
                    data_source TEXT NOT NULL,
                    label TEXT NOT NULL DEFAULT 'unknown',
                    fault_type TEXT,
                    label_notes TEXT,
                    payload_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_sensor_windows_motor_source_label
                ON telemetry_sensor_windows (motor_id, data_source, label, id DESC)
                """
            )
            rows_to_backfill = connection.execute(
                """
                SELECT id, payload_json
                FROM telemetry_windows
                WHERE accel_x_rms_ms2 IS NULL
                """
            ).fetchall()
            for row_id, payload_json in rows_to_backfill:
                window = parse_window(payload_json.encode("utf-8"))
                features = calculate_acceleration_features(window)
                values = tuple(getattr(features, column) for column in _FEATURE_COLUMNS)
                assignments = ", ".join(f"{column} = ?" for column in _FEATURE_COLUMNS)
                connection.execute(
                    f"UPDATE telemetry_windows SET {assignments} WHERE id = ?",
                    (*values, row_id),
                )


def store_window(
    database_path: Path,
    topic: str,
    window: TelemetryWindow,
    data_source: str = DATA_SOURCE,
) -> None:
    if data_source not in _DATA_SOURCES:
        raise ValueError(f"data_source must be one of: {', '.join(sorted(_DATA_SOURCES))}")

    received_at = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
    features = calculate_acceleration_features(window)
    feature_values = tuple(getattr(features, column) for column in _FEATURE_COLUMNS)
    feature_columns = ", ".join(_FEATURE_COLUMNS)
    feature_placeholders = ", ".join("?" for _ in _FEATURE_COLUMNS)
    with closing(sqlite3.connect(database_path, timeout=5)) as connection:
        with connection:
            connection.execute(
                f"""
                INSERT INTO telemetry_windows (
                    received_at,
                    topic,
                    motor_id,
                    schema_version,
                    sample_rate_hz,
                    sample_count,
                    window_start_ms,
                    payload_json,
                    data_source,
                    {feature_columns}
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, {feature_placeholders})
                """,
                (
                    received_at,
                    topic,
                    window.motor_id,
                    window.schema_version,
                    window.sample_rate_hz,
                    window.sample_count,
                    window.window_start_ms,
                    window.payload_json,
                    data_source,
                    *feature_values,
                ),
            )


def store_reading(
    database_path: Path,
    topic: str,
    reading: TelemetryReading,
    data_source: str = DATA_SOURCE,
) -> None:
    global _raw_readings_since_cleanup

    if data_source not in _DATA_SOURCES:
        raise ValueError(f"data_source must be one of: {', '.join(sorted(_DATA_SOURCES))}")

    received_at = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
    with closing(sqlite3.connect(database_path, timeout=5)) as connection:
        with connection:
            connection.execute(
                """
                INSERT INTO telemetry_readings (
                    received_at, topic, motor_id, sample_rate_hz, sample_time_ms,
                    accel_x_milli_ms2, accel_y_milli_ms2, accel_z_milli_ms2,
                    temperature_c, temperature_sample_time_ms,
                    current_amps, current_sample_time_ms, current_sample_count,
                    data_source, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    received_at,
                    topic,
                    reading.motor_id,
                    reading.sample_rate_hz,
                    reading.sample_time_ms,
                    reading.accel_x_milli_ms2,
                    reading.accel_y_milli_ms2,
                    reading.accel_z_milli_ms2,
                    reading.temperature_c,
                    reading.temperature_sample_time_ms,
                    reading.current_amps,
                    reading.current_sample_time_ms,
                    reading.current_sample_count,
                    data_source,
                    reading.payload_json,
                ),
            )
            _raw_readings_since_cleanup += 1
            if _raw_readings_since_cleanup >= 100:
                connection.execute(
                    """
                    DELETE FROM telemetry_readings
                    WHERE motor_id = ?
                      AND id NOT IN (
                          SELECT id
                          FROM telemetry_readings
                          WHERE motor_id = ?
                          ORDER BY id DESC
                          LIMIT ?
                      )
                    """,
                    (reading.motor_id, reading.motor_id, _RAW_READING_RETENTION_LIMIT),
                )
                _raw_readings_since_cleanup = 0


def store_sensor_window(
    database_path: Path,
    topic: str,
    readings: list[TelemetryReading],
    sensor_window: dict[str, object],
    data_source: str = DATA_SOURCE,
) -> int:
    global _sensor_windows_since_cleanup

    if data_source not in _DATA_SOURCES:
        raise ValueError(f"data_source must be one of: {', '.join(sorted(_DATA_SOURCES))}")
    if len(readings) != _AI_WINDOW_SAMPLE_COUNT:
        raise ValueError(f"sensor window requires exactly {_AI_WINDOW_SAMPLE_COUNT} readings")

    received_at = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
    with closing(sqlite3.connect(database_path, timeout=5)) as connection:
        with connection:
            cursor = connection.execute(
                """
                INSERT INTO telemetry_sensor_windows (
                    received_at, topic, motor_id, sample_rate_hz, sample_count,
                    window_start_ms, window_end_ms, data_source, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    received_at,
                    topic,
                    readings[0].motor_id,
                    readings[0].sample_rate_hz,
                    len(readings),
                    readings[0].sample_time_ms,
                    readings[-1].sample_time_ms,
                    data_source,
                    json.dumps(sensor_window, separators=(",", ":"), allow_nan=False),
                ),
            )
            window_id = int(cursor.lastrowid)
            _sensor_windows_since_cleanup += 1
            if _sensor_windows_since_cleanup >= 100:
                connection.execute(
                    """
                    DELETE FROM telemetry_sensor_windows
                    WHERE motor_id = ?
                      AND id NOT IN (
                          SELECT id
                          FROM telemetry_sensor_windows
                          WHERE motor_id = ?
                          ORDER BY id DESC
                          LIMIT ?
                      )
                    """,
                    (readings[0].motor_id, readings[0].motor_id, _AI_WINDOW_RETENTION_LIMIT),
                )
                _sensor_windows_since_cleanup = 0

    return window_id


def get_telemetry_snapshot(
    database_path: Path,
    motor_id: str,
    history_limit: int = 60,
) -> dict[str, object]:
    if not _MOTOR_ID_PATTERN.fullmatch(motor_id):
        raise ValueError("motor_id must contain 1-64 letters, numbers, underscores, or hyphens")
    if type(history_limit) is not int or not 1 <= history_limit <= _MAX_RAW_READINGS:
        raise ValueError(f"history_limit must be an integer from 1 to {_MAX_RAW_READINGS}")

    feature_columns = ", ".join(_FEATURE_COLUMNS)
    with closing(sqlite3.connect(database_path, timeout=5)) as connection:
        raw_rows = connection.execute(
            """
            SELECT received_at, data_source, sample_rate_hz, sample_time_ms,
                   accel_x_milli_ms2, accel_y_milli_ms2, accel_z_milli_ms2,
                   temperature_c, temperature_sample_time_ms,
                   current_amps, current_sample_time_ms, current_sample_count
            FROM telemetry_readings
            WHERE motor_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (motor_id, history_limit),
        ).fetchall()
        if raw_rows:
            raw_rows.reverse()
            latest_row = raw_rows[-1]
            latest = {
                "received_at": latest_row[0],
                "data_source": latest_row[1],
                "sample_rate_hz": latest_row[2],
                "sample_count": 1,
                "sample_time_ms": latest_row[3],
                "samples": [
                    {
                        "offset_s": 0.0,
                        "x_ms2": latest_row[4] * _ACCELERATION_SCALE,
                        "y_ms2": latest_row[5] * _ACCELERATION_SCALE,
                        "z_ms2": latest_row[6] * _ACCELERATION_SCALE,
                    }
                ],
            }
            if latest_row[7] is not None:
                latest["temperature"] = {
                    "value_c": latest_row[7],
                    "sample_time_ms": latest_row[8],
                }
            if latest_row[9] is not None:
                latest["current"] = {
                    "value_amps_rms": latest_row[9],
                    "sample_time_ms": latest_row[10],
                    "sample_count": latest_row[11],
                }

            history = []
            for row in raw_rows:
                item = {
                    "received_at": row[0],
                    "data_source": row[1],
                    "acceleration": {
                        "x_ms2": row[4] * _ACCELERATION_SCALE,
                        "y_ms2": row[5] * _ACCELERATION_SCALE,
                        "z_ms2": row[6] * _ACCELERATION_SCALE,
                    },
                }
                if row[7] is not None:
                    item["temperature"] = {
                        "value_c": row[7],
                        "sample_time_ms": row[8],
                    }
                if row[9] is not None:
                    item["current"] = {
                        "value_amps_rms": row[9],
                        "sample_time_ms": row[10],
                        "sample_count": row[11],
                    }
                history.append(item)
            return {
                "motor_id": motor_id,
                "latest": latest,
                "history": history,
                "mqtt_connected": _mqtt_connected,
            }

        rows = connection.execute(
            f"""
            SELECT received_at, data_source, sample_rate_hz, sample_count,
                   window_start_ms, payload_json, {feature_columns}
            FROM telemetry_windows
            WHERE motor_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (motor_id, history_limit),
        ).fetchall()

    rows.reverse()
    if not rows:
        return {
            "motor_id": motor_id,
            "latest": None,
            "history": [],
            "mqtt_connected": _mqtt_connected,
        }

    latest_row = rows[-1]
    latest_payload = json.loads(latest_row[5])
    latest = {
        "received_at": latest_row[0],
        "data_source": latest_row[1],
        "sample_rate_hz": latest_row[2],
        "sample_count": latest_row[3],
        "window_start_ms": latest_row[4],
        "samples": [
            {
                "offset_s": sample[0] / 1_000_000,
                "x_ms2": sample[1] * _ACCELERATION_SCALE,
                "y_ms2": sample[2] * _ACCELERATION_SCALE,
                "z_ms2": sample[3] * _ACCELERATION_SCALE,
            }
            for sample in latest_payload["samples"]
        ],
        "features": dict(zip(_FEATURE_COLUMNS, latest_row[6:])),
    }
    history = [
        {
            "received_at": row[0],
            "data_source": row[1],
            "features": dict(zip(_FEATURE_COLUMNS, row[6:])),
        }
        for row in rows
    ]
    return {
        "motor_id": motor_id,
        "latest": latest,
        "history": history,
        "mqtt_connected": _mqtt_connected,
    }


def get_sensor_windows(
    database_path: Path,
    motor_id: str,
    label: Optional[str] = None,
    data_source: Optional[str] = None,
    limit: int = 100,
) -> dict[str, object]:
    if not _MOTOR_ID_PATTERN.fullmatch(motor_id):
        raise ValueError("motor_id must contain 1-64 letters, numbers, underscores, or hyphens")
    if label is not None and label not in _LABELS:
        raise ValueError(f"label must be one of: {', '.join(sorted(_LABELS))}")
    if data_source is not None and data_source not in _DATA_SOURCES:
        raise ValueError(f"data_source must be one of: {', '.join(sorted(_DATA_SOURCES))}")
    if type(limit) is not int or not 1 <= limit <= 500:
        raise ValueError("limit must be an integer from 1 to 500")

    filters = ["motor_id = ?"]
    parameters: list[object] = [motor_id]
    if label is not None:
        filters.append("label = ?")
        parameters.append(label)
    if data_source is not None:
        filters.append("data_source = ?")
        parameters.append(data_source)

    with closing(sqlite3.connect(database_path, timeout=5)) as connection:
        rows = connection.execute(
            f"""
            SELECT id, received_at, sample_rate_hz, sample_count,
                   window_start_ms, window_end_ms, data_source, label,
                   fault_type, label_notes, payload_json
            FROM telemetry_sensor_windows
            WHERE {" AND ".join(filters)}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*parameters, limit),
        ).fetchall()

    rows.reverse()
    return {
        "motor_id": motor_id,
        "windows": [
            {
                "window_id": row[0],
                "received_at": row[1],
                "sample_rate_hz": row[2],
                "sample_count": row[3],
                "window_start_ms": row[4],
                "window_end_ms": row[5],
                "data_source": row[6],
                "label": row[7],
                "fault_type": row[8],
                "label_notes": row[9],
                "sensor_window": json.loads(row[10]),
            }
            for row in rows
        ],
    }


def label_sensor_window(
    database_path: Path,
    motor_id: str,
    window_id: int,
    label: str,
    fault_type: Optional[str] = None,
    notes: Optional[str] = None,
) -> bool:
    if not _MOTOR_ID_PATTERN.fullmatch(motor_id):
        raise ValueError("motor_id must contain 1-64 letters, numbers, underscores, or hyphens")
    if label not in _LABELS:
        raise ValueError(f"label must be one of: {', '.join(sorted(_LABELS))}")
    if label == "confirmed_fault" and not fault_type:
        raise ValueError("fault_type is required when label is confirmed_fault")
    if fault_type is not None and (not isinstance(fault_type, str) or len(fault_type) > 80):
        raise ValueError("fault_type must be a string of at most 80 characters")
    if notes is not None and (not isinstance(notes, str) or len(notes) > 500):
        raise ValueError("notes must be a string of at most 500 characters")

    with closing(sqlite3.connect(database_path, timeout=5)) as connection:
        with connection:
            cursor = connection.execute(
                """
                UPDATE telemetry_sensor_windows
                SET label = ?, fault_type = ?, label_notes = ?
                WHERE id = ? AND motor_id = ?
                """,
                (label, fault_type, notes, window_id, motor_id),
            )
    return cursor.rowcount == 1


def start_telemetry_api(database_path: Path, host: str = API_HOST, port: int = API_PORT) -> ThreadingHTTPServer:
    class TelemetryRequestHandler(BaseHTTPRequestHandler):
        def _send_json(self, status_code: int, body: dict[str, object]) -> None:
            response = json.dumps(body, allow_nan=False).encode("utf-8")
            self.send_response(status_code)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(response)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(response)

        def do_GET(self) -> None:
            parsed_url = urlsplit(self.path)
            if parsed_url.path == "/health":
                self._send_json(
                    200,
                    {
                        "status": "ok",
                        "service": "motorpulse-telemetry",
                        "mqtt_connected": _mqtt_connected,
                    },
                )
                return

            windows_match = re.fullmatch(
                r"/api/motors/([A-Za-z0-9_-]{1,64})/windows",
                parsed_url.path,
            )
            if windows_match:
                query = parse_qs(parsed_url.query, strict_parsing=False)
                try:
                    raw_limit = query.get("limit", ["100"])[0]
                    if not raw_limit.isdecimal():
                        raise ValueError("limit must be an integer from 1 to 500")
                    result = get_sensor_windows(
                        database_path,
                        windows_match.group(1),
                        label=query.get("label", [None])[0],
                        data_source=query.get("source", [None])[0],
                        limit=int(raw_limit),
                    )
                except ValueError as error:
                    self._send_json(400, {"detail": str(error)})
                    return
                except sqlite3.Error as error:
                    print(f"Sensor-window query failed: {error}")
                    self._send_json(500, {"detail": "Could not read sensor windows"})
                    return

                self._send_json(200, result)
                return

            match = re.fullmatch(r"/api/motors/([A-Za-z0-9_-]{1,64})/telemetry", parsed_url.path)
            if not match:
                self._send_json(404, {"detail": "Endpoint not found"})
                return

            query = parse_qs(parsed_url.query, strict_parsing=False)
            try:
                raw_limit = query.get("limit", ["60"])[0]
                if not raw_limit.isdecimal():
                    raise ValueError(f"limit must be an integer from 1 to {_MAX_RAW_READINGS}")
                snapshot = get_telemetry_snapshot(database_path, match.group(1), int(raw_limit))
            except ValueError as error:
                self._send_json(400, {"detail": str(error)})
                return
            except sqlite3.Error as error:
                print(f"Telemetry API database query failed: {error}")
                self._send_json(500, {"detail": "Could not read telemetry from the database"})
                return

            self._send_json(200, snapshot)

        def do_POST(self) -> None:
            match = re.fullmatch(
                r"/api/motors/([A-Za-z0-9_-]{1,64})/windows/([0-9]+)/label",
                urlsplit(self.path).path,
            )
            if not match:
                self._send_json(404, {"detail": "Endpoint not found"})
                return

            content_length = self.headers.get("Content-Length", "")
            if not content_length.isdecimal() or int(content_length) > 8192:
                self._send_json(400, {"detail": "Content-Length must be an integer no greater than 8192"})
                return
            try:
                body = json.loads(self.rfile.read(int(content_length)).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                self._send_json(400, {"detail": f"Request body must be valid UTF-8 JSON: {error}"})
                return
            if not isinstance(body, dict):
                self._send_json(400, {"detail": "Request body must be a JSON object"})
                return
            if set(body) - {"label", "fault_type", "notes"}:
                self._send_json(400, {"detail": "Request contains unsupported fields"})
                return
            label = body.get("label")
            if not isinstance(label, str):
                self._send_json(400, {"detail": "label must be a string"})
                return

            try:
                updated = label_sensor_window(
                    database_path,
                    match.group(1),
                    int(match.group(2)),
                    label,
                    fault_type=body.get("fault_type"),
                    notes=body.get("notes"),
                )
            except ValueError as error:
                self._send_json(400, {"detail": str(error)})
                return
            except sqlite3.Error as error:
                print(f"Sensor-window label update failed: {error}")
                self._send_json(500, {"detail": "Could not update sensor-window label"})
                return

            if not updated:
                self._send_json(404, {"detail": "Sensor window not found"})
                return
            self._send_json(200, {"window_id": int(match.group(2)), "label": label, "updated": True})

        def do_OPTIONS(self) -> None:
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()

        def log_message(self, format: str, *args: object) -> None:
            return

    server = ThreadingHTTPServer((host, port), TelemetryRequestHandler)
    Thread(target=server.serve_forever, name="telemetry-api", daemon=True).start()
    print(f"Telemetry API listening on http://{host}:{server.server_port}")
    return server


def on_connect(client, userdata, flags, reason_code, properties):
    global _mqtt_connected
    _mqtt_connected = reason_code == 0
    if not _mqtt_connected:
        print(f"MQTT broker connection rejected: {reason_code}")
        return
    print(f"Connected to MQTT broker: {reason_code}")
    result, _ = client.subscribe(MQTT_TOPIC)
    if result != mqtt.MQTT_ERR_SUCCESS:
        print(f"Could not subscribe to {MQTT_TOPIC}: MQTT error {result}")


def on_disconnect(client, userdata, disconnect_flags, reason_code, properties):
    global _mqtt_connected
    _mqtt_connected = False
    if reason_code != 0:
        print(f"Disconnected from MQTT broker: {reason_code}; retrying")


def on_message(client, userdata, message):
    try:
        message_data = json.loads(message.payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        message_data = None

    if isinstance(message_data, dict) and message_data.get("message_type") == "acceleration":
        try:
            reading = parse_reading(message.payload)
        except ValueError as error:
            print(f"Rejected invalid telemetry on {message.topic}: {error}")
            return

        try:
            store_reading(DATABASE_PATH, message.topic, reading)
        except sqlite3.Error as error:
            print(f"Could not save telemetry reading to {DATABASE_PATH}: {error}")
            return

        window_batch = append_reading_to_sensor_window(reading)
        if window_batch is not None:
            readings, sensor_window = window_batch
            try:
                window_id = store_sensor_window(
                    DATABASE_PATH,
                    message.topic,
                    readings,
                    sensor_window,
                )
            except sqlite3.Error as error:
                print(f"Could not save prepared sensor window to {DATABASE_PATH}: {error}")
                return
            print(
                f"Stored AI-ready window {window_id} for {reading.motor_id} "
                f"({len(readings)} samples, {DATA_SOURCE})"
            )

        if reading.sample_time_ms % 5000 < int(1000 / reading.sample_rate_hz):
            print(
                f"Receiving raw acceleration for {reading.motor_id} "
                f"({reading.sample_rate_hz:g} Hz, {DATA_SOURCE}) from {message.topic}"
            )
        return

    try:
        window = parse_window(message.payload)
    except ValueError as error:
        print(f"Rejected invalid telemetry on {message.topic}: {error}")
        return

    try:
        store_window(DATABASE_PATH, message.topic, window)
    except sqlite3.Error as error:
        print(f"Could not save telemetry window to {DATABASE_PATH}: {error}")
        return

    print(
        f"Saved {window.sample_count} samples for {window.motor_id} "
        f"({window.sample_rate_hz:g} Hz, {DATA_SOURCE}) from {message.topic}"
    )


def main() -> None:
    initialize_database(DATABASE_PATH)
    start_telemetry_api(DATABASE_PATH)
    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id="windows-mqtt-receiver",
    )
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    client.reconnect_delay_set(min_delay=1, max_delay=30)
    client.connect_async(MQTT_HOST, MQTT_PORT, keepalive=60)
    print(
        f"Telemetry API listening on http://{API_HOST}:{API_PORT}; "
        f"connecting to MQTT broker {MQTT_HOST}:{MQTT_PORT}; "
        f"saving telemetry to {DATABASE_PATH}. Press Ctrl+C to stop."
    )
    client.loop_forever()


if __name__ == "__main__":
    main()

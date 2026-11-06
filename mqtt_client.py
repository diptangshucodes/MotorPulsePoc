import json
import math
import os
import re
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
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
_MAX_HISTORY_WINDOWS = 120
_ACCELERATION_SCALE = 0.001


@dataclass(frozen=True)
class TelemetryWindow:
    schema_version: int
    motor_id: str
    sample_rate_hz: float
    sample_count: int
    window_start_ms: int
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


def get_telemetry_snapshot(
    database_path: Path,
    motor_id: str,
    history_limit: int = 60,
) -> dict[str, object]:
    if not _MOTOR_ID_PATTERN.fullmatch(motor_id):
        raise ValueError("motor_id must contain 1-64 letters, numbers, underscores, or hyphens")
    if type(history_limit) is not int or not 1 <= history_limit <= _MAX_HISTORY_WINDOWS:
        raise ValueError(f"history_limit must be an integer from 1 to {_MAX_HISTORY_WINDOWS}")

    feature_columns = ", ".join(_FEATURE_COLUMNS)
    with closing(sqlite3.connect(database_path, timeout=5)) as connection:
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
        return {"motor_id": motor_id, "latest": None, "history": []}

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
    return {"motor_id": motor_id, "latest": latest, "history": history}


def start_telemetry_api(database_path: Path, host: str = API_HOST, port: int = API_PORT) -> ThreadingHTTPServer:
    class TelemetryRequestHandler(BaseHTTPRequestHandler):
        def _send_json(self, status_code: int, body: dict[str, object]) -> None:
            response = json.dumps(body, allow_nan=False).encode("utf-8")
            self.send_response(status_code)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(response)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(response)

        def do_GET(self) -> None:
            parsed_url = urlsplit(self.path)
            if parsed_url.path == "/health":
                self._send_json(200, {"status": "ok", "service": "motorpulse-telemetry"})
                return

            match = re.fullmatch(r"/api/motors/([A-Za-z0-9_-]{1,64})/telemetry", parsed_url.path)
            if not match:
                self._send_json(404, {"detail": "Endpoint not found"})
                return

            query = parse_qs(parsed_url.query, strict_parsing=False)
            try:
                raw_limit = query.get("limit", ["60"])[0]
                if not raw_limit.isdecimal():
                    raise ValueError(f"limit must be an integer from 1 to {_MAX_HISTORY_WINDOWS}")
                snapshot = get_telemetry_snapshot(database_path, match.group(1), int(raw_limit))
            except ValueError as error:
                self._send_json(400, {"detail": str(error)})
                return
            except sqlite3.Error as error:
                print(f"Telemetry API database query failed: {error}")
                self._send_json(500, {"detail": "Could not read telemetry from the database"})
                return

            self._send_json(200, snapshot)

        def log_message(self, format: str, *args: object) -> None:
            return

    server = ThreadingHTTPServer((host, port), TelemetryRequestHandler)
    Thread(target=server.serve_forever, name="telemetry-api", daemon=True).start()
    print(f"Telemetry API listening on http://{host}:{server.server_port}")
    return server


def on_connect(client, userdata, flags, reason_code, properties):
    print(f"Connected to MQTT broker: {reason_code}")
    result, _ = client.subscribe(MQTT_TOPIC)
    if result != mqtt.MQTT_ERR_SUCCESS:
        print(f"Could not subscribe to {MQTT_TOPIC}: MQTT error {result}")


def on_message(client, userdata, message):
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
    client.on_message = on_message

    client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    print(f"Listening on {MQTT_HOST}:{MQTT_PORT}; saving telemetry to {DATABASE_PATH}. Press Ctrl+C to stop.")
    client.loop_forever()


if __name__ == "__main__":
    main()

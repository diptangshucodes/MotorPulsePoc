import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from urllib.request import Request, urlopen

from mqtt_client import (
    append_reading_to_sensor_window,
    calculate_acceleration_features,
    get_telemetry_snapshot,
    initialize_database,
    parse_reading,
    parse_window,
    start_telemetry_api,
    store_reading,
    store_sensor_window,
    store_window,
)


def make_payload(samples=None) -> bytes:
    if samples is None:
        samples = [[index * 10_000, 0, 0, 9_810] for index in range(128)]
    return json.dumps(
        {
            "schema_version": 1,
            "motor_id": "motor-01",
            "sample_rate_hz": 100,
            "sample_count": len(samples),
            "window_start_ms": 1234,
            "window_start_unit": "ms since boot",
            "sample_offset_unit": "us",
            "acceleration_unit": "m/s^2",
            "acceleration_scale": 0.001,
            "sample_format": "[offset_us, ax_milli_ms2, ay_milli_ms2, az_milli_ms2]",
            "samples": samples,
        },
        separators=(",", ":"),
    ).encode("utf-8")


def make_reading_payload(
    sample_time_ms=1234,
    x=250,
    y=-500,
    z=9800,
    sample_rate_hz=20,
    motor_id="motor-01",
) -> bytes:
    return json.dumps(
        {
            "schema_version": 2,
            "message_type": "acceleration",
            "motor_id": motor_id,
            "sample_rate_hz": sample_rate_hz,
            "sample_time_ms": sample_time_ms,
            "acceleration_unit": "m/s^2",
            "acceleration_scale": 0.001,
            "accel_x_milli_ms2": x,
            "accel_y_milli_ms2": y,
            "accel_z_milli_ms2": z,
            "temperature_c": 31.5,
            "temperature_sample_time_ms": sample_time_ms,
            "current_amps": 0.42,
            "current_unit": "A",
            "current_measurement": "rms_1s",
            "current_sample_time_ms": (sample_time_ms // 1000) * 1000,
            "current_sample_count": 1980,
        },
        separators=(",", ":"),
    ).encode("utf-8")


class TelemetryWindowTests(unittest.TestCase):
    def test_parse_window_accepts_current_firmware_payload(self):
        window = parse_window(make_payload())

        self.assertEqual(window.motor_id, "motor-01")
        self.assertEqual(window.sample_count, 128)
        self.assertEqual(window.sample_rate_hz, 100.0)
        self.assertIn('"acceleration_scale":0.001', window.payload_json)

    def test_parse_window_rejects_malformed_and_inconsistent_payloads(self):
        with self.assertRaisesRegex(ValueError, "valid UTF-8 JSON"):
            parse_window(b"{not json")

        payload = json.loads(make_payload())
        payload["sample_count"] = 127
        with self.assertRaisesRegex(ValueError, "exactly sample_count"):
            parse_window(json.dumps(payload).encode("utf-8"))

        payload = json.loads(make_payload())
        payload["samples"][1][0] = payload["samples"][0][0]
        with self.assertRaisesRegex(ValueError, "strictly increasing"):
            parse_window(json.dumps(payload).encode("utf-8"))

    def test_parse_reading_accepts_raw_mpu6050_payload_and_rejects_invalid_axes(self):
        reading = parse_reading(make_reading_payload())

        self.assertEqual(reading.motor_id, "motor-01")
        self.assertEqual(reading.sample_rate_hz, 20.0)
        self.assertEqual(reading.sample_time_ms, 1234)
        self.assertEqual(reading.accel_x_milli_ms2, 250)
        self.assertEqual(reading.accel_y_milli_ms2, -500)
        self.assertEqual(reading.accel_z_milli_ms2, 9800)
        self.assertEqual(reading.temperature_c, 31.5)
        self.assertEqual(reading.current_amps, 0.42)
        self.assertEqual(reading.current_sample_count, 1980)

        payload = json.loads(make_reading_payload())
        payload["accel_x_milli_ms2"] = 0.25
        with self.assertRaisesRegex(ValueError, "axis values must be integers"):
            parse_reading(json.dumps(payload).encode("utf-8"))

        payload = json.loads(make_reading_payload())
        del payload["current_sample_count"]
        with self.assertRaisesRegex(ValueError, "all current measurement fields"):
            parse_reading(json.dumps(payload).encode("utf-8"))

    def test_acceleration_readings_form_a_window_with_fresh_sensor_values(self):
        readings = [
            parse_reading(
                make_reading_payload(
                    sample_time_ms=1000 + index * 10,
                    sample_rate_hz=100,
                    motor_id="window-motor",
                )
            )
            for index in range(128)
        ]
        completed_window = None
        for reading in readings:
            completed_window = append_reading_to_sensor_window(reading)

        self.assertIsNotNone(completed_window)
        batch, sensor_window = completed_window
        self.assertEqual(len(batch), 128)
        self.assertEqual(sensor_window["sample_rate_hz"], 100.0)
        self.assertEqual(sensor_window["temperature_c"], 31.5)
        self.assertEqual(sensor_window["current_amps"], 0.42)
        self.assertEqual(sensor_window["acceleration_samples"][0]["x_m_s2"], 0.25)

    def test_window_rejects_stale_slow_sensor_values(self):
        readings = [
            parse_reading(
                make_reading_payload(
                    sample_time_ms=10_000 + index * 10,
                    sample_rate_hz=100,
                    motor_id="stale-window-motor",
                )
            )
            for index in range(128)
        ]
        readings = [
            parse_reading(
                json.dumps(
                    {
                        **json.loads(reading.payload_json),
                        "temperature_sample_time_ms": 1000,
                        "current_sample_time_ms": 1000,
                    }
                ).encode("utf-8")
            )
            for reading in readings
        ]

        completed_window = None
        for reading in readings:
            completed_window = append_reading_to_sensor_window(reading)

        self.assertIsNone(completed_window)

    def test_calculate_acceleration_features_removes_gravity_and_measures_variation(self):
        samples = [
            [index * 10_000, -1000 if index % 2 == 0 else 1000, 0, 9810]
            for index in range(128)
        ]
        features = calculate_acceleration_features(parse_window(make_payload(samples)))

        self.assertAlmostEqual(features.accel_x_mean_ms2, 0.0)
        self.assertAlmostEqual(features.accel_y_mean_ms2, 0.0)
        self.assertAlmostEqual(features.accel_z_mean_ms2, 9.81)
        self.assertAlmostEqual(features.accel_x_rms_ms2, 1.0)
        self.assertAlmostEqual(features.accel_y_rms_ms2, 0.0)
        self.assertAlmostEqual(features.accel_z_rms_ms2, 0.0)
        self.assertAlmostEqual(features.accel_x_peak_to_peak_ms2, 2.0)
        self.assertAlmostEqual(features.accel_vector_rms_ms2, 1.0)

    def test_store_window_persists_features_and_simulated_source(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / "data" / "telemetry.sqlite3"
            initialize_database(database_path)
            raw_payload = make_payload()
            window = parse_window(raw_payload)
            store_window(database_path, "esp32/switch", window)

            with closing(sqlite3.connect(database_path)) as connection, connection:
                row = connection.execute(
                    """
                    SELECT received_at, topic, motor_id, sample_rate_hz,
                           sample_count, window_start_ms, payload_json,
                           data_source, accel_x_rms_ms2, accel_z_mean_ms2,
                           accel_vector_rms_ms2
                    FROM telemetry_windows
                    """
                ).fetchone()

        self.assertIsNotNone(row)
        self.assertTrue(row[0].endswith("+00:00"))
        self.assertEqual(row[1:6], ("esp32/switch", "motor-01", 100.0, 128, 1234))
        self.assertEqual(row[6], raw_payload.decode("utf-8"))
        self.assertEqual(row[7], "simulated")
        self.assertAlmostEqual(row[8], 0.0)
        self.assertAlmostEqual(row[9], 9.81)
        self.assertAlmostEqual(row[10], 0.0)

    def test_raw_readings_are_stored_and_returned_without_window_aggregation(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / "telemetry.sqlite3"
            initialize_database(database_path)
            store_reading(
                database_path,
                "esp32/switch",
                parse_reading(make_reading_payload(sample_time_ms=1000)),
            )
            store_reading(
                database_path,
                "esp32/switch",
                parse_reading(make_reading_payload(sample_time_ms=1050, x=750)),
            )

            snapshot = get_telemetry_snapshot(database_path, "motor-01", history_limit=5)

        self.assertEqual(snapshot["latest"]["sample_count"], 1)
        self.assertEqual(snapshot["latest"]["sample_time_ms"], 1050)
        self.assertEqual(snapshot["latest"]["samples"], [
            {"offset_s": 0.0, "x_ms2": 0.75, "y_ms2": -0.5, "z_ms2": 9.8},
        ])
        self.assertEqual(snapshot["latest"]["temperature"]["value_c"], 31.5)
        self.assertEqual(snapshot["latest"]["current"]["value_amps_rms"], 0.42)
        self.assertEqual(len(snapshot["history"]), 2)
        self.assertEqual(snapshot["history"][-1]["acceleration"]["x_ms2"], 0.75)
        self.assertNotIn("features", snapshot["latest"])
        self.assertFalse(snapshot["mqtt_connected"])

    def test_initialize_database_migrates_and_backfills_existing_windows(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / "telemetry.sqlite3"
            with closing(sqlite3.connect(database_path)) as connection, connection:
                connection.execute(
                    """
                    CREATE TABLE telemetry_windows (
                        id INTEGER PRIMARY KEY,
                        received_at TEXT NOT NULL,
                        topic TEXT NOT NULL,
                        motor_id TEXT NOT NULL,
                        schema_version INTEGER NOT NULL,
                        sample_rate_hz REAL NOT NULL,
                        sample_count INTEGER NOT NULL,
                        window_start_ms INTEGER NOT NULL,
                        payload_json TEXT NOT NULL
                    )
                    """
                )
                connection.execute(
                    """
                    INSERT INTO telemetry_windows (
                        received_at, topic, motor_id, schema_version,
                        sample_rate_hz, sample_count, window_start_ms, payload_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "2026-01-01T00:00:00+00:00",
                        "esp32/switch",
                        "motor-01",
                        1,
                        100.0,
                        128,
                        1234,
                        make_payload().decode("utf-8"),
                    ),
                )

            initialize_database(database_path)
            initialize_database(database_path)
            with closing(sqlite3.connect(database_path)) as connection:
                row = connection.execute(
                    """
                    SELECT data_source, accel_x_rms_ms2, accel_z_mean_ms2,
                           accel_vector_rms_ms2
                    FROM telemetry_windows
                    WHERE id = 1
                    """
                ).fetchone()

        self.assertEqual(row[0], "simulated")
        self.assertAlmostEqual(row[1], 0.0)
        self.assertAlmostEqual(row[2], 9.81)
        self.assertAlmostEqual(row[3], 0.0)

    def test_telemetry_snapshot_exposes_latest_samples_and_feature_history(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / "telemetry.sqlite3"
            initialize_database(database_path)
            window = parse_window(make_payload())
            store_window(database_path, "esp32/switch", window)

            snapshot = get_telemetry_snapshot(database_path, "motor-01", history_limit=5)

        self.assertEqual(snapshot["motor_id"], "motor-01")
        self.assertEqual(len(snapshot["latest"]["samples"]), 128)
        self.assertEqual(snapshot["latest"]["samples"][0]["offset_s"], 0.0)
        self.assertEqual(snapshot["latest"]["samples"][0]["z_ms2"], 9.81)
        self.assertEqual(snapshot["latest"]["data_source"], "simulated")
        self.assertEqual(len(snapshot["history"]), 1)
        self.assertEqual(snapshot["history"][0]["features"]["accel_vector_rms_ms2"], 0.0)

    def test_telemetry_snapshot_rejects_invalid_motor_and_history_limit(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / "telemetry.sqlite3"
            initialize_database(database_path)

            with self.assertRaisesRegex(ValueError, "motor_id"):
                get_telemetry_snapshot(database_path, "../motor", history_limit=5)
            with self.assertRaisesRegex(ValueError, "history_limit"):
                get_telemetry_snapshot(database_path, "motor-01", history_limit=0)

    def test_telemetry_api_serves_snapshot_with_browser_cors(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / "telemetry.sqlite3"
            initialize_database(database_path)
            store_window(
                database_path,
                "esp32/switch",
                parse_window(make_payload()),
            )
            server = start_telemetry_api(database_path, host="127.0.0.1", port=0)
            try:
                with urlopen(
                    f"http://127.0.0.1:{server.server_port}/api/motors/motor-01/telemetry?limit=1"
                ) as response:
                    body = json.loads(response.read())
                    self.assertEqual(response.status, 200)
                    self.assertEqual(response.headers["Access-Control-Allow-Origin"], "*")
                    self.assertFalse(body["mqtt_connected"])
            finally:
                server.shutdown()
                server.server_close()

        self.assertEqual(body["motor_id"], "motor-01")
        self.assertEqual(body["latest"]["data_source"], "simulated")
        self.assertEqual(len(body["latest"]["samples"]), 128)

    def test_telemetry_api_labels_and_filters_training_windows(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / "telemetry.sqlite3"
            initialize_database(database_path)
            readings = [
                parse_reading(
                    make_reading_payload(
                        sample_time_ms=1000 + index * 10,
                        sample_rate_hz=100,
                        motor_id="label-motor",
                    )
                )
                for index in range(128)
            ]
            window_batch = None
            for reading in readings:
                window_batch = append_reading_to_sensor_window(reading)
            self.assertIsNotNone(window_batch)
            batch, sensor_window = window_batch
            window_id = store_sensor_window(
                database_path,
                "esp32/switch",
                batch,
                sensor_window,
                data_source="real",
            )
            server = start_telemetry_api(database_path, host="127.0.0.1", port=0)
            try:
                body = json.dumps(
                    {"label": "healthy", "notes": "Inspected; steady operation."}
                ).encode("utf-8")
                request = Request(
                    f"http://127.0.0.1:{server.server_port}/api/motors/label-motor/"
                    f"windows/{window_id}/label",
                    data=body,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urlopen(request) as response:
                    self.assertEqual(response.status, 200)

                with urlopen(
                    f"http://127.0.0.1:{server.server_port}/api/motors/label-motor/"
                    "windows?label=healthy&source=real"
                ) as response:
                    result = json.loads(response.read())
            finally:
                server.shutdown()
                server.server_close()

        self.assertEqual(len(result["windows"]), 1)
        self.assertEqual(result["windows"][0]["label"], "healthy")
        self.assertEqual(result["windows"][0]["sensor_window"]["current_amps"], 0.42)


if __name__ == "__main__":
    unittest.main()

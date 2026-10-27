import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from fastapi.testclient import TestClient

import main


def make_window(amplitude: float = 1.0, temperature: float = 42.0) -> dict[str, object]:
    samples = (amplitude * np.sin(2 * np.pi * 50 * np.arange(128) / 1000)).tolist()
    return {
        "vibration_samples": samples,
        "sample_rate_hz": 1000,
        "rpm": 1500,
        "temperature_c": temperature,
        "current_amps": 4.2,
    }


class EdgeAiApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.data_directory = Path(self.temporary_directory.name)
        self.data_dir_patch = patch.object(main, "DATA_DIR", self.data_directory)
        self.data_dir_patch.start()
        self.client = TestClient(main.app)

    def tearDown(self) -> None:
        self.data_dir_patch.stop()
        self.temporary_directory.cleanup()

    def learn_baseline(self, motor_id: str = "M-48201") -> None:
        response = self.client.post(
            f"/v1/motors/{motor_id}/baseline",
            json={"windows": [make_window() for _ in range(5)]},
        )
        self.assertEqual(response.status_code, 200, response.text)

    def test_health_endpoint(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_analysis_requires_a_healthy_baseline(self) -> None:
        response = self.client.post("/v1/motors/M-48201/analyze", json=make_window())
        self.assertEqual(response.status_code, 409)

    def test_healthy_window_is_normal_and_baseline_persists(self) -> None:
        self.learn_baseline()
        response = self.client.post("/v1/motors/M-48201/analyze", json=make_window())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "normal")
        self.assertTrue((self.data_directory / "M-48201.json").is_file())

    def test_large_vibration_change_is_flagged(self) -> None:
        self.learn_baseline()
        response = self.client.post("/v1/motors/M-48201/analyze", json=make_window(amplitude=2.0))
        self.assertEqual(response.status_code, 200)
        self.assertIn(response.json()["status"], {"warning", "critical"})
        self.assertEqual(response.json()["contributing_feature"], "vibration_rms_mm_s")

    def test_baseline_requires_five_healthy_windows(self) -> None:
        response = self.client.post(
            "/v1/motors/M-48201/baseline",
            json={"windows": [make_window() for _ in range(4)]},
        )
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Annotated

import numpy as np
from fastapi import FastAPI, HTTPException, Path as ApiPath
from pydantic import BaseModel, ConfigDict, Field

MotorId = Annotated[str, ApiPath(pattern=r"^[A-Za-z0-9_-]{1,64}$")]
MIN_HEALTHY_WINDOWS = 5
MAX_SAMPLES_PER_WINDOW = 8192
FEATURE_NAMES = (
    "vibration_rms_mm_s",
    "vibration_peak_to_peak_mm_s",
    "dominant_frequency_hz",
    "temperature_c",
    "current_amps",
)


class SensorWindow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vibration_samples: list[float] = Field(min_length=16, max_length=MAX_SAMPLES_PER_WINDOW)
    sample_rate_hz: float = Field(gt=0, le=100_000)
    rpm: float = Field(ge=0, le=100_000)
    temperature_c: float = Field(ge=0, le=500)
    current_amps: float = Field(ge=0, le=100_000)


class BaselineRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    windows: list[SensorWindow] = Field(min_length=MIN_HEALTHY_WINDOWS, max_length=500)


class FeatureValues(BaseModel):
    vibration_rms_mm_s: float
    vibration_peak_to_peak_mm_s: float
    dominant_frequency_hz: float
    temperature_c: float
    current_amps: float


class BaselineResponse(BaseModel):
    motor_id: str
    healthy_windows: int
    features: dict[str, float]
    saved: bool


class AnalysisResponse(BaseModel):
    motor_id: str
    status: str
    anomaly_score: float
    confidence: str
    explanation: str
    contributing_feature: str
    features: FeatureValues


app = FastAPI(
    title="MotorPulse Edge AI",
    description=(
        "A lightweight, explainable anomaly detector for motor sensor windows. "
        "This prototype identifies deviations from a motor-specific healthy baseline; "
        "it does not diagnose faults or predict failure dates."
    ),
    version="0.1.0",
)
DATA_DIR = Path(os.environ.get("MODEL_DATA_DIR", Path(__file__).parent / "data"))
MOTOR_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def _validate_motor_id(motor_id: str) -> str:
    if not MOTOR_ID_PATTERN.fullmatch(motor_id):
        raise HTTPException(status_code=422, detail="Motor ID must contain only letters, numbers, '_' or '-'.")
    return motor_id


def _baseline_path(motor_id: str) -> Path:
    return DATA_DIR / f"{motor_id}.json"


def _extract_features(window: SensorWindow) -> dict[str, float]:
    samples = np.asarray(window.vibration_samples, dtype=np.float64)
    if not np.all(np.isfinite(samples)):
        raise HTTPException(status_code=422, detail="Vibration samples must be finite numbers.")

    centered_samples = samples - np.mean(samples)
    spectrum = np.abs(np.fft.rfft(centered_samples))
    frequencies = np.fft.rfftfreq(len(centered_samples), d=1 / window.sample_rate_hz)
    dominant_frequency = float(frequencies[1 + np.argmax(spectrum[1:])]) if len(spectrum) > 1 else 0.0

    return {
        "vibration_rms_mm_s": float(np.sqrt(np.mean(np.square(centered_samples)))),
        "vibration_peak_to_peak_mm_s": float(np.ptp(samples)),
        "dominant_frequency_hz": dominant_frequency,
        "temperature_c": window.temperature_c,
        "current_amps": window.current_amps,
    }


def _write_baseline(motor_id: str, features: list[dict[str, float]]) -> dict[str, object]:
    columns = {
        name: np.asarray([window[name] for window in features], dtype=np.float64)
        for name in FEATURE_NAMES
    }
    medians = {name: float(np.median(values)) for name, values in columns.items()}
    mads = {name: float(np.median(np.abs(values - medians[name]))) for name, values in columns.items()}
    baseline = {"healthy_windows": len(features), "median": medians, "mad": mads}

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_path = tempfile.mkstemp(prefix=f".{motor_id}-", dir=DATA_DIR, text=True)
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as file:
            json.dump(baseline, file, allow_nan=False)
        os.replace(temporary_path, _baseline_path(motor_id))
    except Exception:
        if os.path.exists(temporary_path):
            os.unlink(temporary_path)
        raise
    return baseline


def _load_baseline(motor_id: str) -> dict[str, object]:
    path = _baseline_path(motor_id)
    if not path.is_file():
        raise HTTPException(
            status_code=409,
            detail=f"No healthy baseline exists for {motor_id}; submit at least {MIN_HEALTHY_WINDOWS} known-healthy windows first.",
        )
    try:
        baseline = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=500, detail=f"Could not read the saved baseline for {motor_id}.") from error
    return baseline


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "motorpulse-edge-ai"}


@app.post("/v1/motors/{motor_id}/baseline", response_model=BaselineResponse)
def learn_baseline(motor_id: MotorId, request: BaselineRequest) -> BaselineResponse:
    motor_id = _validate_motor_id(motor_id)
    features = [_extract_features(window) for window in request.windows]
    baseline = _write_baseline(motor_id, features)
    return BaselineResponse(
        motor_id=motor_id,
        healthy_windows=int(baseline["healthy_windows"]),
        features=baseline["median"],  # type: ignore[arg-type]
        saved=True,
    )


@app.post("/v1/motors/{motor_id}/analyze", response_model=AnalysisResponse)
def analyze_window(motor_id: MotorId, window: SensorWindow) -> AnalysisResponse:
    motor_id = _validate_motor_id(motor_id)
    baseline = _load_baseline(motor_id)
    current = _extract_features(window)
    medians = baseline["median"]
    mads = baseline["mad"]

    deviations: dict[str, float] = {}
    for name in FEATURE_NAMES:
        median = float(medians[name])  # type: ignore[index]
        mad = float(mads[name])  # type: ignore[index]
        # A small floor handles features with nearly identical healthy readings.
        scale_floor = max(abs(median) * 0.10, 0.05)
        robust_scale = max(1.4826 * mad, scale_floor)
        deviations[name] = abs(current[name] - median) / robust_scale

    contributing_feature = max(deviations, key=deviations.get)
    strongest_deviation = deviations[contributing_feature]
    anomaly_score = round(min(strongest_deviation / 6, 1.0), 3)
    if strongest_deviation >= 6:
        status = "critical"
    elif strongest_deviation >= 3:
        status = "warning"
    else:
        status = "normal"

    explanation = (
        f"{contributing_feature.replace('_', ' ')} is {strongest_deviation:.1f} "
        "robust baseline deviations from this motor's learned healthy range."
    )
    return AnalysisResponse(
        motor_id=motor_id,
        status=status,
        anomaly_score=anomaly_score,
        confidence="baseline",
        explanation=explanation,
        contributing_feature=contributing_feature,
        features=FeatureValues(**current),
    )

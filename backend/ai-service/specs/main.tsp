import "@typespec/http";

using TypeSpec.Http;

@service({ title: "MotorPulse Edge AI API" })
@server("http://localhost:8001", "Local edge AI service")
namespace MotorPulse.EdgeAI;

model AccelerationSample {
  x_m_s2: float64;
  y_m_s2: float64;
  z_m_s2: float64;
}

model SensorWindow {
  acceleration_samples: AccelerationSample[];
  sample_rate_hz: float64;
  rpm?: float64;
  temperature_c: float64;
  current_amps: float64;
}

model HealthyBaselineRequest {
  windows: SensorWindow[];
}

model LearnedBaseline {
  motor_id: string;
  healthy_windows: int32;
  features: Record<float64>;
  saved: boolean;
}

model AnalyzedFeatures {
  acceleration_vector_rms_m_s2: float64;
  acceleration_peak_to_peak_m_s2: float64;
  dominant_frequency_hz: float64;
  temperature_c: float64;
  current_amps: float64;
}

model AnomalyAnalysis {
  motor_id: string;
  status: "normal" | "warning" | "critical";
  anomaly_score: float64;
  confidence: "baseline";
  explanation: string;
  contributing_feature: string;
  features: AnalyzedFeatures;
}

@route("/health")
@tag("Health")
interface Health {
  @get
  check(): {
    status: string;
    service: string;
  };
}

@route("/v1/motors/{motor_id}")
@tag("Edge AI")
interface MotorAnalysis {
  @post
  @route("/baseline")
  learnHealthyBaseline(
    @path motor_id: string,
    @body body: HealthyBaselineRequest,
  ): LearnedBaseline;

  @post
  @route("/analyze")
  analyzeWindow(
    @path motor_id: string,
    @body body: SensorWindow,
  ): AnomalyAnalysis;
}

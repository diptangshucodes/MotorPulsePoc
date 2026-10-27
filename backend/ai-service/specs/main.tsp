import "@typespec/http";

using TypeSpec.Http;

@service({ title: "MotorPulse Edge AI API" })
@server("http://localhost:8001", "Local edge AI service")
namespace MotorPulse.EdgeAI;

model SensorWindow {
  vibrationSamples: float64[];
  sampleRateHz: float64;
  rpm: float64;
  temperatureC: float64;
  currentAmps: float64;
}

model HealthyBaselineRequest {
  windows: SensorWindow[];
}

model LearnedBaseline {
  motorId: string;
  healthyWindows: int32;
  features: Record<float64>;
  saved: boolean;
}

model AnalyzedFeatures {
  vibrationRmsMmS: float64;
  vibrationPeakToPeakMmS: float64;
  dominantFrequencyHz: float64;
  temperatureC: float64;
  currentAmps: float64;
}

model AnomalyAnalysis {
  motorId: string;
  status: "normal" | "warning" | "critical";
  anomalyScore: float64;
  confidence: "baseline";
  explanation: string;
  contributingFeature: string;
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

@route("/v1/motors/{motorId}")
@tag("Edge AI")
interface MotorAnalysis {
  @post
  @route("/baseline")
  learnHealthyBaseline(
    @path motorId: string,
    @body body: HealthyBaselineRequest,
  ): LearnedBaseline;

  @post
  @route("/analyze")
  analyzeWindow(
    @path motorId: string,
    @body body: SensorWindow,
  ): AnomalyAnalysis;
}

import "@typespec/http";

using TypeSpec.Http;

@service({ title: "MotorPulse Fleet Intelligence API" })
@server("http://localhost:5000/api/v1", "Local development server")
namespace MotorPulse;

enum MotorStatus {
  healthy,
  warning,
  critical,
  offline,
}

enum OperatingMode {
  manual,
  scheduled,
  aiAssisted: "ai-assisted",
}

enum AlertSeverity {
  info,
  warning,
  critical,
}

enum WorkOrderPriority {
  low,
  normal,
  high,
  urgent,
}

enum WorkOrderStatus {
  open,
  inProgress: "in-progress",
  completed,
  cancelled,
}

model MotorSummary {
  id: string;
  name: string;
  area: string;
  status: MotorStatus;
  healthScore: int32;
  rpm: int32;
  temperatureC: float64;
  currentAmps: float64;
  vibrationMmPerSec: float64;
  powerKw: float64;
  mode: OperatingMode;
  speedSetpointRpm: int32;
  running: boolean;
  lastSeenAt: string;
}

model Motor extends MotorSummary {
  manufacturer?: string;
  modelNumber?: string;
  ratedPowerKw?: float64;
  installDate?: string;
  gatewayId: string;
}

model TelemetryPoint {
  timestamp: string;
  rpm: int32;
  temperatureC: float64;
  currentAmps: float64;
  vibrationMmPerSec: float64;
  powerKw: float64;
}

model FaultProbability {
  fault: string;
  probability: float64;
}

model MotorDiagnostics {
  motorId: string;
  healthScore: int32;
  anomalyScore: float64;
  confidence: float64;
  estimatedDaysToFailure?: int32;
  modelStatus: string;
  explanation: string;
  faultProbabilities: FaultProbability[];
  analyzedAt: string;
}

model UpdateMotorModeRequest {
  mode: OperatingMode;
}

model UpdateSpeedRequest {
  speedSetpointRpm: int32;
}

model MotorCommandRequest {
  command: "start" | "stop";
  requestedBy: string;
  reason?: string;
  requireConfirmation: boolean;
}

model MotorCommand {
  id: string;
  motorId: string;
  command: "start" | "stop";
  status: "queued" | "accepted" | "rejected" | "completed";
  requestedBy: string;
  requestedAt: string;
  message?: string;
}

model EmergencyStopRequest {
  requestedBy: string;
  reason: string;
  requireConfirmation: boolean;
}

model Alert {
  id: string;
  motorId: string;
  severity: AlertSeverity;
  title: string;
  message: string;
  acknowledged: boolean;
  acknowledgedBy?: string;
  createdAt: string;
}

model AcknowledgeAlertRequest {
  acknowledgedBy: string;
  note?: string;
}

model WorkOrder {
  id: string;
  motorId: string;
  title: string;
  description: string;
  priority: WorkOrderPriority;
  status: WorkOrderStatus;
  recommendedAction?: string;
  sourceAlertId?: string;
  assignedTo?: string;
  dueAt?: string;
  createdAt: string;
}

model CreateWorkOrderRequest {
  motorId: string;
  title: string;
  description: string;
  priority: WorkOrderPriority;
  recommendedAction?: string;
  sourceAlertId?: string;
  assignedTo?: string;
  dueAt?: string;
}

model EnergySummary {
  measuredAt: string;
  totalPowerKw: float64;
  consumptionTodayKwh: float64;
  estimatedCostToday: float64;
  carbonFootprintKgCo2: float64;
  efficiencyDriftPercent: float64;
}

model MotorEnergy {
  motorId: string;
  motorName: string;
  powerKw: float64;
  consumptionTodayKwh: float64;
  estimatedCostToday: float64;
  efficiencyPercent: float64;
  diagnosis?: string;
}

model RoiInputs {
  downtimeCostPerHour: float64;
  plannedRepairCost: float64;
  motorReplacementCost: float64;
  energyTariffPerKwh: float64;
  unplannedRepairCost: float64;
  technicianHourlyRate: float64;
}

model RoiForecastRequest {
  inputs: RoiInputs;
  avoidedDowntimeHours: float64;
  avoidedFailures: int32;
  reportingPeriodMonths: int32;
}

model RoiForecast {
  reportingPeriodMonths: int32;
  avoidedDowntimeHours: float64;
  avoidedDowntimeCost: float64;
  energyWasteSaved: float64;
  maintenanceCostAvoided: float64;
  estimatedTotalSavings: float64;
  estimatedRoiMultiple: float64;
  estimatedPaybackMonths: float64;
}

model Device {
  id: string;
  name: string;
  motorId: string;
  status: "online" | "offline";
  rssiDbm?: int32;
  firmwareVersion: string;
  sampleRateHz: int32;
  lastSeenAt: string;
}

model UpdateDeviceConfigRequest {
  sampleRateHz: int32;
}

@route("/motors")
@tag("Motors")
interface Motors {
  @get
  list(): MotorSummary[];

  @get
  @route("/{motorId}")
  read(@path motorId: string): Motor;

  @get
  @route("/{motorId}/telemetry")
  telemetry(
    @path motorId: string,
    @query from?: string,
    @query to?: string,
    @query interval?: string,
  ): TelemetryPoint[];

  @get
  @route("/{motorId}/diagnostics")
  diagnostics(@path motorId: string): MotorDiagnostics;

  @put
  @route("/{motorId}/mode")
  updateMode(
    @path motorId: string,
    @body body: UpdateMotorModeRequest,
  ): Motor;

  @put
  @route("/{motorId}/speed-setpoint")
  updateSpeed(
    @path motorId: string,
    @body body: UpdateSpeedRequest,
  ): Motor;

  @post
  @route("/{motorId}/commands")
  command(
    @path motorId: string,
    @body body: MotorCommandRequest,
  ): MotorCommand;

  @post
  @route("/emergency-stop")
  emergencyStop(@body body: EmergencyStopRequest): MotorCommand[];
}

@route("/alerts")
@tag("Alerts")
interface Alerts {
  @get
  list(
    @query severity?: AlertSeverity,
    @query acknowledged?: boolean,
  ): Alert[];

  @post
  @route("/{alertId}/acknowledge")
  acknowledge(
    @path alertId: string,
    @body body: AcknowledgeAlertRequest,
  ): Alert;
}

@route("/work-orders")
@tag("Maintenance")
interface WorkOrders {
  @get
  list(
    @query status?: WorkOrderStatus,
    @query motorId?: string,
  ): WorkOrder[];

  @post
  create(@body body: CreateWorkOrderRequest): WorkOrder;

  @get
  @route("/{workOrderId}")
  read(@path workOrderId: string): WorkOrder;
}

@route("/energy")
@tag("Energy")
interface Energy {
  @get
  summary(): EnergySummary;

  @get
  @route("/motors")
  byMotor(): MotorEnergy[];
}

@route("/roi")
@tag("ROI")
interface Roi {
  @post
  @route("/forecast")
  forecast(@body body: RoiForecastRequest): RoiForecast;
}

@route("/devices")
@tag("Devices")
interface Devices {
  @get
  list(): Device[];

  @put
  @route("/{deviceId}/configuration")
  updateConfiguration(
    @path deviceId: string,
    @body body: UpdateDeviceConfigRequest,
  ): Device;
}

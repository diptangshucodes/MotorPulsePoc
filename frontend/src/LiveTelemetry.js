import { useEffect, useMemo, useState } from 'react';

const API_BASE_URL = process.env.REACT_APP_TELEMETRY_API_URL || 'http://127.0.0.1:8002';
const MOTOR_ID = 'motor-01';
const POLL_INTERVAL_MS = 100;
const MOTION_RMS_THRESHOLD_MS2 = 0.12;
const MOTION_PEAK_THRESHOLD_MS2 = 0.3;
const VECTOR_DISPLAY_LIMIT_MS2 = 19.62;

function formatValue(value, digits = 3) {
  return Number.isFinite(value) ? value.toFixed(digits) : '—';
}

function Acceleration3DView({ samples, history }) {
  const view = useMemo(() => {
    if (!samples.length) return null;

    const axes = ['x_ms2', 'y_ms2', 'z_ms2'];
    const acceleration = axes.map((axis) => samples[samples.length - 1][axis]);
    const historyReadings = history
      .map((entry) => entry.acceleration)
      .filter((reading) => reading && axes.every((axis) => Number.isFinite(reading[axis])));
    const recentReadings = (historyReadings.length ? historyReadings : samples).slice(-6);
    const changes = recentReadings.slice(1).map((reading, index) =>
      Math.sqrt(axes.reduce(
        (sum, axis) => sum + (reading[axis] - recentReadings[index][axis]) ** 2,
        0,
      )),
    );
    const changeRms = changes.length
      ? Math.sqrt(changes.reduce((sum, value) => sum + value ** 2, 0) / changes.length)
      : 0;
    const motionDetected = changeRms >= MOTION_RMS_THRESHOLD_MS2
      || Math.max(0, ...changes) >= MOTION_PEAK_THRESHOLD_MS2;
    const magnitude = Math.sqrt(acceleration.reduce((sum, value) => sum + value ** 2, 0));
    const displayScale = magnitude > VECTOR_DISPLAY_LIMIT_MS2
      ? VECTOR_DISPLAY_LIMIT_MS2 / magnitude
      : 1;
    const center = { x: 410, y: 170 };
    const pixelsPerMs2 = 70 / 9.81;
    const project = (x, y, z) => ({
      x: center.x + (x - y) * Math.sqrt(3) / 2 * pixelsPerMs2,
      y: center.y + (x + y) * 0.5 * pixelsPerMs2 - z * pixelsPerMs2,
    });
    const vectorEnd = project(
      acceleration[0] * displayScale,
      acceleration[1] * displayScale,
      acceleration[2] * displayScale,
    );
    return {
      acceleration,
      magnitude,
      motionDetected,
      center,
      vectorEnd,
      axes: [
        { name: 'X', className: 'axis-x', direction: [1, 0, 0] },
        { name: 'Y', className: 'axis-y', direction: [0, 1, 0] },
        { name: 'Z', className: 'axis-z', direction: [0, 0, 1] },
      ].map((axis) => ({
        ...axis,
        positiveEnd: project(
          axis.direction[0] * VECTOR_DISPLAY_LIMIT_MS2,
          axis.direction[1] * VECTOR_DISPLAY_LIMIT_MS2,
          axis.direction[2] * VECTOR_DISPLAY_LIMIT_MS2,
        ),
        negativeEnd: project(
          -axis.direction[0] * VECTOR_DISPLAY_LIMIT_MS2,
          -axis.direction[1] * VECTOR_DISPLAY_LIMIT_MS2,
          -axis.direction[2] * VECTOR_DISPLAY_LIMIT_MS2,
        ),
      })),
    };
  }, [history, samples]);

  if (!view) {
    return <div className="live-chart-empty">Waiting for the first MQTT reading…</div>;
  }

  return (
    <div className="live-3d-view">
      <div className={`telemetry-motion-status ${view.motionDetected ? 'is-moving' : 'is-still'}`} role="status">
        <i />
        {view.motionDetected ? 'Motion detected' : 'Still · noise filtered'}
      </div>
      <svg
        className="live-3d-chart"
        viewBox="0 0 820 360"
        role="img"
        aria-label={`3D acceleration vector on X, Y, and Z axes${view.motionDetected ? ', motion detected' : ', sensor still'}`}
      >
        <defs>
          <marker id="acceleration-vector-arrow" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
            <path d="M0,0 L8,4 L0,8 Z" className="live-3d-vector-arrow" />
          </marker>
        </defs>
        <circle cx={view.center.x} cy={view.center.y} r={70} className="live-3d-reference" />
        {view.axes.map((axis) => (
          <g key={axis.name} className={`live-3d-axis ${axis.className}`}>
            <line
              x1={axis.negativeEnd.x}
              y1={axis.negativeEnd.y}
              x2={axis.positiveEnd.x}
              y2={axis.positiveEnd.y}
            />
            <text x={axis.positiveEnd.x + (axis.name === 'Y' ? -12 : 7)} y={axis.positiveEnd.y - 7}>
              {axis.name}
            </text>
          </g>
        ))}
        <line
          id="acceleration-vector"
          x1={view.center.x}
          y1={view.center.y}
          x2={view.vectorEnd.x}
          y2={view.vectorEnd.y}
          className="live-3d-vector"
          markerEnd="url(#acceleration-vector-arrow)"
        />
        <circle cx={view.center.x} cy={view.center.y} r="4" className="live-3d-origin" />
        <text x={view.center.x + 82} y={view.center.y - 50} className="live-3d-label">1 g reference</text>
        <text x={view.center.x + 82} y={view.center.y - 35} className="live-3d-label">Axes scaled to ±2 g</text>
        <text x={view.center.x} y="344" textAnchor="middle" className="live-chart-axis-title">
          Arrow follows the latest raw acceleration reading
        </text>
        {view.acceleration.map((value, index) => (
          <text key={index} x={260 + index * 100} y="325" textAnchor="middle" className={`live-3d-value ${view.axes[index].className}`}>
            {view.axes[index].name}: {formatValue(value / 9.81, 2)} g
          </text>
        ))}
        <text x="560" y="325" className="live-3d-value">|a|: {formatValue(view.magnitude / 9.81, 2)} g</text>
      </svg>
    </div>
  );
}

function AccelerationHistoryChart({ history }) {
  const points = useMemo(() => {
    if (!history.length) return '';

    const values = history.map((entry) => {
      if (entry.acceleration) {
        const { x_ms2, y_ms2, z_ms2 } = entry.acceleration;
        return Math.sqrt(x_ms2 ** 2 + y_ms2 ** 2 + z_ms2 ** 2);
      }
      return entry.features?.accel_vector_rms_ms2 ?? 0;
    });
    const maximum = Math.max(...values, 0.1);
    return values.map((value, index) => {
      const x = history.length === 1 ? 50 : (index / (history.length - 1)) * 100;
      const y = 52 - (value / maximum) * 44;
      return `${x},${y}`;
    }).join(' ');
  }, [history]);

  return (
    <svg
      className="live-history-chart"
      viewBox="0 0 100 60"
      preserveAspectRatio="none"
      role="img"
      aria-label="Recent raw acceleration magnitude by MQTT reading"
    >
      {[10, 30, 50].map((line) => (
        <line key={line} x1="0" x2="100" y1={line} y2={line} className="live-chart-gridline" />
      ))}
      {points && <polyline points={points} className="live-chart-line axis-vector" />}
      <line x1="0" x2="100" y1="58" y2="58" className="live-chart-axis" />
    </svg>
  );
}

export default function LiveTelemetry() {
  const [snapshot, setSnapshot] = useState(null);
  const [error, setError] = useState('');
  const [updatedAt, setUpdatedAt] = useState(null);

  useEffect(() => {
    let active = true;
    let requestInProgress = false;
    let timeoutId;

    const refresh = async () => {
      if (requestInProgress) return;
      requestInProgress = true;
      let nextDelay = POLL_INTERVAL_MS;
      try {
        const response = await fetch(`${API_BASE_URL}/api/motors/${MOTOR_ID}/telemetry?limit=60`);
        if (!response.ok) {
          throw new Error(`Telemetry service returned HTTP ${response.status}`);
        }
        const data = await response.json();
        if (active) {
          setSnapshot(data);
          setError('');
          setUpdatedAt(new Date());
        }
      } catch (requestError) {
        nextDelay = 3000;
        if (active) {
          setError(requestError.message || 'Could not connect to the telemetry service.');
        }
      } finally {
        requestInProgress = false;
        if (active) timeoutId = window.setTimeout(refresh, nextDelay);
      }
    };

    refresh();
    return () => {
      active = false;
      window.clearTimeout(timeoutId);
    };
  }, []);

  const latest = snapshot?.latest;
  const isFresh = latest && Date.now() - Date.parse(latest.received_at) < 10_000;
  const isBrokerConnected = snapshot?.mqtt_connected;
  const isRealSource = latest?.data_source === 'real';
  const connectionText = error
    ? 'Telemetry API unavailable'
    : isBrokerConnected === false
      ? 'API online · MQTT disconnected'
      : isFresh
        ? 'Receiving live readings'
        : isBrokerConnected
          ? 'Broker connected · waiting for readings'
          : 'Waiting for sensor data';

  return (
    <section className="live-telemetry">
      <header className="live-telemetry-heading">
        <div>
          <span className="eyebrow">DEVICE / MQTT STREAM</span>
          <h1>Live sensor · Motor 01</h1>
          <p>Live ESP32 MPU6050 readings from the local MQTT database.</p>
        </div>
        <div className={`telemetry-connection ${isFresh && isBrokerConnected !== false ? 'is-connected' : ''}`} role="status">
          <i />
          {connectionText}
        </div>
      </header>

      <div className="telemetry-notice">
        <strong>{isRealSource ? 'REAL SOURCE' : 'SIMULATED SOURCE'}</strong>
        <span>
          {isRealSource
            ? 'The logger is marked as a real source. Confirm the sensor is physically attached before using this data operationally.'
            : 'Wokwi data is simulated. This chart shows acceleration, not vibration velocity or a real motor condition.'}
        </span>
      </div>

      {error && (
        <div className="telemetry-error" role="alert">
          <strong>Can’t reach the telemetry API at {API_BASE_URL}.</strong> Keep <code>python mqtt_client.py</code> running in a repository-root terminal.
          <span>{error}</span>
        </div>
      )}

      <div className="telemetry-kpis">
        <article className="panel telemetry-kpi">
          <span>Sample rate</span>
          <strong>{latest ? `${latest.sample_rate_hz} Hz` : '—'}</strong>
        </article>
        <article className="panel telemetry-kpi">
          <span>MQTT payload</span>
          <strong>{latest ? 'Single raw reading' : '—'}</strong>
        </article>
        <article className="panel telemetry-kpi">
          <span>Acceleration magnitude</span>
          <strong>{latest?.samples?.length ? `${formatValue(Math.sqrt(
            latest.samples[latest.samples.length - 1].x_ms2 ** 2
            + latest.samples[latest.samples.length - 1].y_ms2 ** 2
            + latest.samples[latest.samples.length - 1].z_ms2 ** 2,
          ))} m/s²` : '—'}</strong>
        </article>
        <article className="panel telemetry-kpi">
          <span>Last raw reading</span>
          <strong>{latest ? new Date(latest.received_at).toLocaleTimeString() : '—'}</strong>
          <small>{updatedAt ? `Refreshed ${updatedAt.toLocaleTimeString()}` : 'Polling local service'}</small>
        </article>
      </div>

      <article className="panel telemetry-chart-panel">
        <div className="panel-title">
          <div>
            <h2>3D acceleration vector</h2>
            <span className="subtle">The arrow follows the latest raw X, Y, and Z reading with no window averaging</span>
          </div>
          <div className="telemetry-legend">
            <span className="axis-x">X</span>
            <span className="axis-y">Y</span>
            <span className="axis-z">Z</span>
          </div>
        </div>
        <Acceleration3DView samples={latest?.samples || []} history={snapshot?.history || []} />
      </article>

      <article className="panel telemetry-chart-panel">
        <div className="panel-title">
          <div>
            <h2>Acceleration trend</h2>
            <span className="subtle">Raw acceleration magnitude from recent MQTT readings · m/s²</span>
          </div>
          <span className="chart-live"><i className="live-dot" /> POLLING</span>
        </div>
        <AccelerationHistoryChart history={snapshot?.history || []} />
        <div className="telemetry-history-caption">
          <span>{snapshot?.history?.length || 0} readings</span>
          <span>Updates every {POLL_INTERVAL_MS / 1000} seconds</span>
        </div>
      </article>

      <div className="telemetry-axis-metrics">
        {[
          ['X axis', 'x_ms2'],
          ['Y axis', 'y_ms2'],
          ['Z axis', 'z_ms2'],
        ].map(([axis, sampleKey]) => {
          const currentSample = latest?.samples?.[latest.samples.length - 1];
          const previousHistory = snapshot?.history || [];
          const previousSample = previousHistory.length > 1
            ? previousHistory[previousHistory.length - 2].acceleration
            : null;
          const currentValue = currentSample?.[sampleKey];
          const previousValue = previousSample?.[sampleKey];
          return (
            <article className="panel telemetry-axis-card" key={axis}>
              <h2>{axis}</h2>
              <p>Raw acceleration <strong>{Number.isFinite(currentValue) ? `${formatValue(currentValue)} m/s²` : '—'}</strong></p>
              <p>Change since previous reading <strong>{Number.isFinite(currentValue) && Number.isFinite(previousValue) ? `${formatValue(currentValue - previousValue)} m/s²` : '—'}</strong></p>
            </article>
          );
        })}
      </div>
    </section>
  );
}

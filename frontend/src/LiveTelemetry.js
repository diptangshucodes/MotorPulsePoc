import { useEffect, useMemo, useState } from 'react';

const API_BASE_URL = process.env.REACT_APP_TELEMETRY_API_URL || 'http://localhost:8002';
const MOTOR_ID = 'motor-01';
const POLL_INTERVAL_MS = 1500;

function formatValue(value, digits = 3) {
  return Number.isFinite(value) ? value.toFixed(digits) : '—';
}

function AccelerationChart({ samples }) {
  const chart = useMemo(() => {
    if (!samples.length) return null;

    const values = samples.flatMap((sample) => [sample.x_ms2, sample.y_ms2, sample.z_ms2]);
    let min = Math.min(...values);
    let max = Math.max(...values);
    const padding = Math.max((max - min) * 0.12, Math.max(Math.abs(min), Math.abs(max)) * 0.025, 0.1);
    min -= padding;
    max += padding;

    const left = 58;
    const right = 790;
    const top = 18;
    const bottom = 220;
    const duration = Math.max(samples[samples.length - 1].offset_s, 0.001);
    const x = (offset) => left + (offset / duration) * (right - left);
    const y = (value) => bottom - ((value - min) / (max - min)) * (bottom - top);
    const line = (axis) => samples
      .map((sample) => `${x(sample.offset_s)},${y(sample[axis])}`)
      .join(' ');

    return {
      min,
      max,
      top,
      bottom,
      left,
      right,
      middle: (top + bottom) / 2,
      xLabels: [0, duration / 2, duration],
      x,
      y,
      lines: [
        { axis: 'x_ms2', label: 'X', className: 'axis-x' },
        { axis: 'y_ms2', label: 'Y', className: 'axis-y' },
        { axis: 'z_ms2', label: 'Z', className: 'axis-z' },
      ].map((axis) => ({ ...axis, points: line(axis.axis) })),
    };
  }, [samples]);

  if (!chart) {
    return <div className="live-chart-empty">Waiting for the first MQTT sample window…</div>;
  }

  return (
    <svg
      className="live-acceleration-chart"
      viewBox="0 0 820 260"
      role="img"
      aria-label="Latest X, Y, and Z acceleration samples in meters per second squared"
    >
      {[chart.top, chart.middle, chart.bottom].map((lineY) => (
        <line key={lineY} x1={chart.left} x2={chart.right} y1={lineY} y2={lineY} className="live-chart-gridline" />
      ))}
      {[chart.max, (chart.max + chart.min) / 2, chart.min].map((value, index) => {
        const labelY = [chart.top + 4, chart.middle + 4, chart.bottom + 4][index];
        return <text key={index} x={chart.left - 9} y={labelY} textAnchor="end" className="live-chart-label">{formatValue(value, 2)}</text>;
      })}
      <line x1={chart.left} x2={chart.right} y1={chart.bottom} y2={chart.bottom} className="live-chart-axis" />
      {chart.lines.map((line) => (
        <polyline key={line.axis} points={line.points} className={`live-chart-line ${line.className}`} />
      ))}
      {chart.xLabels.map((label, index) => (
        <text
          key={index}
          x={chart.x(label)}
          y="244"
          textAnchor={index === 0 ? 'start' : index === chart.xLabels.length - 1 ? 'end' : 'middle'}
          className="live-chart-label"
        >
          {label.toFixed(2)} s
        </text>
      ))}
      <text x="424" y="258" textAnchor="middle" className="live-chart-axis-title">Time within latest sample window</text>
    </svg>
  );
}

function AccelerationHistoryChart({ history }) {
  const points = useMemo(() => {
    if (!history.length) return '';

    const values = history.map((entry) => entry.features.accel_vector_rms_ms2);
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
      aria-label="Recent vector dynamic acceleration RMS by sample window"
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

    const refresh = async () => {
      if (requestInProgress) return;
      requestInProgress = true;
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
        if (active) setError(requestError.message || 'Could not connect to the telemetry service.');
      } finally {
        requestInProgress = false;
      }
    };

    refresh();
    const intervalId = window.setInterval(refresh, POLL_INTERVAL_MS);
    return () => {
      active = false;
      window.clearInterval(intervalId);
    };
  }, []);

  const latest = snapshot?.latest;
  const isFresh = latest && Date.now() - Date.parse(latest.received_at) < 10_000;
  const features = latest?.features;
  const isRealSource = latest?.data_source === 'real';

  return (
    <section className="live-telemetry">
      <header className="live-telemetry-heading">
        <div>
          <span className="eyebrow">DEVICE / MQTT STREAM</span>
          <h1>Live sensor · Motor 01</h1>
          <p>ESP32 MPU6050 acceleration windows from the local MQTT database.</p>
        </div>
        <div className={`telemetry-connection ${isFresh ? 'is-connected' : ''}`} role="status">
          <i />
          {isFresh ? 'Receiving live windows' : 'Waiting for sensor data'}
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
          <strong>Telemetry API unavailable.</strong> Start <code>python mqtt_client.py</code> from the repository root.
          <span>{error}</span>
        </div>
      )}

      <div className="telemetry-kpis">
        <article className="panel telemetry-kpi">
          <span>Sample rate</span>
          <strong>{latest ? `${latest.sample_rate_hz} Hz` : '—'}</strong>
        </article>
        <article className="panel telemetry-kpi">
          <span>Samples per window</span>
          <strong>{latest?.sample_count ?? '—'}</strong>
        </article>
        <article className="panel telemetry-kpi">
          <span>Vector dynamic acceleration RMS</span>
          <strong>{features ? `${formatValue(features.accel_vector_rms_ms2)} m/s²` : '—'}</strong>
        </article>
        <article className="panel telemetry-kpi">
          <span>Last MQTT window</span>
          <strong>{latest ? new Date(latest.received_at).toLocaleTimeString() : '—'}</strong>
          <small>{updatedAt ? `Refreshed ${updatedAt.toLocaleTimeString()}` : 'Polling local service'}</small>
        </article>
      </div>

      <article className="panel telemetry-chart-panel">
        <div className="panel-title">
          <div>
            <h2>Latest acceleration waveform</h2>
            <span className="subtle">128 raw readings · X, Y, and Z · m/s²</span>
          </div>
          <div className="telemetry-legend">
            <span className="axis-x">X</span>
            <span className="axis-y">Y</span>
            <span className="axis-z">Z</span>
          </div>
        </div>
        <AccelerationChart samples={latest?.samples || []} />
      </article>

      <article className="panel telemetry-chart-panel">
        <div className="panel-title">
          <div>
            <h2>Acceleration trend</h2>
            <span className="subtle">Mean-centered vector RMS for recent MQTT windows · m/s²</span>
          </div>
          <span className="chart-live"><i className="live-dot" /> POLLING</span>
        </div>
        <AccelerationHistoryChart history={snapshot?.history || []} />
        <div className="telemetry-history-caption">
          <span>{snapshot?.history?.length || 0} windows</span>
          <span>Updates every {POLL_INTERVAL_MS / 1000} seconds</span>
        </div>
      </article>

      <div className="telemetry-axis-metrics">
        {[
          ['X axis', 'accel_x_mean_ms2', 'accel_x_rms_ms2', 'accel_x_peak_to_peak_ms2'],
          ['Y axis', 'accel_y_mean_ms2', 'accel_y_rms_ms2', 'accel_y_peak_to_peak_ms2'],
          ['Z axis', 'accel_z_mean_ms2', 'accel_z_rms_ms2', 'accel_z_peak_to_peak_ms2'],
        ].map(([axis, meanKey, rmsKey, peakKey]) => (
          <article className="panel telemetry-axis-card" key={axis}>
            <h2>{axis}</h2>
            <p>Mean acceleration <strong>{features ? `${formatValue(features[meanKey])} m/s²` : '—'}</strong></p>
            <p>Dynamic RMS <strong>{features ? `${formatValue(features[rmsKey])} m/s²` : '—'}</strong></p>
            <p>Peak-to-peak <strong>{features ? `${formatValue(features[peakKey])} m/s²` : '—'}</strong></p>
          </article>
        ))}
      </div>
    </section>
  );
}

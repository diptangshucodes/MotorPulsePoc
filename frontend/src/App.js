import { useEffect, useMemo, useState } from 'react';
import './App.css';

const initialMotors = [
  { id: 'M-48201', name: 'Pump Motor A1', area: 'Production line · North', status: 'healthy', health: 98, rpm: 1747, temp: 42.8, current: 45.3, vibration: 1.2, power: 2.45, mode: 'AI-assisted', speed: 1745, running: true },
  { id: 'M-22091', name: 'Conveyor B-Left', area: 'Packaging · Line 2', status: 'warning', health: 72, rpm: 1419, temp: 65.1, current: 58.5, vibration: 4.8, power: 3.18, mode: 'Manual', speed: 1400, running: true },
  { id: 'M-44823', name: 'Fan Unit Main', area: 'HVAC · Roof', status: 'critical', health: 34, rpm: 2098, temp: 88.3, current: 72.3, vibration: 12.5, power: 4.62, mode: 'Manual', speed: 0, running: false },
  { id: 'M-33210', name: 'Mill Drive 01', area: 'Production line · South', status: 'healthy', health: 100, rpm: 852, temp: 38.1, current: 32.6, vibration: 0.8, power: 1.94, mode: 'AI-assisted', speed: 850, running: true },
  { id: 'M-39014', name: 'Mixer X-4', area: 'Batching · Cell 4', status: 'offline', health: 0, rpm: 0, temp: 24.2, current: 0, vibration: 0, power: 0, mode: 'Manual', speed: 0, running: false },
  { id: 'M-48211', name: 'Conveyor A-Right', area: 'Packaging · Line 1', status: 'healthy', health: 92, rpm: 1414, temp: 44.2, current: 42.8, vibration: 1.5, power: 2.21, mode: 'AI-assisted', speed: 1410, running: true },
  { id: 'M-11903', name: 'Compressor 12', area: 'Utilities · Plant room', status: 'warning', health: 68, rpm: 2998, temp: 72.3, current: 122.5, vibration: 5.2, power: 8.36, mode: 'Scheduled', speed: 2900, running: true },
  { id: 'M-48202', name: 'Pump Motor A2', area: 'Production line · North', status: 'healthy', health: 96, rpm: 1742, temp: 40.5, current: 44.8, vibration: 1.1, power: 2.38, mode: 'AI-assisted', speed: 1740, running: true },
  { id: 'M-18921', name: 'Ventilation 1.1', area: 'HVAC · East wing', status: 'healthy', health: 99, rpm: 1201, temp: 32.6, current: 18.6, vibration: 0.6, power: 1.12, mode: 'Scheduled', speed: 1200, running: true },
  { id: 'M-33211', name: 'Mill Drive 02', area: 'Production line · South', status: 'healthy', health: 97, rpm: 850, temp: 39.1, current: 31.9, vibration: 0.9, power: 1.88, mode: 'AI-assisted', speed: 850, running: true },
];

const initialAlerts = [
  { id: 'ALT-1048', severity: 'critical', title: 'High vibration alarm', motorId: 'M-44823', message: 'Vibration RMS exceeded 12.5 mm/s. AI detects an 88% probability of bearing failure within 48 hours.', age: '2 min ago', acknowledged: false },
  { id: 'ALT-1047', severity: 'warning', title: 'Misalignment detected', motorId: 'M-22091', message: 'Harmonic peak at 2x RPM is trending upward (+40%) over 3 days.', age: '15 min ago', acknowledged: false },
  { id: 'ALT-1046', severity: 'warning', title: 'Efficiency drift', motorId: 'M-11903', message: 'Current draw is 8% above the healthy baseline for this operating load.', age: '1 hr ago', acknowledged: true },
];

const navItems = [
  { id: 'overview', label: 'Fleet overview', icon: 'grid' },
  { id: 'detail', label: 'Motor detail', icon: 'pulse' },
  { id: 'control', label: 'Control panel', icon: 'sliders' },
  { id: 'alerts', label: 'Alerts & maintenance', icon: 'bell' },
  { id: 'energy', label: 'Energy', icon: 'bolt' },
  { id: 'roi', label: 'ROI savings', icon: 'chart' },
];

function Icon({ name, size = 17 }) {
  const paths = {
    grid: <><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" /></>,
    pulse: <><path d="M3 12h3l3-8 5 16 3-8h4" /><circle cx="12" cy="12" r="9" /></>,
    sliders: <><path d="M4 21v-7m0-4V3m8 18v-9m0-4V3m8 18v-5m0-4V3M2 14h4m4-6h4m4 8h4" /></>,
    bell: <><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9" /><path d="M10 21h4" /></>,
    bolt: <path d="m13 2-3 9H5l6 11 3-9h5L13 2Z" />,
    chart: <><path d="M3 3v18h18" /><path d="m7 14 4-4 4 3 6-7" /></>,
    chevron: <path d="m9 18 6-6-6-6" />,
    plus: <><path d="M12 5v14M5 12h14" /></>,
    shield: <><path d="M12 22s8-4 8-11V5l-8-3-8 3v6c0 7 8 11 8 11Z" /><path d="m9 12 2 2 4-4" /></>,
    settings: <><circle cx="12" cy="12" r="3" /><path d="m19.4 15 .1.1a1.7 1.7 0 1 1-2.4 2.4l-.1-.1a1.7 1.7 0 0 0-2.9 1.2v.2a1.7 1.7 0 1 1-3.4 0v-.2a1.7 1.7 0 0 0-2.9-1.2l-.1.1a1.7 1.7 0 1 1-2.4-2.4l.1-.1a1.7 1.7 0 0 0-1.2-2.9H4a1.7 1.7 0 1 1 0-3.4h.2a1.7 1.7 0 0 0 1.2-2.9l-.1-.1a1.7 1.7 0 1 1 2.4-2.4l.1.1a1.7 1.7 0 0 0 2.9-1.2V4a1.7 1.7 0 1 1 3.4 0v.2a1.7 1.7 0 0 0 2.9 1.2l.1-.1a1.7 1.7 0 1 1 2.4 2.4l-.1.1a1.7 1.7 0 0 0 1.2 2.9h.2a1.7 1.7 0 1 1 0 3.4h-.2a1.7 1.7 0 0 0-1.2.9Z" /></>,
    close: <><path d="m18 6-12 12M6 6l12 12" /></>,
    check: <path d="m5 12 4 4L19 6" />,
    spark: <><path d="m12 3 1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3Z" /><path d="m19 14 .9 2.1L22 17l-2.1.9L19 20l-.9-2.1L16 17l2.1-.9L19 14Z" /></>,
  };
  return <svg aria-hidden="true" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">{paths[name] || paths.grid}</svg>;
}

function TrendChart({ color = '#119b8e', secondaryColor, height = 170, points = 36, seed = 0 }) {
  const makePoints = (offset, amplitude) => Array.from({ length: points }, (_, index) => {
    const trend = Math.sin((index + seed) * 0.72) * amplitude * 0.34;
    const noise = Math.sin((index + seed * 2) * 1.83) * amplitude * 0.16;
    return `${(index / (points - 1)) * 100},${50 - trend - noise + offset}`;
  }).join(' ');
  return (
    <svg className="trend-chart" viewBox="0 0 100 60" preserveAspectRatio="none" style={{ height }} role="img" aria-label="Telemetry trend chart">
      {[10, 30, 50].map((line) => <line key={line} x1="0" x2="100" y1={line} y2={line} className="chart-gridline" />)}
      <polyline points={makePoints(0, 60)} fill="none" stroke={color} strokeWidth="1.4" vectorEffect="non-scaling-stroke" />
      {secondaryColor && <polyline points={makePoints(13, 48)} fill="none" stroke={secondaryColor} strokeWidth="1.2" vectorEffect="non-scaling-stroke" />}
      <line x1="0" x2="100" y1="59" y2="59" className="chart-axis" />
    </svg>
  );
}

function SectionTitle({ eyebrow, title, description, actions }) {
  return <div className="section-title"><div>{eyebrow && <span className="eyebrow">{eyebrow}</span>}<h1>{title}</h1>{description && <p>{description}</p>}</div>{actions && <div className="title-actions">{actions}</div>}</div>;
}

function KpiCard({ label, value, suffix, trend, tone = 'teal', icon }) {
  return <article className={`kpi-card kpi-${tone}`}><div className="kpi-top"><span>{label}</span>{icon && <span className="kpi-icon"><Icon name={icon} size={16} /></span>}</div><div className="kpi-value">{value}<small>{suffix}</small></div>{trend && <div className="kpi-trend">{trend}</div>}</article>;
}

function MotorCard({ motor, onClick }) {
  const statusLabel = { healthy: 'Healthy', warning: 'Warning', critical: 'Critical', offline: 'Offline' }[motor.status];
  return (
    <button className={`motor-card status-${motor.status}`} onClick={onClick} aria-label={`View ${motor.name} details`}>
      <div className="motor-card-head"><span className="motor-name">{motor.name}</span><span className={`status-pill status-pill-${motor.status}`}><i />{statusLabel}</span></div>
      <span className="motor-id">{motor.id}</span>
      <div className="motor-metrics"><div><label>RPM</label><strong>{motor.rpm.toLocaleString()}</strong></div><div><label>Temp</label><strong>{motor.temp.toFixed(1)}<small>°C</small></strong></div><div><label>Vibration</label><strong>{motor.vibration.toFixed(1)}<small> mm/s</small></strong></div><div><label>Current</label><strong>{motor.current.toFixed(1)}<small> A</small></strong></div></div>
      <div className="health-line"><span>Health score</span><strong>{motor.status === 'offline' ? '—' : `${motor.health}%`}</strong></div>
      <div className="health-track"><span style={{ width: `${motor.health}%` }} /></div>
    </button>
  );
}

function Modal({ title, children, onClose, footer }) {
  useEffect(() => {
    const onKeyDown = (event) => { if (event.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [onClose]);
  return <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}><section className="modal" role="dialog" aria-modal="true" aria-labelledby="modal-title"><div className="modal-head"><h2 id="modal-title">{title}</h2><button className="icon-button" onClick={onClose} aria-label="Close dialog"><Icon name="close" /></button></div><div className="modal-content">{children}</div>{footer && <div className="modal-footer">{footer}</div>}</section></div>;
}

function App() {
  const [motors, setMotors] = useState(initialMotors);
  const [alerts, setAlerts] = useState(initialAlerts);
  const [auditLog, setAuditLog] = useState([
    { time: '10:18:42', message: 'Marcus Chen modified speed setpoint for Pump Motor A1 (1,200 → 1,745 RPM)', actor: 'M. Chen · Operator', system: false },
    { time: '10:02:15', message: 'AI agent initiated safe derate on Fan Unit Main due to vibration alarm', actor: 'System · AI', system: true },
    { time: '08:18:08', message: 'Scheduled task: Shift Start Command executed globally', actor: 'Scheduler', system: false },
  ]);
  const [screen, setScreen] = useState('overview');
  const [selectedId, setSelectedId] = useState('M-48201');
  const [simulating, setSimulating] = useState(true);
  const [modal, setModal] = useState(null);
  const [toast, setToast] = useState('');
  const [workOrders, setWorkOrders] = useState(4);
  const [roi, setRoi] = useState({ downtime: 1500, planned: 850, replacement: 12000, tariff: 0.12, unplanned: 4500, technician: 85 });
  const [roiSaved, setRoiSaved] = useState(false);
  const [tick, setTick] = useState(0);
  const selectedMotor = motors.find((motor) => motor.id === selectedId) || motors[0];
  const healthyCount = motors.filter((motor) => motor.status === 'healthy').length;
  const warningCount = motors.filter((motor) => motor.status === 'warning').length;
  const criticalCount = motors.filter((motor) => motor.status === 'critical').length;
  const onlineCount = motors.filter((motor) => motor.status !== 'offline').length;
  const energyToday = motors.reduce((sum, motor) => sum + motor.power, 0) * 7.1;
  const savings = 4290 + tick * 8;
  const activeAlerts = alerts.filter((alert) => !alert.acknowledged).length;

  useEffect(() => {
    if (!simulating) return undefined;
    const interval = window.setInterval(() => {
      setTick((value) => value + 1);
      setMotors((current) => current.map((motor) => {
        if (motor.status === 'offline' || !motor.running) return motor;
        const variation = () => (Math.random() - 0.5);
        const nextTemp = Math.max(20, motor.temp + variation() * 1.2);
        const nextVibration = Math.max(0.1, motor.vibration + variation() * 0.34);
        return { ...motor, rpm: Math.max(0, Math.round(motor.speed + variation() * 12)), temp: Number(nextTemp.toFixed(1)), vibration: Number(nextVibration.toFixed(1)), current: Math.max(0, Number((motor.current + variation() * 0.7).toFixed(1))) };
      }));
    }, 2500);
    return () => window.clearInterval(interval);
  }, [simulating]);

  useEffect(() => {
    if (!toast) return undefined;
    const timeout = window.setTimeout(() => setToast(''), 3200);
    return () => window.clearTimeout(timeout);
  }, [toast]);

  const goToMotor = (id) => { setSelectedId(id); setScreen('detail'); };
  const updateMotor = (id, patch) => setMotors((current) => current.map((motor) => motor.id === id ? { ...motor, ...patch } : motor));
  const confirmMotorCommand = (motor, action) => setModal({ type: 'motor-command', motorId: motor.id, action });
  const confirmEmergencyStop = () => setModal({ type: 'emergency-stop' });
  const executeModalAction = () => {
    if (modal?.type === 'motor-command') {
      const motor = motors.find((item) => item.id === modal.motorId);
      const running = modal.action === 'start';
      updateMotor(modal.motorId, { running, rpm: running ? motor.speed : 0 });
      setAuditLog((current) => [{ time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }), message: `Operator ${modal.action} command sent to ${motor.name}`, actor: 'Marcus Chen · Operator', system: false }, ...current]);
      setToast(`${motor.name} ${running ? 'start' : 'stop'} command queued`);
    } else if (modal?.type === 'emergency-stop') {
      setMotors((current) => current.map((motor) => motor.status === 'offline' ? motor : { ...motor, running: false, rpm: 0 }));
      setAuditLog((current) => [{ time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }), message: `Emergency stop sent to all ${onlineCount} connected motors`, actor: 'Marcus Chen · Operator', system: true }, ...current]);
      setToast('Emergency stop sent to all online motors');
    } else if (modal?.type === 'work-order') {
      setWorkOrders((count) => count + 1);
      setToast('Work order created and added to maintenance queue');
    }
    setModal(null);
  };
  const acknowledge = (id) => setAlerts((current) => current.map((alert) => alert.id === id ? { ...alert, acknowledged: true } : alert));
  const setFault = (fault) => {
    const motor = selectedMotor;
    const impact = fault === 'overheat' ? { temp: 87.6, status: 'critical', health: 31 } : { vibration: fault === 'bearing' ? 10.8 : 7.6, status: fault === 'imbalance' ? 'warning' : 'critical', health: fault === 'imbalance' ? 61 : 39 };
    updateMotor(motor.id, impact);
    const newAlert = { id: `ALT-${1049 + alerts.length}`, severity: impact.status, title: `${fault === 'overheat' ? 'Temperature' : fault === 'bearing' ? 'Bearing wear' : 'Imbalance'} detected`, motorId: motor.id, message: `Demo fault injection is affecting ${motor.name}. Review condition and plan maintenance.`, age: 'Just now', acknowledged: false };
    setAlerts((current) => [newAlert, ...current]);
    setAuditLog((current) => [{ time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }), message: `Expo demo fault injected: ${fault} on ${motor.name}`, actor: 'Demo simulator', system: true }, ...current]);
    setToast(`Injected ${fault} fault into ${motor.name}`);
  };
  const updateRoi = (key, value) => { setRoi((current) => ({ ...current, [key]: Number(value) || 0 })); setRoiSaved(false); };
  const roiAnnual = Math.round(156 * roi.downtime * 0.78 + (roi.unplanned - roi.planned) * 12 + roi.technician * 96 + roi.tariff * 365 * 220);
  const titleMap = useMemo(() => Object.fromEntries(navItems.map((item) => [item.id, item.label])), []);

  const renderOverview = () => (
    <>
      <SectionTitle eyebrow="MONITORING / FLEET" title="Fleet overview" description="A live view of equipment health across your production floor." actions={<><span className="updated-note"><i className="live-dot" /> Live · updated just now</span><button className="button button-outline" onClick={() => setToast('Fleet report exported')}><Icon name="chart" size={15} /> Export report</button></>} />
      <div className="kpi-grid six">
        <KpiCard label="Motors online" value={`${onlineCount}`} suffix="/ 10" tone="blue" trend="All gateways connected" />
        <KpiCard label="Healthy" value={healthyCount.toString().padStart(2, '0')} tone="teal" trend="Within normal limits" />
        <KpiCard label="Warning" value={warningCount.toString().padStart(2, '0')} tone="amber" trend="Needs attention" />
        <KpiCard label="Critical" value={criticalCount.toString().padStart(2, '0')} tone="red" trend="Action recommended" />
        <KpiCard label="Energy today" value={energyToday.toFixed(1)} suffix="kWh" tone="blue" trend="↓ 4.8% vs. yesterday" />
        <KpiCard label="$ saved" value={`$${savings.toLocaleString()}`} tone="teal" trend="This month · +12.4%" />
      </div>
      <div className="section-heading"><div><h2>Main production line</h2><p>10 monitored assets · select a motor to inspect</p></div><button className="icon-button" aria-label="Filter motors" onClick={() => setToast('Showing all production assets')}><Icon name="settings" /></button></div>
      <div className="motor-grid">{motors.map((motor) => <MotorCard key={motor.id} motor={motor} onClick={() => goToMotor(motor.id)} />)}</div>
      <div className="insight-strip"><div className="insight-icon"><Icon name="spark" /></div><div><strong>AI fleet insight</strong><p>2 assets show early signs of degradation. Reviewing them now could prevent an estimated 11 hours of unplanned downtime.</p></div><button className="text-button" onClick={() => setScreen('alerts')}>Review alerts <Icon name="chevron" size={15} /></button></div>
    </>
  );

  const renderDetail = () => (
    <>
      <SectionTitle eyebrow="ASSET / LIVE DIAGNOSTICS" title={selectedMotor.name} description={`${selectedMotor.id} · ${selectedMotor.area}`} actions={<><span className={`status-pill status-pill-${selectedMotor.status}`}><i />{selectedMotor.status}</span><button className="button button-primary" onClick={() => setScreen('control')}><Icon name="sliders" size={15} /> Control panel</button></>} />
      <div className="detail-overview">
        <article className="panel ai-summary"><div className="panel-title"><span className="panel-icon"><Icon name="spark" size={15} /></span><div><h2>AI predictive analysis</h2><span className="subtle">Condition model · last analysis 12 sec ago</span></div><span className="confidence-tag">94% confidence</span></div>
          <p className="ai-explanation">Vibration at <strong>2x RPM is up 40% over 3 days</strong>, which is consistent with shaft misalignment. Bearing temperature remains stable. Plan a visual inspection of coupling alignment within the next 2 days.</p>
          <div className="detail-mini-kpis"><div><span>Est. days to failure</span><strong className="text-red">42 days</strong></div><div><span>Anomaly score</span><strong>0.12 <small>/ 1.00</small></strong></div><div><span>Model status</span><strong className="text-teal">Optimal</strong></div></div>
        </article>
        <article className="panel health-panel"><span className="eyebrow">OVERALL HEALTH SCORE</span><div className="health-gauge" style={{ '--gauge-value': `${selectedMotor.health}%` }}><div><strong>{selectedMotor.health}</strong><span>/100</span></div></div><div className="health-label"><span className={`status-pill status-pill-${selectedMotor.status}`}><i />{selectedMotor.status}</span></div></article>
        <article className="panel fault-panel"><div className="panel-title"><div><h2>Fault probability</h2><span className="subtle">Predicted failure modes</span></div></div>{[['Imbalance', 8], ['Misalignment', 62], ['Bearing wear', 12], ['Mechanical looseness', 4]].map(([label, value]) => <div className="probability-row" key={label}><div><span>{label}</span><strong>{value}%</strong></div><div className="probability-track"><span style={{ width: `${value}%` }} /></div></div>)}</article>
      </div>
      <div className="chart-grid detail-charts">
        <article className="panel chart-panel"><div className="panel-title"><div><h2>Vibration & temperature</h2><span className="subtle">Last 60 minutes · live telemetry</span></div><div className="legend"><span><i className="legend-teal" /> Vibration</span><span><i className="legend-amber" /> Temp</span></div></div><TrendChart secondaryColor="#e9a23b" seed={tick + 4} /><div className="chart-xlabels"><span>60m ago</span><span>45m</span><span>30m</span><span>15m</span><span>Now</span></div></article>
        <article className="panel chart-panel"><div className="panel-title"><div><h2>Current · phase analysis</h2><span className="subtle">Three-phase motor current (A)</span></div><span className="chart-live"><i className="live-dot" /> LIVE</span></div><TrendChart color="#159d90" secondaryColor="#5987d5" seed={tick + 8} /><div className="chart-xlabels"><span>0</span><span>10</span><span>20</span><span>30</span><span>40 sec</span></div></article>
        <article className="panel chart-panel"><div className="panel-title"><div><h2>FFT spectrum analysis</h2><span className="subtle">Frequency (Hz) · peaks normalized</span></div><span className="subtle">Markers at 1x, 2x, 3x RPM</span></div><div className="spectrum-chart">{[18, 30, 20, 43, 26, 34, 20, 61, 26, 28, 22, 38, 17, 27, 16, 20, 14, 25, 16, 12, 19, 13, 17, 11, 15, 10, 13, 9].map((height, index) => <span key={index} style={{ height: `${height}%` }} />)}<i className="fft-marker marker-one">1x</i><i className="fft-marker marker-two">2x</i><i className="fft-marker marker-three">3x</i></div><div className="chart-xlabels"><span>0</span><span>200</span><span>400</span><span>600</span><span>800 Hz</span></div></article>
        <article className="panel chart-panel"><div className="panel-title"><div><h2>Frequency waterfall</h2><span className="subtle">Vibration spectrum · last 30 minutes</span></div><span className="subtle">30 min</span></div><div className="waterfall">{Array.from({ length: 10 }, (_, row) => <div className="waterfall-row" key={row}>{Array.from({ length: 24 }, (_, column) => { const intensity = Math.abs(Math.sin((row + 2) * (column + tick / 5 + 1)) * Math.cos(column * 0.5)); return <i key={column} style={{ opacity: 0.2 + intensity * 0.8, background: intensity > 0.65 ? '#0b958d' : intensity > 0.36 ? '#75c6bb' : '#d3e8e4' }} />; })}</div>)}</div><div className="chart-xlabels"><span>-30m</span><span>-20m</span><span>-10m</span><span>Now</span></div></article>
      </div>
      <article className="panel event-panel"><div className="panel-title"><div><h2>Recent events & command log</h2><span className="subtle">A time-ordered view of asset activity</span></div><button className="text-button" onClick={() => setScreen('alerts')}>View all <Icon name="chevron" size={15} /></button></div><div className="timeline">{auditLog.slice(0, 3).map((event) => <div className="timeline-event" key={`${event.time}-${event.message}`}><i className={`event-dot ${event.system ? 'event-red' : ''}`} /><div><strong>{event.message}</strong><p>{event.actor}</p></div><time>{event.time}</time></div>)}</div></article>
      <article className="panel demo-fault-panel"><div><span className="eyebrow">EXPO DEMO TOOLS</span><h2>Inject a fault to demonstrate predictive alerts</h2><p>Simulated faults update this motor's telemetry, health score, and alert feed. No hardware commands are sent.</p></div><div className="fault-buttons"><button className="button button-outline button-small" onClick={() => setFault('imbalance')}>Inject imbalance</button><button className="button button-outline button-small" onClick={() => setFault('bearing')}>Inject bearing wear</button><button className="button button-outline button-small" onClick={() => setFault('overheat')}>Inject overheat</button></div></article>
    </>
  );

  const renderControl = () => (
    <>
      <SectionTitle eyebrow="OPERATIONS / COMMANDS" title="Control panel" description="Manage speed and operating modes. Commands are logged and require confirmation." actions={<button className="button button-danger" onClick={confirmEmergencyStop}><Icon name="shield" size={15} /> Emergency stop all</button>} />
      <div className="kpi-grid four"><KpiCard label="Fleet status" value="Operational" tone="teal" trend="9 connected gateways" /><KpiCard label="Motors running" value={`${motors.filter((motor) => motor.running).length} / 10`} tone="blue" trend="Across all production areas" /><KpiCard label="Active mode" value="AI-assisted" tone="teal" trend="3 motors in this mode" /><KpiCard label="Safety interlocks" value="Engaged" tone="green" trend="All limits enforced" /></div>
      <article className="panel control-table-panel"><div className="panel-title"><div><h2>Motor commands</h2><span className="subtle">Set a mode and speed for each connected motor</span></div><span className="safety-badge"><Icon name="shield" size={14} /> Safety mode active</span></div>
        <div className="table-scroll"><table className="data-table"><thead><tr><th>Motor unit</th><th>Status</th><th>Mode</th><th>Speed setpoint</th><th>Actions</th></tr></thead><tbody>{motors.map((motor) => <tr key={motor.id}><td><button className="table-link" onClick={() => goToMotor(motor.id)}>{motor.name}</button><small>{motor.id}</small></td><td><span className={`table-status status-${motor.status}`}><i />{motor.running ? 'Running' : motor.status === 'offline' ? 'Offline' : 'Stopped'}</span></td><td><select value={motor.mode} onChange={(event) => updateMotor(motor.id, { mode: event.target.value })} aria-label={`${motor.name} mode`}><option>Manual</option><option>Scheduled</option><option>AI-assisted</option></select></td><td className="speed-cell"><input type="range" min="0" max="3000" step="25" value={motor.speed} disabled={motor.status === 'offline'} onChange={(event) => updateMotor(motor.id, { speed: Number(event.target.value) })} aria-label={`${motor.name} speed setpoint`} /><strong>{motor.speed.toLocaleString()} <small>RPM</small></strong></td><td>{motor.status === 'offline' ? <span className="subtle">—</span> : <button className={`button ${motor.running ? 'button-stop' : 'button-primary'} button-small`} onClick={() => confirmMotorCommand(motor, motor.running ? 'stop' : 'start')}>{motor.running ? 'Stop' : 'Start'}</button>}</td></tr>)}</tbody></table></div>
      </article>
      <article className="panel audit-panel"><div className="panel-title"><div><h2>Control audit log</h2><span className="subtle">Recent user and automated actions</span></div><button className="text-button" onClick={() => setToast('Audit log exported')}>Export log <Icon name="chevron" size={15} /></button></div>{auditLog.slice(0, 8).map((event) => <div className="audit-row" key={`${event.time}-${event.message}`}><time>{event.time}</time><span>{event.message}</span><span className={event.system ? 'audit-system' : 'audit-user'}>{event.actor}</span></div>)}</article>
      <div className="safety-callout"><Icon name="shield" /><div><strong>Safety-critical controls</strong><p>AI-assisted mode can recommend or apply changes only within configured limits. Emergency stop commands always require operator confirmation and are recorded in the audit log.</p></div></div>
    </>
  );

  const renderRoi = () => (
    <>
      <SectionTitle eyebrow="BUSINESS IMPACT / FINANCIALS" title="ROI & cost savings" description="Translate condition monitoring into avoided downtime, repairs, and energy costs." actions={<label className="period-select">Reporting period <select aria-label="Reporting period"><option>Last 12 months</option><option>Last 30 days</option><option>Year to date</option></select></label>} />
      <div className="kpi-grid four"><KpiCard label="Total avoided loss" value="$242,500" tone="teal" trend="↑ 12.4% vs. last period" /><KpiCard label="Energy waste saved" value="$18,240" tone="teal" trend="Approx. 42 MWh prevented" /><KpiCard label="Avoided downtime" value="156" suffix="hours" tone="amber" trend="8 costly failures detected" /><KpiCard label="System ROI score" value="4.8×" tone="dark" trend="Payback period · 6 months" /></div>
      <div className="chart-grid roi-charts"><article className="panel chart-panel"><div className="panel-title"><div><h2>Maintenance costs: planned vs unplanned</h2><span className="subtle">Monthly costs · $ thousands</span></div></div><div className="bar-chart">{[55, 73, 62, 82, 64, 77].map((height, index) => <div className="bar-group" key={index}><div className="bar-pair"><i style={{ height: `${height}%` }} /><i style={{ height: `${height * 0.34}%` }} /></div><span>{['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'][index]}</span></div>)}</div><div className="legend"><span><i className="legend-gray" /> Without system</span><span><i className="legend-teal" /> With MotorPulse</span></div></article><article className="panel chart-panel"><div className="panel-title"><div><h2>Cumulative savings</h2><span className="subtle">Yearly projection · USD</span></div><span className="chart-live">PROJECTED</span></div><TrendChart color="#119b8e" height={190} points={24} seed={3} /><div className="chart-xlabels"><span>Jan</span><span>Mar</span><span>May</span><span>Jul</span><span>Sep</span><span>Dec</span></div></article></div>
      <article className="panel savings-breakdown"><div className="panel-title"><div><h2>Savings breakdown by category</h2><span className="subtle">Where the system delivers value</span></div></div><div className="savings-content"><div className="savings-categories">{[['Downtime prevention', '$185,000', 76], ['Labor optimization', '$32,000', 53], ['Energy efficiency', '$18,240', 24], ['Parts & repairs', '$7,260', 15]].map(([label, value, width]) => <div className="savings-category" key={label}><div><span>{label}</span><strong>{value}</strong></div><div className="health-track"><span style={{ width: `${width}%` }} /></div></div>)}</div><div className="donut-chart"><div><strong>$242k</strong><span>annual savings</span></div></div></div></article>
      <article className="panel roi-inputs"><div className="panel-title"><div><h2><span className="panel-icon"><Icon name="chart" size={15} /></span> ROI calculator inputs</h2><span className="subtle">Adjust your facility assumptions to model the opportunity</span></div><span className="calculated-tag">ESTIMATED ANNUAL SAVINGS</span></div><div className="roi-fields">{[['downtime', 'Downtime cost / hour', '$'], ['planned', 'Planned repair cost', '$'], ['replacement', 'Motor replacement cost', '$'], ['tariff', 'Energy tariff (per kWh)', '$'], ['unplanned', 'Unplanned repair cost', '$'], ['technician', 'Technician hourly rate', '$']].map(([key, label, prefix]) => <label key={key}>{label}<span className="input-prefix">{prefix}<input type="number" min="0" step={key === 'tariff' ? '0.01' : '50'} value={roi[key]} onChange={(event) => updateRoi(key, event.target.value)} /></span></label>)}</div><div className="roi-total"><div><span>Estimated annual savings</span><strong>${roiAnnual.toLocaleString()}</strong></div><button className="button button-primary" onClick={() => { setRoiSaved(true); setToast('ROI forecast updated'); }}>{roiSaved ? <><Icon name="check" size={14} /> Forecast saved</> : 'Update forecast'}</button></div></article>
    </>
  );

  const renderAlerts = () => (
    <>
      <SectionTitle eyebrow="RELIABILITY / PLANNING" title="Alerts & maintenance" description="Turn early warnings into planned work before failures disrupt production." actions={<><button className="button button-outline" onClick={() => setToast('Threshold settings are ready to configure')}><Icon name="settings" size={15} /> Threshold settings</button><button className="button button-primary" onClick={() => setModal({ type: 'work-order', motorId: selectedId })}><Icon name="plus" size={15} /> Create work order</button></>} />
      <div className="section-heading alert-heading"><div><h2>Active alerts <span className="count-badge">{activeAlerts}</span></h2><p>{activeAlerts} items need review · sorted by severity</p></div><button className="text-button" onClick={() => setAlerts((current) => current.map((alert) => ({ ...alert, acknowledged: true })))}>Acknowledge all</button></div>
      <div className="alert-list">{alerts.map((alert) => <article className={`alert-card alert-${alert.severity} ${alert.acknowledged ? 'is-acknowledged' : ''}`} key={alert.id}><div className="alert-symbol">{alert.severity === 'critical' ? '!' : '△'}</div><div className="alert-body"><div className="alert-title-row"><strong>{alert.severity}: {alert.title}</strong><time>{alert.age}</time></div><span className="alert-asset">Motor: {motors.find((motor) => motor.id === alert.motorId)?.name || 'Unknown asset'} ({alert.motorId})</span><p>{alert.message}</p><div className="alert-actions">{!alert.acknowledged && <button className={`button button-small ${alert.severity === 'critical' ? 'button-danger' : 'button-warning'}`} onClick={() => acknowledge(alert.id)}>Acknowledge</button>}<button className="button button-outline button-small" onClick={() => { setSelectedId(alert.motorId); setModal({ type: 'work-order', motorId: alert.motorId, alertId: alert.id }); }}>Generate work order</button><button className="text-button compact" onClick={() => goToMotor(alert.motorId)}>View motor <Icon name="chevron" size={13} /></button></div></div>{alert.acknowledged && <span className="acknowledged-tag"><Icon name="check" size={13} /> Acknowledged</span>}</article>)}</div>
      <div className="maintenance-grid"><article className="panel calendar-panel"><div className="panel-title"><div><h2>Condition-based maintenance</h2><span className="subtle">Planned work · October 2026</span></div><span className="ai-calendar-tag"><i /> AI-driven</span></div><div className="calendar-grid">{['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN'].map((day) => <strong key={day}>{day}</strong>)}{Array.from({ length: 35 }, (_, index) => { const day = index - 2; const isCurrent = day === 27; return <div className={`calendar-day ${day < 1 || day > 31 ? 'out-month' : ''} ${isCurrent ? 'today' : ''}`} key={index}><span>{day < 1 ? 30 + day : day > 31 ? day - 31 : day}</span>{day === 14 && <small className="cal-event cal-green">A1 Coupling check</small>}{day === 20 && <small className="cal-event cal-red">Fan bearing inspect</small>}{day === 29 && <small className="cal-event cal-amber">Compressor service</small>}</div>; })}</div></article>
        <aside className="maintenance-aside"><article className="panel recommend-card"><div className="panel-title"><h2>AI recommended actions</h2><Icon name="spark" size={15} /></div><div className="recommend-entry"><span className="recommend-label">SHIFT NEEDED</span><p>Move Compressor 12 lubrication from Oct 15 to Nov 30 to increase the observed interval.</p><button className="button button-outline button-small" onClick={() => setToast('Maintenance schedule shift accepted')}>Accept shift</button></div><div className="recommend-entry"><span className="recommend-label amber-label">INVENTORY ALERT</span><p>SKF-6205 bearings (2) required for the upcoming Fan Unit Main repair. Only 1 in stock.</p><button className="button button-outline button-small" onClick={() => setToast('Bearing order request submitted')}>Order parts</button></div></article><article className="panel work-order-summary"><div className="panel-title"><h2>Work orders</h2><span className="count-badge">{workOrders}</span></div><strong>{workOrders} open and completed</strong><p>Last created · Fan Unit Main inspection</p><button className="text-button" onClick={() => setModal({ type: 'work-order', motorId: selectedId })}>Create new work order <Icon name="chevron" size={14} /></button></article></aside>
      </div>
      <article className="panel history-panel"><div className="panel-title"><div><h2>Maintenance history</h2><span className="subtle">Recent completed work</span></div><button className="text-button" onClick={() => setToast('Maintenance history exported')}>Export report <Icon name="chart" size={14} /></button></div><div className="table-scroll"><table className="data-table"><thead><tr><th>Date</th><th>Asset</th><th>Type</th><th>Technician</th><th>Status</th></tr></thead><tbody><tr><td>Oct 24, 2026</td><td>Mill Drive 01</td><td>Calibration</td><td>S. Jenkins</td><td><span className="text-teal">Completed</span></td></tr><tr><td>Oct 21, 2026</td><td>Pump Motor A2</td><td>Routine lubrication</td><td>M. Chen</td><td><span className="text-teal">Completed</span></td></tr><tr><td>Oct 18, 2026</td><td>Conveyor A-Right</td><td>Coupling inspection</td><td>R. Patel</td><td><span className="text-teal">Completed</span></td></tr></tbody></table></div></article>
    </>
  );

  const renderEnergy = () => (
    <>
      <SectionTitle eyebrow="OPERATIONS / ENERGY" title="Energy consumption & efficiency" description="Spot waste, track operating costs, and compare motor efficiency over time." actions={<span className="updated-note"><i className="live-dot" /> Live updates</span>} />
      <div className="kpi-grid four"><KpiCard label="Total power (live)" value={`${motors.reduce((sum, motor) => sum + motor.power, 0).toFixed(1)}`} suffix="kW" tone="blue" trend="Across online motors" /><KpiCard label="Consumption today" value={energyToday.toFixed(1)} suffix="kWh" tone="teal" trend="↓ 4.8% vs. yesterday" /><KpiCard label="Carbon footprint" value={(energyToday * 0.405).toFixed(1)} suffix="kg CO₂" tone="teal" trend="Estimated grid emissions" /><KpiCard label="Efficiency drift" value="−1.2%" tone="red" trend="Average across fleet" /></div>
      <div className="chart-grid energy-charts"><article className="panel chart-panel"><div className="panel-title"><div><h2>Fleet power demand (24h)</h2><span className="subtle">Kilowatts · refreshed in real time</span></div><span className="chart-live"><i className="live-dot" /> LIVE</span></div><TrendChart color="#119b8e" height={220} points={34} seed={tick + 12} /><div className="chart-xlabels"><span>12 AM</span><span>6 AM</span><span>12 PM</span><span>6 PM</span><span>Now</span></div></article><article className="panel chart-panel"><div className="panel-title"><div><h2>Top consuming motors</h2><span className="subtle">Energy use today · kWh</span></div></div><div className="horizontal-bars">{[...motors].sort((a, b) => b.power - a.power).slice(0, 5).map((motor) => <div className="hbar-row" key={motor.id}><span>{motor.name}</span><div><i style={{ width: `${Math.min(100, (motor.power / 9) * 100)}%` }} /></div><strong>{(motor.power * 7.1).toFixed(1)}</strong></div>)}</div></article></div>
      <article className="panel efficiency-panel"><div className="panel-title"><div><h2>Efficiency drift analysis</h2><span className="subtle">A degrading motor draws more current for the same work. AI compares each asset with its healthy baseline.</span></div><button className="button button-outline button-small" onClick={() => setToast('Efficiency report exported')}>Export data</button></div><div className="table-scroll"><table className="data-table"><thead><tr><th>Motor unit</th><th>Power (kW)</th><th>Efficiency</th><th>Daily cost</th><th>AI diagnosis</th></tr></thead><tbody>{motors.filter((motor) => motor.status !== 'offline').slice(0, 6).map((motor) => <tr key={motor.id}><td><button className="table-link" onClick={() => goToMotor(motor.id)}>{motor.name}</button><small>{motor.id}</small></td><td>{motor.power.toFixed(2)}</td><td className={motor.status === 'warning' || motor.status === 'critical' ? 'text-amber' : 'text-teal'}>{motor.status === 'warning' || motor.status === 'critical' ? `${(100 - motor.health * 0.08).toFixed(1)}%` : '94.2%'}</td><td>${(motor.power * 7.1 * 0.12).toFixed(2)}</td><td>{motor.status === 'warning' ? 'Current above healthy baseline' : motor.status === 'critical' ? 'Bearing friction likely' : 'Operating within expected range'}</td></tr>)}</tbody></table></div></article>
      <div className="insight-strip"><div className="insight-icon"><Icon name="bolt" /></div><div><strong>Efficiency opportunity</strong><p>Fan Unit Main is drawing 18% more power than its healthy baseline. Inspecting its bearings may reduce energy use and prevent a costly breakdown.</p></div><button className="text-button" onClick={() => goToMotor('M-44823')}>Inspect motor <Icon name="chevron" size={15} /></button></div>
    </>
  );

  const content = { overview: renderOverview, detail: renderDetail, control: renderControl, roi: renderRoi, alerts: renderAlerts, energy: renderEnergy }[screen]();
  const modalMotor = motors.find((motor) => motor.id === modal?.motorId);
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><div className="brand-mark"><Icon name="pulse" size={18} /></div><div><strong>Motor<span>Pulse</span></strong><small>FLEET INTELLIGENCE</small></div></div>
        <div className="workspace-label">WORKSPACE</div>
        <nav aria-label="Main navigation">{navItems.map((item) => <button key={item.id} className={`nav-item ${screen === item.id ? 'active' : ''}`} aria-label={item.label} onClick={() => setScreen(item.id)}><Icon name={item.icon} size={16} /><span>{item.label}</span>{item.id === 'alerts' && activeAlerts > 0 && <span className="nav-count">{activeAlerts}</span>}</button>)}</nav>
        <div className="sidebar-spacer" />
        <div className="simulator-card"><div className="simulator-top"><span className="sim-icon"><Icon name="spark" size={14} /></span><span>EXPO DEMO MODE</span><button className={`toggle ${simulating ? 'on' : ''}`} onClick={() => setSimulating((value) => !value)} role="switch" aria-checked={simulating} aria-label="Toggle live simulator"><i /></button></div><p>{simulating ? 'Synthetic telemetry is updating live' : 'Simulation paused · showing last values'}</p><div className="sim-status"><i className={simulating ? 'live-dot' : ''} />{simulating ? 'SIMULATOR RUNNING' : 'PAUSED'}</div></div>
        <button className="profile-button" onClick={() => setToast('Signed in as Marcus Chen · Maintenance Lead')}><span className="avatar">MC</span><span><strong>Marcus Chen</strong><small>Maintenance lead</small></span><Icon name="settings" size={15} /></button>
      </aside>
      <main className="main-content"><header className="topbar"><div className="breadcrumb"><span>MotorPulse</span><Icon name="chevron" size={13} /><strong>{titleMap[screen]}</strong></div><div className="topbar-actions"><span className="connection-state"><i className="live-dot" />System live</span><button className="notification-button" aria-label={`${activeAlerts} active alerts`} onClick={() => setScreen('alerts')}><Icon name="bell" size={17} />{activeAlerts > 0 && <i />}</button><span className="header-divider" /><button className="button button-primary button-small" onClick={() => { setSelectedId('M-48201'); setToast('New motor registration is not connected to a backend yet'); }}><Icon name="plus" size={14} /> Register motor</button></div></header>
        <div className="page-content">{content}<footer className="page-footer"><span><i className="live-dot" /> Gateway online</span><span>ESP32 · Wi-Fi · MQTT demo stream</span><span>Last sync · just now</span><span>v0.1.0 · Local simulation</span></footer></div>
      </main>
      {toast && <div className="toast" role="status"><span className="toast-check"><Icon name="check" size={15} /></span>{toast}<button className="toast-close" aria-label="Dismiss notification" onClick={() => setToast('')}><Icon name="close" size={14} /></button></div>}
      {modal?.type === 'motor-command' && <Modal title={`Confirm ${modal.action} command`} onClose={() => setModal(null)} footer={<><button className="button button-outline" onClick={() => setModal(null)}>Cancel</button><button className={`button ${modal.action === 'stop' ? 'button-danger' : 'button-primary'}`} onClick={executeModalAction}>{modal.action === 'stop' ? 'Confirm stop' : 'Confirm start'}</button></>}><div className="confirm-symbol"><Icon name="shield" size={23} /></div><p>This will send a <strong>{modal.action}</strong> command to <strong>{modalMotor?.name}</strong> ({modalMotor?.id}). The command will be added to the audit log.</p><p className="modal-warning">Verify the equipment area is clear and the motor is safe to operate before confirming.</p></Modal>}
      {modal?.type === 'emergency-stop' && <Modal title="Emergency stop all motors?" onClose={() => setModal(null)} footer={<><button className="button button-outline" onClick={() => setModal(null)}>Cancel</button><button className="button button-danger" onClick={executeModalAction}>Confirm emergency stop</button></>}><div className="confirm-symbol danger-symbol"><Icon name="shield" size={23} /></div><p>This sends a stop command to <strong>all {onlineCount} connected motors</strong>. This action overrides scheduled and AI-assisted operation.</p><p className="modal-warning">Use only when required by your facility's safety procedures. Confirm that stopping the equipment is safe.</p></Modal>}
      {modal?.type === 'work-order' && <Modal title="Create maintenance work order" onClose={() => setModal(null)} footer={<><button className="button button-outline" onClick={() => setModal(null)}>Cancel</button><button className="button button-primary" onClick={executeModalAction}>Create work order</button></>}><div className="work-order-form"><label>Asset<select value={modal.motorId} onChange={(event) => setModal((current) => ({ ...current, motorId: event.target.value }))}>{motors.map((motor) => <option value={motor.id} key={motor.id}>{motor.name} · {motor.id}</option>)}</select></label><label>Work type<select defaultValue={modal.alertId ? 'Condition inspection' : 'Preventive maintenance'}><option>Condition inspection</option><option>Preventive maintenance</option><option>Corrective repair</option><option>Calibration</option></select></label><label>Priority<select defaultValue={modal.alertId ? 'High' : 'Normal'}><option>Low</option><option>Normal</option><option>High</option><option>Urgent</option></select></label><label>AI recommendation<textarea defaultValue={modal.alertId ? 'Inspect motor condition and address the alert. AI recommends checking alignment, vibration, and bearing condition.' : ''} placeholder="Add a task description or AI recommendation" rows="3" /></label><p className="form-note"><Icon name="spark" size={14} /> Work orders are stored in this demo session only. Backend integration is not configured.</p></div></Modal>}
    </div>
  );
}

export default App;

import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import App from './App';

afterEach(() => {
  delete global.fetch;
});

test('renders ten motors on the fleet overview', () => {
  render(<App />);
  expect(screen.getByRole('heading', { name: /fleet overview/i })).toBeInTheDocument();
  expect(screen.getAllByRole('button', { name: /view .* details/i })).toHaveLength(10);
});

test('opens a motor detail screen from its fleet tile', () => {
  render(<App />);
  fireEvent.click(screen.getByRole('button', { name: /view pump motor a1 details/i }));
  expect(screen.getByRole('heading', { name: /pump motor a1/i })).toBeInTheDocument();
  expect(screen.getByText(/ai predictive analysis/i)).toBeInTheDocument();
});

test('shows a confirmation before sending a motor stop command', () => {
  render(<App />);
  fireEvent.click(screen.getByRole('button', { name: /control panel/i }));
  fireEvent.click(screen.getAllByRole('button', { name: 'Stop' })[0]);
  expect(screen.getByRole('dialog', { name: /confirm stop command/i })).toBeInTheDocument();
  expect(screen.getByText(/verify the equipment area is clear/i)).toBeInTheDocument();
});

test('requires confirmation before an emergency stop and then stops the fleet', () => {
  render(<App />);
  fireEvent.click(screen.getByRole('button', { name: /control panel/i }));
  fireEvent.click(screen.getByRole('button', { name: /emergency stop all/i }));
  fireEvent.click(screen.getByRole('button', { name: /confirm emergency stop/i }));
  expect(screen.getByText(/0\s*\/ 10/)).toBeInTheDocument();
  expect(screen.getByRole('status')).toHaveTextContent(/emergency stop sent/i);
});

test('fault injection updates the alert feed in demo mode', () => {
  render(<App />);
  fireEvent.click(screen.getByRole('button', { name: /motor detail/i }));
  fireEvent.click(screen.getByRole('button', { name: /inject overheat/i }));
  fireEvent.click(screen.getByRole('button', { name: /alerts & maintenance/i }));
  expect(screen.getByText(/critical: temperature detected/i)).toBeInTheDocument();
});

test('live sensor view displays acceleration data returned by the MQTT telemetry API', async () => {
  const receivedAt = new Date().toISOString();
  global.fetch = jest.fn().mockResolvedValue({
    ok: true,
    json: async () => ({
      motor_id: 'motor-01',
      latest: {
        received_at: receivedAt,
        data_source: 'simulated',
        sample_rate_hz: 100,
        sample_count: 3,
        samples: [
          { offset_s: 0, x_ms2: 0.6, y_ms2: 0, z_ms2: 9.6 },
          { offset_s: 0.01, x_ms2: 0.8, y_ms2: 0, z_ms2: 9.8 },
          { offset_s: 0.02, x_ms2: 0.4, y_ms2: 0, z_ms2: 10.2 },
        ],
        features: {
          accel_x_mean_ms2: 0,
          accel_y_mean_ms2: 0,
          accel_z_mean_ms2: 9.807,
          accel_x_rms_ms2: 0,
          accel_y_rms_ms2: 0,
          accel_z_rms_ms2: 0,
          accel_x_peak_to_peak_ms2: 0,
          accel_y_peak_to_peak_ms2: 0,
          accel_z_peak_to_peak_ms2: 0,
          accel_vector_rms_ms2: 0,
        },
      },
      history: [],
    }),
  });

  render(<App />);
  fireEvent.click(screen.getByRole('button', { name: /live sensor/i }));

  expect(await screen.findByRole('heading', { name: /live sensor · motor 01/i })).toBeInTheDocument();
  await waitFor(() => expect(screen.getByText('100 Hz')).toBeInTheDocument());
  expect(screen.getByText(/wokwi data is simulated/i)).toBeInTheDocument();
  const chart = screen.getByRole('img', { name: /3d acceleration vector on x, y, and z axes, motion detected/i });
  expect(screen.getByText('Motion detected')).toBeInTheDocument();
  expect(chart).toHaveTextContent('X');
  expect(chart).toHaveTextContent('Y');
  expect(chart).toHaveTextContent('Z');
  expect(Number(chart.querySelector('#acceleration-vector').getAttribute('x2'))).toBeGreaterThan(410);
  expect(global.fetch).toHaveBeenCalledWith(
    'http://127.0.0.1:8002/api/motors/motor-01/telemetry?limit=60',
  );
});

test('shows a steady 3D gravity vector when the sensor is still', async () => {
  global.fetch = jest.fn().mockResolvedValue({
    ok: true,
    json: async () => ({
      motor_id: 'motor-01',
      latest: {
        received_at: new Date().toISOString(),
        data_source: 'real',
        sample_rate_hz: 100,
        sample_count: 3,
        samples: [
          { offset_s: 0, x_ms2: 0.02, y_ms2: -0.01, z_ms2: 9.79 },
          { offset_s: 0.01, x_ms2: -0.03, y_ms2: 0.02, z_ms2: 9.82 },
          { offset_s: 0.02, x_ms2: 0.01, y_ms2: -0.02, z_ms2: 9.80 },
        ],
        features: {},
      },
      history: [],
    }),
  });

  render(<App />);
  fireEvent.click(screen.getByRole('button', { name: /live sensor/i }));

  const chart = await screen.findByRole('img', { name: /3d acceleration vector on x, y, and z axes, sensor still/i });
  expect(screen.getByText('Still · noise filtered')).toBeInTheDocument();
  expect(Number(chart.querySelector('#acceleration-vector').getAttribute('x2'))).toBeCloseTo(410, 0);
  expect(Number(chart.querySelector('#acceleration-vector').getAttribute('y2'))).toBeLessThan(170);
  expect(chart).toHaveTextContent('Axes scaled to ±2 g');
});

test('3D vector follows the latest raw MQTT reading without window averaging', async () => {
  const receivedAt = new Date().toISOString();
  global.fetch = jest.fn().mockResolvedValue({
    ok: true,
    json: async () => ({
      motor_id: 'motor-01',
      latest: {
        received_at: receivedAt,
        data_source: 'real',
        sample_rate_hz: 20,
        sample_count: 1,
        samples: [{ offset_s: 0, x_ms2: 9.81, y_ms2: 0, z_ms2: 0 }],
      },
      history: [
        { received_at: receivedAt, data_source: 'real', acceleration: { x_ms2: 0, y_ms2: 0, z_ms2: 9.81 } },
        { received_at: receivedAt, data_source: 'real', acceleration: { x_ms2: 9.81, y_ms2: 0, z_ms2: 0 } },
      ],
    }),
  });

  render(<App />);
  fireEvent.click(screen.getByRole('button', { name: /live sensor/i }));

  const chart = await screen.findByRole('img', { name: /3d acceleration vector on x, y, and z axes, motion detected/i });
  expect(screen.getByText('20 Hz')).toBeInTheDocument();
  expect(chart).toHaveTextContent('X: 1.00 g');
  expect(Number(chart.querySelector('#acceleration-vector').getAttribute('x2'))).toBeGreaterThan(450);
  expect(Number(chart.querySelector('#acceleration-vector').getAttribute('y2'))).toBeGreaterThan(170);
});

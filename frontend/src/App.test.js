import { fireEvent, render, screen } from '@testing-library/react';
import App from './App';

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

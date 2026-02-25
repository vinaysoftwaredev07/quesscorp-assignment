import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';

import AttendancePage from './AttendancePage';

const fetchEmployeesMock = vi.fn();
const markAttendanceMock = vi.fn();
const fetchAttendanceByEmployeeMock = vi.fn();

vi.mock('../api/employees', () => ({
  fetchEmployees: (...args) => fetchEmployeesMock(...args),
}));

vi.mock('../api/attendance', () => ({
  markAttendance: (...args) => markAttendanceMock(...args),
  fetchAttendanceByEmployee: (...args) => fetchAttendanceByEmployeeMock(...args),
}));

vi.mock('react-hot-toast', () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

describe('AttendancePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    fetchEmployeesMock.mockResolvedValue([
      {
        id: 1,
        employee_id: 'EMP001',
        full_name: 'John Doe',
      },
    ]);
  });

  test('shows validation error when mark attendance form is incomplete', async () => {
    render(<AttendancePage />);

    await screen.findByRole('heading', { name: 'Mark Attendance' });
    await userEvent.click(screen.getByRole('button', { name: 'Mark Attendance' }));

    expect(screen.getByText('All attendance fields are required')).toBeInTheDocument();
  });

  test('marks attendance with valid form data', async () => {
    markAttendanceMock.mockResolvedValueOnce({ id: 1 });

    render(<AttendancePage />);
    await screen.findByRole('heading', { name: 'Mark Attendance' });

    const dateInput = screen.getByLabelText('Date');
    await userEvent.type(dateInput, '2026-02-25');
    await userEvent.click(screen.getByRole('button', { name: 'Mark Attendance' }));

    await waitFor(() => {
      expect(markAttendanceMock).toHaveBeenCalledWith({
        employee_id: 'EMP001',
        date: '2026-02-25',
        status: 'PRESENT',
      });
    });
  });

  test('fetches and renders attendance summary', async () => {
    fetchAttendanceByEmployeeMock.mockResolvedValueOnce({
      employee_id: 'EMP001',
      total_records: 1,
      total_present: 1,
      records: [
        {
          id: 10,
          employee_id: 'EMP001',
          date: '2026-02-25',
          status: 'PRESENT',
          created_at: '2026-02-25T10:00:00Z',
        },
      ],
    });

    render(<AttendancePage />);
    await screen.findByRole('heading', { name: 'Attendance Records' });

    await userEvent.click(screen.getByRole('button', { name: 'Fetch Records' }));

    await waitFor(() => {
      expect(fetchAttendanceByEmployeeMock).toHaveBeenCalledWith('EMP001', undefined, undefined);
    });

    expect(screen.getByText('Total Records')).toBeInTheDocument();
    expect(screen.getByText('2026-02-25')).toBeInTheDocument();
  });
});

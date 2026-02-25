import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';

import EmployeePage from './EmployeePage';

const createEmployeeMock = vi.fn();
const fetchEmployeesMock = vi.fn();
const removeEmployeeMock = vi.fn();

vi.mock('../api/employees', () => ({
  createEmployee: (...args) => createEmployeeMock(...args),
  fetchEmployees: (...args) => fetchEmployeesMock(...args),
  removeEmployee: (...args) => removeEmployeeMock(...args),
}));

vi.mock('react-hot-toast', () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

describe('EmployeePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('renders employee list empty state', async () => {
    fetchEmployeesMock.mockResolvedValueOnce([]);

    render(<EmployeePage />);

    expect(await screen.findByText('No employees found')).toBeInTheDocument();
  });

  test('shows validation errors for empty form submission', async () => {
    fetchEmployeesMock.mockResolvedValueOnce([]);

    render(<EmployeePage />);
    await screen.findByText('No employees found');

    await userEvent.click(screen.getByRole('button', { name: 'Add Employee' }));

    expect(screen.getByText('Employee ID is required')).toBeInTheDocument();
    expect(screen.getByText('Full name is required')).toBeInTheDocument();
    expect(screen.getByText('Email is required')).toBeInTheDocument();
    expect(screen.getByText('Department is required')).toBeInTheDocument();
  });

  test('submits valid employee form', async () => {
    fetchEmployeesMock.mockResolvedValueOnce([]).mockResolvedValueOnce([]);
    createEmployeeMock.mockResolvedValueOnce({ employee_id: 'EMP001' });

    render(<EmployeePage />);
    await screen.findByText('No employees found');

    await userEvent.type(screen.getByPlaceholderText('EMP001'), 'EMP001');
    await userEvent.type(screen.getByPlaceholderText('John Doe'), 'John Doe');
    await userEvent.type(screen.getByPlaceholderText('john@company.com'), 'john@company.com');
    await userEvent.type(screen.getByPlaceholderText('Engineering'), 'Engineering');

    await userEvent.click(screen.getByRole('button', { name: 'Add Employee' }));

    await waitFor(() => {
      expect(createEmployeeMock).toHaveBeenCalledWith({
        employee_id: 'EMP001',
        full_name: 'John Doe',
        email: 'john@company.com',
        department: 'Engineering',
      });
    });
  });

  test('deletes an employee after confirmation', async () => {
    fetchEmployeesMock
      .mockResolvedValueOnce([
        {
          id: 1,
          employee_id: 'EMP001',
          full_name: 'John Doe',
          email: 'john@company.com',
          department: 'Engineering',
        },
      ])
      .mockResolvedValueOnce([]);
    removeEmployeeMock.mockResolvedValueOnce({ message: 'ok' });

    render(<EmployeePage />);
    await screen.findByText('EMP001');

    await userEvent.click(screen.getByRole('button', { name: 'Delete' }));
    const confirmationText = await screen.findByText(/Are you sure you want to delete employee/i);
    const modal = confirmationText.closest('div');
    await userEvent.click(within(modal).getByRole('button', { name: /^Delete$/ }));

    await waitFor(() => {
      expect(removeEmployeeMock).toHaveBeenCalledWith('EMP001');
    });
  });
});

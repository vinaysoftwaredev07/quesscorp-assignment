import { render, screen, waitFor } from '@testing-library/react';
import { vi } from 'vitest';

import DashboardPage from './DashboardPage';

const fetchEmployeesMock = vi.fn();

vi.mock('../api/employees', () => ({
  fetchEmployees: (...args) => fetchEmployeesMock(...args),
}));

describe('DashboardPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('renders employee count', async () => {
    fetchEmployeesMock.mockResolvedValueOnce([
      { employee_id: 'EMP001' },
      { employee_id: 'EMP002' },
    ]);

    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText('2')).toBeInTheDocument();
    });
  });

  test('renders error state when fetch fails', async () => {
    fetchEmployeesMock.mockRejectedValueOnce(new Error('API unavailable'));

    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText('API unavailable')).toBeInTheDocument();
    });
  });
});

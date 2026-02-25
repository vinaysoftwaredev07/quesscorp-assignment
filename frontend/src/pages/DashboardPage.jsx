import { useEffect, useState } from 'react';

import { fetchEmployees } from '../api/employees';
import Alert from '../components/Alert';
import Loader from '../components/Loader';
import useAsyncState from '../hooks/useAsyncState';

function DashboardPage() {
  const [employeeCount, setEmployeeCount] = useState(0);
  const [error, setError] = useState('');
  const { loading, withLoading } = useAsyncState(true);

  useEffect(() => {
    withLoading(async () => {
      try {
        const employees = await fetchEmployees();
        setEmployeeCount(employees.length);
        setError('');
      } catch (fetchError) {
        setError(fetchError.message);
      }
    });
  }, []);

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold text-slate-800">Dashboard</h2>
      <Alert message={error} type="error" />
      {loading ? (
        <Loader label="Loading dashboard" />
      ) : (
        <div className="rounded-lg border border-slate-200 bg-white p-6">
          <p className="text-sm text-slate-500">Total Employees</p>
          <p className="mt-2 text-3xl font-bold text-slate-900">{employeeCount}</p>
        </div>
      )}
    </div>
  );
}

export default DashboardPage;

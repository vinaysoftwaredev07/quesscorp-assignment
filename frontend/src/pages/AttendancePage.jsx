import { useEffect, useState } from 'react';
import toast from 'react-hot-toast';

import { markAttendance, fetchAttendanceByEmployee } from '../api/attendance';
import { fetchEmployees } from '../api/employees';
import Alert from '../components/Alert';
import Button from '../components/Button';
import InputField from '../components/InputField';
import Loader from '../components/Loader';
import Table from '../components/Table';
import useAsyncState from '../hooks/useAsyncState';
import { required } from '../utils/validators';

const initialForm = {
  employee_id: '',
  date: '',
  status: 'PRESENT',
};

function AttendancePage() {
  const [employees, setEmployees] = useState([]);
  const [attendanceSummary, setAttendanceSummary] = useState(null);
  const [form, setForm] = useState(initialForm);
  const [lookupEmployeeId, setLookupEmployeeId] = useState('');
  const [lookupDate, setLookupDate] = useState('');
  const [lookupMonth, setLookupMonth] = useState('');
  const [formError, setFormError] = useState('');
  const [pageError, setPageError] = useState('');

  const refreshCurrentLookup = async () => {
    if (!required(lookupEmployeeId)) {
      return;
    }

    const data = await fetchAttendanceByEmployee(lookupEmployeeId, lookupDate || undefined, lookupMonth || undefined);
    setAttendanceSummary(data);
  };

  const { loading: loadingEmployees, withLoading: withEmployeesLoading } = useAsyncState(true);
  const { loading: actionLoading, withLoading: withActionLoading } = useAsyncState(false);

  useEffect(() => {
    withEmployeesLoading(async () => {
      try {
        const data = await fetchEmployees();
        setEmployees(data);
        if (data[0]?.employee_id) {
          setForm((prev) => ({ ...prev, employee_id: data[0].employee_id }));
          setLookupEmployeeId(data[0].employee_id);
        }
      } catch (error) {
        setPageError(error.message);
      }
    });
  }, []);

  const handleMark = async (event) => {
    event.preventDefault();

    if (!required(form.employee_id) || !required(form.date) || !required(form.status)) {
      setFormError('All attendance fields are required');
      return;
    }

    setFormError('');
    await withActionLoading(async () => {
      try {
        await markAttendance(form);
        toast.success('Attendance saved successfully');
        if (lookupEmployeeId === form.employee_id) {
          await refreshCurrentLookup();
        }
      } catch (error) {
        toast.error(error.message);
      }
    });
  };

  const handleLookup = async () => {
    if (!required(lookupEmployeeId)) {
      setPageError('Please provide employee ID to fetch attendance');
      return;
    }

    await withActionLoading(async () => {
      try {
        const data = await fetchAttendanceByEmployee(lookupEmployeeId, lookupDate || undefined, lookupMonth || undefined);
        setAttendanceSummary(data);
        setPageError('');
      } catch (error) {
        setPageError(error.message);
      }
    });
  };

  const handleEditRecord = (record) => {
    setForm({
      employee_id: record.employee_id,
      date: record.date,
      status: record.status,
    });
    setFormError('');
    toast.success('Attendance loaded. Update status and save.');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <div className="space-y-6">
      <section className="rounded-lg border border-slate-200 bg-white p-4 md:p-6">
        <h2 className="mb-4 text-lg font-semibold text-slate-800">Mark Attendance</h2>
        <p className="mb-4 text-sm text-slate-500">You can update an existing date entry by selecting the same employee and date, then saving again.</p>
        {loadingEmployees ? <Loader label="Loading employees" /> : null}
        <form onSubmit={handleMark} className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <div>
            <label htmlFor="attendance-employee" className="mb-1 block text-sm font-medium text-slate-700">Employee</label>
            <select
              id="attendance-employee"
              value={form.employee_id}
              onChange={(event) => setForm((prev) => ({ ...prev, employee_id: event.target.value }))}
              className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm"
            >
              <option value="">Select employee</option>
              {employees.map((employee) => (
                <option key={employee.employee_id} value={employee.employee_id}>
                  {employee.employee_id} - {employee.full_name}
                </option>
              ))}
            </select>
          </div>
          <InputField
            label="Date"
            type="date"
            value={form.date}
            onChange={(event) => setForm((prev) => ({ ...prev, date: event.target.value }))}
          />
          <div>
            <label htmlFor="attendance-status" className="mb-1 block text-sm font-medium text-slate-700">Status</label>
            <select
              id="attendance-status"
              value={form.status}
              onChange={(event) => setForm((prev) => ({ ...prev, status: event.target.value }))}
              className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm"
            >
              <option value="PRESENT">Present</option>
              <option value="ABSENT">Absent</option>
            </select>
          </div>
          <div className="md:col-span-3">
            <Alert message={formError} type="error" />
          </div>
          <div className="md:col-span-3">
            <Button type="submit" disabled={actionLoading}>
              {actionLoading ? 'Saving...' : 'Mark Attendance'}
            </Button>
          </div>
        </form>
      </section>

      <section className="space-y-4 rounded-lg border border-slate-200 bg-white p-4 md:p-6">
        <h2 className="text-lg font-semibold text-slate-800">Attendance Records</h2>
        <Alert message={pageError} type="error" />
        <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
          <InputField
            label="Employee ID"
            value={lookupEmployeeId}
            onChange={(event) => setLookupEmployeeId(event.target.value)}
            placeholder="EMP001"
          />
          <InputField
            label="Date Filter (optional)"
            type="date"
            value={lookupDate}
            onChange={(event) => setLookupDate(event.target.value)}
          />
          <InputField
            label="Month Filter (optional)"
            type="month"
            value={lookupMonth}
            onChange={(event) => setLookupMonth(event.target.value)}
          />
          <div className="flex items-end">
            <Button onClick={handleLookup} disabled={actionLoading}>
              {actionLoading ? 'Fetching...' : 'Fetch Records'}
            </Button>
          </div>
        </div>

        {attendanceSummary ? (
          <div className="space-y-3">
            <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
              <div className="rounded-md border border-slate-200 bg-slate-50 p-3 text-sm">
                <p className="text-slate-500">Employee</p>
                <p className="font-semibold text-slate-800">{attendanceSummary.employee_id}</p>
              </div>
              <div className="rounded-md border border-slate-200 bg-slate-50 p-3 text-sm">
                <p className="text-slate-500">Total Records</p>
                <p className="font-semibold text-slate-800">{attendanceSummary.total_records}</p>
              </div>
              <div className="rounded-md border border-slate-200 bg-slate-50 p-3 text-sm">
                <p className="text-slate-500">Total Present Days</p>
                <p className="font-semibold text-slate-800">{attendanceSummary.total_present}</p>
              </div>
            </div>
            <Table
              columns={[
                { key: 'date', label: 'Date' },
                {
                  key: 'status',
                  label: 'Status',
                  render: (value) => (
                    <span
                      className={`rounded px-2 py-1 text-xs font-semibold ${
                        value === 'PRESENT' ? 'bg-emerald-100 text-emerald-700' : 'bg-rose-100 text-rose-700'
                      }`}
                    >
                      {value}
                    </span>
                  ),
                },
                { key: 'created_at', label: 'Marked At' },
              ]}
              data={attendanceSummary.records}
              emptyText="No attendance records found"
              renderActions={(row) => (
                <Button variant="secondary" onClick={() => handleEditRecord(row)}>
                  Update
                </Button>
              )}
            />
          </div>
        ) : (
          <p className="text-sm text-slate-500">Search attendance by employee to view records.</p>
        )}
      </section>
    </div>
  );
}

export default AttendancePage;

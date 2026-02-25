import { useEffect, useState } from 'react';
import toast from 'react-hot-toast';

import { createEmployee, fetchEmployees, removeEmployee } from '../api/employees';
import Alert from '../components/Alert';
import Button from '../components/Button';
import InputField from '../components/InputField';
import Loader from '../components/Loader';
import Modal from '../components/Modal';
import Table from '../components/Table';
import useAsyncState from '../hooks/useAsyncState';
import { isValidEmail, required } from '../utils/validators';

const initialForm = {
  employee_id: '',
  full_name: '',
  email: '',
  department: '',
};

function EmployeePage() {
  const [employees, setEmployees] = useState([]);
  const [form, setForm] = useState(initialForm);
  const [formErrors, setFormErrors] = useState({});
  const [pageError, setPageError] = useState('');
  const [employeeToDelete, setEmployeeToDelete] = useState(null);

  const { loading: listLoading, withLoading: withListLoading } = useAsyncState(true);
  const { loading: actionLoading, withLoading: withActionLoading } = useAsyncState(false);

  const loadEmployees = async () => {
    await withListLoading(async () => {
      try {
        const data = await fetchEmployees();
        setEmployees(data);
        setPageError('');
      } catch (error) {
        setPageError(error.message);
      }
    });
  };

  useEffect(() => {
    loadEmployees();
  }, []);

  const validate = () => {
    const errors = {};
    if (!required(form.employee_id)) errors.employee_id = 'Employee ID is required';
    if (!required(form.full_name)) errors.full_name = 'Full name is required';
    if (!required(form.email)) errors.email = 'Email is required';
    if (required(form.email) && !isValidEmail(form.email)) errors.email = 'Invalid email format';
    if (!required(form.department)) errors.department = 'Department is required';
    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleCreate = async (event) => {
    event.preventDefault();
    if (!validate()) return;

    await withActionLoading(async () => {
      try {
        await createEmployee(form);
        toast.success('Employee added successfully');
        setForm(initialForm);
        await loadEmployees();
      } catch (error) {
        toast.error(error.message);
      }
    });
  };

  const handleDelete = async () => {
    if (!employeeToDelete) return;
    await withActionLoading(async () => {
      try {
        await removeEmployee(employeeToDelete.employee_id);
        toast.success('Employee deleted successfully');
        setEmployeeToDelete(null);
        await loadEmployees();
      } catch (error) {
        toast.error(error.message);
      }
    });
  };

  return (
    <div className="space-y-6">
      <section className="rounded-lg border border-slate-200 bg-white p-4 md:p-6">
        <h2 className="mb-4 text-lg font-semibold text-slate-800">Add Employee</h2>
        <form onSubmit={handleCreate} className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <InputField
            label="Employee ID"
            value={form.employee_id}
            onChange={(event) => setForm((prev) => ({ ...prev, employee_id: event.target.value }))}
            error={formErrors.employee_id}
            placeholder="EMP001"
          />
          <InputField
            label="Full Name"
            value={form.full_name}
            onChange={(event) => setForm((prev) => ({ ...prev, full_name: event.target.value }))}
            error={formErrors.full_name}
            placeholder="John Doe"
          />
          <InputField
            label="Email"
            value={form.email}
            onChange={(event) => setForm((prev) => ({ ...prev, email: event.target.value }))}
            error={formErrors.email}
            placeholder="john@company.com"
            type="email"
          />
          <InputField
            label="Department"
            value={form.department}
            onChange={(event) => setForm((prev) => ({ ...prev, department: event.target.value }))}
            error={formErrors.department}
            placeholder="Engineering"
          />
          <div className="md:col-span-2">
            <Button type="submit" disabled={actionLoading}>
              {actionLoading ? 'Saving...' : 'Add Employee'}
            </Button>
          </div>
        </form>
      </section>

      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-800">Employees</h2>
          {listLoading ? <Loader label="Fetching employees" /> : null}
        </div>
        <Alert message={pageError} type="error" />
        <Table
          columns={[
            { key: 'employee_id', label: 'Employee ID' },
            { key: 'full_name', label: 'Full Name' },
            { key: 'email', label: 'Email' },
            { key: 'department', label: 'Department' },
          ]}
          data={employees}
          emptyText="No employees found"
          renderActions={(row) => (
            <Button variant="danger" onClick={() => setEmployeeToDelete(row)}>
              Delete
            </Button>
          )}
        />
      </section>

      <Modal open={Boolean(employeeToDelete)} title="Confirm Delete" onClose={() => setEmployeeToDelete(null)}>
        <p className="mb-4 text-sm text-slate-600">
          Are you sure you want to delete employee <strong>{employeeToDelete?.employee_id}</strong>?
        </p>
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={() => setEmployeeToDelete(null)}>
            Cancel
          </Button>
          <Button variant="danger" onClick={handleDelete} disabled={actionLoading}>
            {actionLoading ? 'Deleting...' : 'Delete'}
          </Button>
        </div>
      </Modal>
    </div>
  );
}

export default EmployeePage;

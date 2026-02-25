import apiClient from './client';

export const createEmployee = async (payload) => {
  const { data } = await apiClient.post('/employees', payload);
  return data;
};

export const fetchEmployees = async () => {
  const { data } = await apiClient.get('/employees');
  return data;
};

export const removeEmployee = async (employeeId) => {
  const { data } = await apiClient.delete(`/employees/${employeeId}`);
  return data;
};

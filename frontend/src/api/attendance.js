import apiClient from './client';

export const markAttendance = async (payload) => {
  const { data } = await apiClient.post('/attendance', payload);
  return data;
};

export const fetchAttendanceByEmployee = async (employeeId, date, month) => {
  const params = {};
  if (date) {
    params.date = date;
  }
  if (month) {
    params.month = month;
  }
  const { data } = await apiClient.get(`/attendance/${employeeId}`, { params });
  return data;
};

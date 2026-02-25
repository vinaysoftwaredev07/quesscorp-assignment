import apiClient from './client';

export const enterWithSuperadminKey = async (key) => {
  const { data } = await apiClient.post('/auth/enter', { key });
  return data;
};

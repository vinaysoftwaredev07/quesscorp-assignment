const STORAGE_KEY = 'hrms_superadmin_key';

export const getStoredAdminKey = () => localStorage.getItem(STORAGE_KEY) || '';

export const setStoredAdminKey = (value) => {
  localStorage.setItem(STORAGE_KEY, value);
};

export const clearStoredAdminKey = () => {
  localStorage.removeItem(STORAGE_KEY);
};

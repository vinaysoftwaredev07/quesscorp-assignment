export const isValidEmail = (value) => /^(?!\.)(?!.*\.\.)([A-Za-z0-9_'+-.]*)[A-Za-z0-9_+-]@([A-Za-z0-9][A-Za-z0-9-]*\.)+[A-Za-z]{2,}$/.test(value);

export const required = (value) => String(value || '').trim().length > 0;

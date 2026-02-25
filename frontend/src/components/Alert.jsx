import PropTypes from 'prop-types';

function Alert({ message, type = 'error' }) {
  if (!message) {
    return null;
  }

  const styles = {
    error: 'border-rose-200 bg-rose-50 text-rose-700',
    success: 'border-emerald-200 bg-emerald-50 text-emerald-700',
    info: 'border-sky-200 bg-sky-50 text-sky-700',
  };

  return <div className={`rounded-md border px-3 py-2 text-sm ${styles[type]}`}>{message}</div>;
}

Alert.propTypes = {
  message: PropTypes.string,
  type: PropTypes.oneOf(['error', 'success', 'info']),
};

export default Alert;

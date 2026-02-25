import PropTypes from 'prop-types';
import { useId } from 'react';

function InputField({ id, label, error, className = '', ...props }) {
  const generatedId = useId();
  const inputId = id || generatedId;

  return (
    <div className={`w-full ${className}`}>
      {label ? <label htmlFor={inputId} className="mb-1 block text-sm font-medium text-slate-700">{label}</label> : null}
      <input
        id={inputId}
        className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none ring-0 transition focus:border-slate-900"
        {...props}
      />
      {error ? <p className="mt-1 text-xs text-rose-600">{error}</p> : null}
    </div>
  );
}

InputField.propTypes = {
  id: PropTypes.string,
  label: PropTypes.string,
  error: PropTypes.string,
  className: PropTypes.string,
};

export default InputField;

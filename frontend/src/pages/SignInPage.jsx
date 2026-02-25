import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';

import { enterWithSuperadminKey } from '../api/auth';
import Alert from '../components/Alert';
import Button from '../components/Button';
import InputField from '../components/InputField';
import { setStoredAdminKey } from '../utils/auth';

function SignInPage() {
  const [key, setKey] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (!key.trim()) {
      setError('Superadmin key is required');
      return;
    }

    setLoading(true);
    setError('');

    try {
      await enterWithSuperadminKey(key.trim());
      setStoredAdminKey(key.trim());
      toast.success('Access granted');
      navigate('/dashboard', { replace: true });
    } catch (apiError) {
      setError(apiError.message || 'Invalid superadmin key');
      toast.error(apiError.message || 'Invalid superadmin key');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto mt-12 w-full max-w-md rounded-lg border border-slate-200 bg-white p-6">
      <h2 className="mb-2 text-xl font-semibold text-slate-800">Admin Entrance</h2>
      <p className="mb-4 text-sm text-slate-500">Enter the shared superadmin key to access HRMS Lite.</p>
      <Alert message={error} type="error" />
      <form className="mt-4 space-y-4" onSubmit={handleSubmit}>
        <InputField
          label="Superadmin Key"
          type="password"
          placeholder="Enter shared key"
          value={key}
          onChange={(event) => setKey(event.target.value)}
        />
        <Button type="submit" disabled={loading} className="w-full">
          {loading ? 'Verifying...' : 'Enter Platform'}
        </Button>
      </form>
    </div>
  );
}

export default SignInPage;

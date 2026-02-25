import { useState } from 'react';

function useAsyncState(initial = false) {
  const [loading, setLoading] = useState(initial);

  const withLoading = async (fn) => {
    setLoading(true);
    try {
      return await fn();
    } finally {
      setLoading(false);
    }
  };

  return { loading, withLoading, setLoading };
}

export default useAsyncState;

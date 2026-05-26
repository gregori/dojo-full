import { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

export default function CallbackPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { user, isLoading } = useAuth();

  useEffect(() => {
    const success = searchParams.get('success');
    const error = searchParams.get('error');

    if (success === 'true') {
      // The backend has set auth cookies. The AuthProvider will fetch user data.
      // Wait for the user to be loaded.
      if (!isLoading && user) {
        navigate('/dashboard', { replace: true });
      }
    } else {
      // OAuth failed — redirect to login with error message
      const errorMsg = error || 'Google OAuth login failed';
      navigate(`/login?error=${encodeURIComponent(errorMsg)}`, { replace: true });
    }
  }, [searchParams, user, isLoading, navigate]);

  return (
    <div style={{ textAlign: 'center', padding: '2rem' }}>
      <h2>Processing login...</h2>
      <p>Please wait while we complete your authentication.</p>
    </div>
  );
}
import React, { useEffect, useState } from 'react';
import { useLocation } from 'wouter';
import { apiRequest } from '@/lib/queryClient';
import { API_CONFIG } from '@/config/api';

export default function ResetPasswordPage() {
  const [, setLocation] = useLocation();

  // Parse query params from current URL (works with wouter)
  const params = new URLSearchParams(window.location.search);
  const token = params.get('token') || '';
  const email = params.get('email') || '';

  const [status, setStatus] = useState<'loading' | 'invalid' | 'valid' | 'submitted'>('loading');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!token || !email) {
      setStatus('invalid');
      return;
    }

    (async () => {
      try {
        await apiRequest(
          `${API_CONFIG.ENDPOINTS.AUTH_VERIFY_RESET}?email=${encodeURIComponent(email)}&token=${encodeURIComponent(token)}`,
          'GET'
        );
        setStatus('valid');
      } catch (e) {
        setStatus('invalid');
      }
    })();
  }, [token, email]);

  const validatePassword = (p: string) => {
    return (
      p.length >= 8 && /[A-Z]/.test(p) && /[a-z]/.test(p) && /[0-9]/.test(p) && /[^A-Za-z0-9]/.test(p)
    );
  };

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (newPassword !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }
    if (!validatePassword(newPassword)) {
      setError('Password does not meet complexity requirements');
      return;
    }
    setLoading(true);
    try {
      await apiRequest(API_CONFIG.ENDPOINTS.AUTH_RESET_PASSWORD, 'POST', {
        email,
        token,
        new_password: newPassword,
      });
      setStatus('submitted');
      setTimeout(() => setLocation('/login'), 1500);
    } catch (e) {
      setError('Failed to reset password. Link may be invalid or expired.');
    } finally {
      setLoading(false);
    }
  };

  if (status === 'loading') return <div className="p-8">Verifying reset link...</div>;
  if (status === 'invalid') return <div className="p-8">Link expired or invalid.</div>;
  if (status === 'submitted') return <div className="p-8">Password reset successful. Redirecting to login...</div>;

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="max-w-md w-full bg-white p-8 rounded-xl shadow">
        <h2 className="text-xl font-bold mb-4">Set a new password</h2>
        <form onSubmit={onSubmit}>
          <label className="block text-sm mb-2">New password</label>
          <input
            type="password"
            required
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            className="w-full px-3 py-2 border rounded mb-4"
          />
          <label className="block text-sm mb-2">Confirm password</label>
          <input
            type="password"
            required
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            className="w-full px-3 py-2 border rounded mb-4"
          />
          {error && <div className="text-red-600 mb-2">{error}</div>}
          <button className="w-full bg-blue-600 text-white py-2 rounded" disabled={loading}>
            {loading ? 'Resetting...' : 'Reset password'}
          </button>
        </form>
      </div>
    </div>
  );
}

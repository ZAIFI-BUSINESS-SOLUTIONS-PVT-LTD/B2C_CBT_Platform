import React, { useState } from 'react';
import { apiRequest } from '@/lib/queryClient';
import { API_CONFIG } from '@/config/api';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await apiRequest(API_CONFIG.ENDPOINTS.AUTH_FORGOT_PASSWORD, 'POST', { email });
    } catch (e) {
      // ignore errors - always show generic message
    } finally {
      setLoading(false);
      setSubmitted(true);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="max-w-md w-full bg-white p-8 rounded-xl shadow">
        <h2 className="text-xl font-bold mb-4">Forgot password</h2>
        {!submitted ? (
          <form onSubmit={onSubmit}>
            <label className="block text-sm mb-2">Email</label>
            <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className="w-full px-3 py-2 border rounded mb-4" />
            <button className="w-full bg-blue-600 text-white py-2 rounded" disabled={loading}>
              {loading ? 'Sending...' : 'Send reset link'}
            </button>
          </form>
        ) : (
          <div className="text-center">
            <p className="mb-4">If this email exists, reset instructions were sent.</p>
            <a href="/login" className="text-blue-600">Return to login</a>
          </div>
        )}
      </div>
    </div>
  );
}

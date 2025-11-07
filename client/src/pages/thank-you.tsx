import React from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useLocation } from 'wouter';
import { Button } from '@/components/ui/button';

export default function ThankYou() {
  const { logout } = useAuth();
  const [, navigate] = useLocation();

  const handleLogout = async () => {
    try {
      await logout();
    } catch (e) {
      console.error('Logout failed', e);
    } finally {
      // Navigate to login page
      navigate('/login');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-blue-50/30 to-indigo-50 px-4">
      <div className="bg-white rounded-2xl shadow-lg border border-gray-200 p-8 max-w-lg text-center">
        <h1 className="text-2xl font-semibold mb-4">Thanks for taking the test!</h1>
        <p className="text-gray-600 mb-6">
          Your results will be shared with you soon on your registered phone number or email ID.
        </p>
        <div className="flex justify-center">
          <Button onClick={handleLogout} className="bg-blue-600 text-white px-6 py-2 rounded-lg">Logout</Button>
        </div>
      </div>
    </div>
  );
}

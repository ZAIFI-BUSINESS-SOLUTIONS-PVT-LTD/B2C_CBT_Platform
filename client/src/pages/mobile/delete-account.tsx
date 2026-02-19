import React from 'react';
import { useLocation } from 'wouter';
import { Button } from '@/components/ui/button';

export default function MobileDeleteAccount() {
  const [, navigate] = useLocation();

  return (
    <div className="min-h-screen bg-white px-4 py-6">
      <div className="max-w-xl mx-auto">
        <header className="mb-4">
          <button onClick={() => navigate('/login')} className="text-blue-600 mb-2">Back</button>
          <h1 className="text-2xl font-semibold text-gray-900">Delete Account</h1>
          <p className="text-sm text-gray-500">Effective Date: February 16, 2026</p>
        </header>

        <article className="bg-white shadow-sm rounded-lg p-4 text-gray-800">
          <section className="mb-3">
            <p>
              Use this page to permanently delete your NEETBRO account and all associated data. Deleting
              your account will remove test results, answers, AI insights, chat history, notifications,
              and any other personal data stored by the application. This action is irreversible.
            </p>
          </section>

          <h2 className="font-semibold mt-3">What Gets Deleted</h2>
          <ul className="list-disc list-inside text-sm mb-2">
            <li>Answers and test submissions</li>
            <li>Test sessions and scheduled tests</li>
            <li>AI-generated insights and analytics</li>
            <li>Chat sessions and messages</li>
            <li>Notifications and password reset tokens</li>
            <li>Activity logs and personal profile information</li>
          </ul>

          <h2 className="font-semibold mt-3">How to Delete</h2>
          <p className="text-sm">Follow the in-app delete flow in Settings &gt; Delete Account and confirm when prompted. You will be logged out after deletion.</p>

          <h2 className="font-semibold mt-3">Retention & Legal Exceptions</h2>
          <p className="text-sm">We may retain certain records if required by law or to comply with legal obligations.</p>

          <h2 className="font-semibold mt-3">Contact</h2>
          <p className="text-sm">If you need assistance, contact support@neatbro.com.</p>

          <div className="mt-6 flex justify-center">
            <Button onClick={() => navigate('/')} className="bg-blue-600 text-white">Return Home</Button>
          </div>
        </article>
      </div>
    </div>
  );
}

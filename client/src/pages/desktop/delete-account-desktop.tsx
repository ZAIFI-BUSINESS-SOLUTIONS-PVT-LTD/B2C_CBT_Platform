import React from 'react';
import { useLocation } from 'wouter';
import { Button } from '@/components/ui/button';

export default function DesktopDeleteAccount() {
  const [, navigate] = useLocation();

  return (
    <div className="min-h-screen flex items-start justify-center bg-gradient-to-br from-slate-50 to-white p-12">
      <div className="w-full max-w-4xl bg-white rounded-2xl shadow-lg border border-gray-200 p-10">
        <div className="mb-6 flex justify-between items-start">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Delete Account</h1>
            <p className="text-sm text-gray-500">Effective Date: February 16, 2026</p>
          </div>
          <div>
            <Button onClick={() => navigate('/login')} className="bg-blue-50 text-blue-600">Back</Button>
          </div>
        </div>

        <article className="prose prose-sm prose-slate max-w-none text-gray-800">
          <p>
            Use this page to permanently delete your NEETBRO account and all associated data. Deleting
            your account will remove test results, answers, AI insights, chat history, notifications,
            and any other personal data stored by the application. This action is irreversible.
          </p>

          <h2>What Gets Deleted</h2>
          <ul>
            <li>Answers and test submissions</li>
            <li>Test sessions and scheduled tests</li>
            <li>AI-generated insights and analytics</li>
            <li>Chat sessions and messages</li>
            <li>Notifications and password reset tokens</li>
            <li>Activity logs and personal profile information</li>
          </ul>

          <h2>How to Delete</h2>
          <p>
            To delete your account, open Settings &gt; Delete Account in the app and follow the
            confirmation prompts. You will be asked to confirm the deletion explicitly. After
            deletion completes you will be logged out and will no longer be able to sign in with the
            same account credentials.
          </p>

          <h2>Retention & Legal Exceptions</h2>
          <p>
            We generally remove associated data when an account is deleted. However, we may retain
            certain records if required by law or to comply with legal obligations, resolve disputes,
            or enforce our agreements.
          </p>

          <h2>Contact</h2>
          <p>
            If you need assistance or have questions about account deletion, contact support@neatbro.com.
          </p>

          <div className="mt-6">
            <Button onClick={() => navigate('/')} className="bg-blue-600 text-white">Return Home</Button>
          </div>
        </article>
      </div>
    </div>
  );
}

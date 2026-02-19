import React from 'react';
import { useLocation } from 'wouter';
import { Button } from '@/components/ui/button';

export default function MobilePolicy() {
  const [, navigate] = useLocation();

  return (
    <div className="min-h-screen bg-white px-4 py-6">
      <div className="max-w-xl mx-auto">
        <header className="mb-4">
          <button onClick={() => navigate('/login')} className="text-blue-600 mb-2">Back</button>
          <h1 className="text-2xl font-semibold text-gray-900">Privacy Policy for NEETBRO</h1>
          <p className="text-sm text-gray-500">Effective Date: February 16, 2026</p>
        </header>

        <article className="bg-white shadow-sm rounded-lg p-4 text-gray-800">
          <section className="mb-3">
            <p>
              This Privacy Policy explains how NEETBRO, operated by ZAi-Fi Business Solutions ("we,"
              "our," or "us"), collects, uses, shares, and protects your personal information when you
              use our mobile application. NEETBRO is a test taking platform where users log in via Google
              Sign-In or phone number authentication, take scheduled or customized tests by selecting
              chapters and questions, and receive results with AI-generated insights.
            </p>
          </section>

          <h2 className="font-semibold mt-3">Information We Collect</h2>
          <p className="text-sm text-gray-600">We collect personal information necessary for app functionality and performance.</p>

          <h3 className="mt-2 font-medium">Login Data</h3>
          <ul className="list-disc list-inside text-sm mb-2">
            <li>Name and email address (via Google Sign-In using profile, email, and openid scopes only)</li>
            <li>Phone number (via OTP authentication)</li>
          </ul>
          <p className="text-sm">We do not access Google Drive, Gmail, or other Google account data.</p>

          <h3 className="mt-2 font-medium">Test Data</h3>
          <ul className="list-disc list-inside text-sm mb-2">
            <li>Answers submitted during tests</li>
            <li>Scores and performance metrics</li>
            <li>Selected chapters and questions</li>
            <li>Test timestamps and scheduling information</li>
          </ul>

          <h3 className="mt-2 font-medium">Usage Data</h3>
          <p className="text-sm">We do not collect analytics or device-level usage tracking data beyond what is strictly required for app functionality and security.</p>

          <h3 className="mt-2 font-medium">AI Insights Data</h3>
          <p className="text-sm">Test performance data may be processed to generate personalized feedback and AI-based insights.</p>

          <h3 className="mt-2 font-medium">We do not collect sensitive personal data such as:</h3>
          <ul className="list-disc list-inside text-sm mb-2">
            <li>Location data</li>
            <li>Photos or media files</li>
            <li>Financial information</li>
            <li>Health data</li>
          </ul>

          <h2 className="font-semibold mt-3">How We Use Your Information</h2>
          <p className="text-sm">We use collected data to operate and improve NEETBRO, including:</p>
          <ul className="list-disc list-inside text-sm mb-2">
            <li>Authenticating users and managing accounts</li>
            <li>Delivering tests and storing results</li>
            <li>Generating AI-based performance insights</li>
            <li>Improving app functionality and analytics</li>
            <li>Communicating important updates or results</li>
          </ul>

          <h2 className="font-semibold mt-3">Sharing and Disclosure</h2>
          <p className="text-sm">We share only limited data with trusted service providers:</p>

          <div className="text-sm mt-2">
            <p className="font-medium">Third Party — Purpose — Data Shared</p>
            <ul className="list-disc list-inside">
              <li>Google (OAuth) — Authentication — Name, email</li>
              <li>AI service providers — AI insights generation — Anonymized test data</li>
              <li>Firebase Analytics — App performance monitoring — Aggregated usage data</li>
            </ul>
          </div>

          <p className="text-sm mt-2">We do not sell personal data.</p>
          <p className="text-sm">We may disclose information when necessary to comply with legal obligations, prevent fraud or misuse, or support business transfers or restructuring. Some services may process data on servers outside India; appropriate safeguards are used.</p>

          <h2 className="font-semibold mt-3">Data Security and Retention</h2>
          <p className="text-sm">We protect data using:</p>
          <ul className="list-disc list-inside text-sm mb-2">
            <li>Encryption in transit (TLS)</li>
            <li>Secure storage practices</li>
            <li>Access controls</li>
            <li>Periodic security reviews</li>
          </ul>

          <p className="text-sm font-medium">Retention</p>
          <ul className="list-disc list-inside text-sm mb-2">
            <li>Account data: retained while the account is active and up to 2 years after inactivity</li>
            <li>Test data: retained until deletion is requested</li>
            <li>Deleted accounts: associated data removed unless legally required to retain</li>
          </ul>

          <h2 className="font-semibold mt-3">Your Rights and Choices</h2>
          <p className="text-sm">You may access your data, correct inaccurate information, request deletion, export your data, or withdraw consent. To exercise these rights, contact: support@neatbro.com. Requests are typically processed within 30 days.</p>

          <h2 className="font-semibold mt-3">Account Deletion</h2>
          <p className="text-sm">Users can delete their account through in-app settings or by contacting support. Associated test data and results will be removed.</p>

          <h2 className="font-semibold mt-3">Children’s Privacy</h2>
          <p className="text-sm">If we become aware that personal information from a child has been provided without appropriate parental or guardian consent where required by law, we will take steps to delete such information promptly.</p>

          <h2 className="font-semibold mt-3">Changes to This Policy</h2>
          <p className="text-sm">We may update this Privacy Policy periodically. Significant changes will be communicated through the app or via email. Continued use after updates constitutes acceptance.</p>

          <h2 className="font-semibold mt-3">Contact Us</h2>
          <p className="text-sm">ZAi-Fi Business Solutions<br/>mohamed hanig nager, Villupuram, Tamilnadu<br/>Email: support@neatbro.com<br/>Website: https://neatbro.com</p>

          <div className="mt-6 flex justify-center">
            <Button onClick={() => navigate('/')} className="bg-blue-600 text-white">Return Home</Button>
          </div>
        </article>
      </div>
    </div>
  );
}

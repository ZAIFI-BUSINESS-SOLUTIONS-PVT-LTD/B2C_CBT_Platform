import React from 'react';
import { useLocation } from 'wouter';
import { Button } from '@/components/ui/button';

export default function DesktopPolicy() {
  const [, navigate] = useLocation();

  return (
    <div className="min-h-screen flex items-start justify-center bg-gradient-to-br from-slate-50 to-white p-12">
      <div className="w-full max-w-4xl bg-white rounded-2xl shadow-lg border border-gray-200 p-10">
        <div className="mb-6 flex justify-between items-start">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Privacy Policy for NEETBRO</h1>
            <p className="text-sm text-gray-500">Effective Date: February 16, 2026</p>
          </div>
          <div>
            <Button onClick={() => navigate('/login')} className="bg-blue-50 text-blue-600">Back</Button>
          </div>
        </div>

        <article className="prose prose-sm prose-slate max-w-none text-gray-800">
          <p>
            This Privacy Policy explains how NEETBRO, operated by ZAi-Fi Business Solutions ("we," "our," or "us"),
            collects, uses, shares, and protects your personal information when you use our mobile application. NEETBRO
            is a test taking platform where users log in via Google Sign-In or phone number authentication, take scheduled
            or customized tests by selecting chapters and questions, and receive results with AI-generated insights.
          </p>

          <h2>Information We Collect</h2>
          <p>We collect personal information necessary for app functionality and performance.</p>

          <h3>Login Data</h3>
          <ul>
            <li>Name and email address (via Google Sign-In using profile, email, and openid scopes only)</li>
            <li>Phone number (via OTP authentication)</li>
          </ul>
          <p>We do not access Google Drive, Gmail, or other Google account data.</p>

          <h3>Test Data</h3>
          <ul>
            <li>Answers submitted during tests</li>
            <li>Scores and performance metrics</li>
            <li>Selected chapters and questions</li>
            <li>Test timestamps and scheduling information</li>
          </ul>

          <h3>Usage Data</h3>
          <p>We do not collect analytics or device-level usage tracking data beyond what is strictly required for app functionality and security.</p>

          <h3>AI Insights Data</h3>
          <p>Test performance data may be processed to generate personalized feedback and AI-based insights.</p>

          <h3>We do not collect sensitive personal data such as:</h3>
          <ul>
            <li>Location data</li>
            <li>Photos or media files</li>
            <li>Financial information</li>
            <li>Health data</li>
          </ul>

          <h2>How We Use Your Information</h2>
          <p>We use collected data to operate and improve NEETBRO, including:</p>
          <ul>
            <li>Authenticating users and managing accounts</li>
            <li>Delivering tests and storing results</li>
            <li>Generating AI-based performance insights</li>
            <li>Improving app functionality and analytics</li>
            <li>Communicating important updates or results</li>
          </ul>

          <h2>Sharing and Disclosure</h2>
          <p>We share only limited data with trusted service providers:</p>
          <table className="table-auto w-full">
            <thead>
              <tr>
                <th className="text-left">Third Party</th>
                <th className="text-left">Purpose</th>
                <th className="text-left">Data Shared</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Google (OAuth)</td>
                <td>Authentication</td>
                <td>Name, email</td>
              </tr>
              <tr>
                <td>AI service providers</td>
                <td>AI insights generation</td>
                <td>Anonymized test data</td>
              </tr>
              <tr>
                <td>Firebase Analytics</td>
                <td>App performance monitoring</td>
                <td>Aggregated usage data</td>
              </tr>
            </tbody>
          </table>

          <p>We do not sell personal data. We may disclose information when necessary to comply with legal obligations, prevent fraud or misuse, or support business transfers or restructuring. Some services may process data on servers outside India; appropriate safeguards are used.</p>

          <h2>Data Security and Retention</h2>
          <p>We protect data using encryption in transit (TLS), secure storage practices, access controls, and periodic security reviews.</p>

          <h3>Retention</h3>
          <ul>
            <li>Account data: retained while the account is active and up to 2 years after inactivity</li>
            <li>Test data: retained until deletion is requested</li>
            <li>Deleted accounts: associated data removed unless legally required to retain</li>
          </ul>

          <h2>Your Rights and Choices</h2>
          <p>You may access your data, correct inaccurate information, request deletion, export your data, or withdraw consent. To exercise these rights, contact: support@neatbro.com. Requests are typically processed within 30 days.</p>

          <h2>Account Deletion</h2>
          <p>Users can delete their account through in-app settings or by contacting support. Associated test data and results will be removed.</p>

          <h2>Children’s Privacy</h2>
          <p>If we become aware that personal information from a child has been provided without appropriate parental or guardian consent where required by law, we will take steps to delete such information promptly.</p>

          <h2>Changes to This Policy</h2>
          <p>We may update this Privacy Policy periodically. Significant changes will be communicated through the app or via email. Continued use after updates constitutes acceptance.</p>

          <h2>Contact Us</h2>
          <p>ZAi-Fi Business Solutions<br/>mohamed hanig nager, Villupuram, Tamilnadu<br/>Email: support@neatbro.com<br/>Website: https://neatbro.com</p>

          <div className="mt-6">
            <Button onClick={() => navigate('/')} className="bg-blue-600 text-white">Return Home</Button>
          </div>
        </article>
      </div>
    </div>
  );
}

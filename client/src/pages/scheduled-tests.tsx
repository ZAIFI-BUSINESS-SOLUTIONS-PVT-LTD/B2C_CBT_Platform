import { useState, useEffect } from 'react';
import { useLocation } from 'wouter';
import { Clock, Calendar, BookOpen, Users, PlayCircle, AlertCircle, ArrowLeft, ChevronLeft } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { getAvailablePlatformTests, startPlatformTest } from '@/config/api';
import { PlatformTest, AvailablePlatformTestsResponse } from '@/types/api';
import { useAuth } from '@/contexts/AuthContext';

export default function ScheduledTestsPage() {
  const [platformTests, setPlatformTests] = useState<AvailablePlatformTestsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [startingTest, setStartingTest] = useState<number | null>(null);
  const [showPasscodeModal, setShowPasscodeModal] = useState(false);
  const [passcodeValue, setPasscodeValue] = useState('');
  const [passcodeError, setPasscodeError] = useState<string | null>(null);
  const [pendingTestToStart, setPendingTestToStart] = useState<PlatformTest | null>(null);
  const [showCompletedModal, setShowCompletedModal] = useState(false);
  const [completedSessionInfo, setCompletedSessionInfo] = useState<{ sessionId?: number | null; completedAt?: string | null; message?: string | null }>({ sessionId: null, completedAt: null, message: null });
  const [activeTab, setActiveTab] = useState<'open' | 'upcoming'>('open');
  const { isAuthenticated } = useAuth();
  const [, setLocation] = useLocation();

  useEffect(() => {
    if (!isAuthenticated) {
      setLocation('/login');
      return;
    }

    fetchPlatformTests();
  }, [isAuthenticated, setLocation]);

  const fetchPlatformTests = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getAvailablePlatformTests();
      setPlatformTests(data);
    } catch (err) {
      console.error('Error fetching platform tests:', err);
      setError('Failed to load platform tests. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleStartTest = async (testId: number, passcode?: string) => {
    try {
      setPasscodeError(null);
      setStartingTest(testId);
      const response = await (startPlatformTest as any)({ testId, passcode });
      // Navigate to test interface with session ID
      // Note: wouter does not support navigation state; test page should fetch session by id
      setLocation(`/test/${response.session.id}`);
    } catch (err) {
      console.error('Error starting test:', err);
      // Special-case: backend may return 409 with existing session info when a session already exists
      if (err instanceof Error && /^\s*409\s*:/.test(err.message)) {
        try {
          const bodyText = err.message.replace(/^\s*\d+\s*:\s*/, '');
          const parsed = JSON.parse(bodyText);
          const existingSessionId = parsed.sessionId || (parsed.session && parsed.session.id);
          if (existingSessionId) {
            // Navigate to existing session
            setLocation(`/test/${existingSessionId}`);
            return;
          }
        } catch (parseErr) {
          console.error('Failed to parse 409 response body:', parseErr);
        }
      }

      // If backend returned 403 with "already completed" message, show modal instead of generic error
      if (err instanceof Error && /^\s*403\s*:/.test(err.message)) {
        try {
          const bodyText = err.message.replace(/^\s*\d+\s*:\s*/, '');
          const parsed = JSON.parse(bodyText);
          const completedSessionId = parsed.completed_session_id || parsed.completedSessionId || (parsed.completed_session && parsed.completed_session.id);
          const completedAt = parsed.completed_at || parsed.completedAt || null;
          const message = parsed.error || parsed.message || 'You have already completed this test.';
          setCompletedSessionInfo({ sessionId: completedSessionId ?? null, completedAt: completedAt ?? null, message });
          setShowCompletedModal(true);
          return;
        } catch (parseErr) {
          console.error('Failed to parse 403 response body:', parseErr);
        }
      }

      // If backend returned 401/403 for invalid passcode, surface the error back to the passcode modal
      if (err instanceof Error && (/^\s*401\s*:/.test(err.message) || /^\s*403\s*:/.test(err.message)) && pendingTestToStart) {
        try {
          const bodyText = err.message.replace(/^\s*\d+\s*:\s*/, '');
          const parsed = JSON.parse(bodyText);
          const message = parsed.error || parsed.message || 'Invalid passcode.';
          setPasscodeError(message);
          setShowPasscodeModal(true);
          return;
        } catch (parseErr) {
          console.error('Failed to parse auth error response body:', parseErr);
        }
      }

      setError('Failed to start test. Please try again.');
    } finally {
      setStartingTest(null);
    }
  };

  const formatDateTime = (dateTime: string) => {
    return new Date(dateTime).toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: true
    });
  };

  const getTestStatus = (test: PlatformTest) => {
    if (!test.scheduledDateTime) return 'open';

    const now = new Date();
    const scheduledTime = new Date(test.scheduledDateTime);
    const testEndTime = new Date(scheduledTime.getTime() + (test.timeLimit * 60 * 1000));

    if (now < scheduledTime) return 'upcoming';
    if (now >= scheduledTime && now <= testEndTime) return 'active';
    return 'expired';
  };

  const getStatusBadge = (test: PlatformTest) => {
    const status = getTestStatus(test);

    switch (status) {
      case 'active':
        return <Badge variant="default" className="bg-green-500">Live Now</Badge>;
      case 'upcoming':
        return <Badge variant="secondary">Upcoming</Badge>;
      case 'expired':
        return <Badge variant="destructive">Expired</Badge>;
      case 'open':
        return <Badge variant="outline">Available Anytime</Badge>;
      default:
        return null;
    }
  };

  const requiresPasscode = (test: PlatformTest) => {
    const t = test as any;
    return !!(t.requiresPasscode || t.passcodeRequired || t.requires_passcode || t.passcode_required);
  };

  const isTestAvailable = (test: PlatformTest) => {
    const status = getTestStatus(test);
    return status === 'active' || status === 'open';
  };

  const TestCard = ({ test }: { test: PlatformTest }) => (
    <Card className="h-full shadow-md">
      <CardHeader className="pb-3">
        <div className="flex justify-between items-start">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <CardTitle className="text-base leading-tight">{test.testName}</CardTitle>
              {/* Render exam-type badge if present (try common fields) */}
              {((test as any).examType || (test as any).testType || (test as any).exam_type) && (
                <Badge variant="outline" className="text-xs ml-1 uppercase">{(test as any).examType ?? (test as any).testType ?? (test as any).exam_type}</Badge>
              )}
              {/* Show a small passcode badge if this test requires one */}
              {requiresPasscode(test) && (
                <Badge variant="secondary" className="text-xs ml-1">Passcode</Badge>
              )}
            </div>
            <CardDescription className="mt-1 text-sm">{test.description}</CardDescription>
          </div>
          <div className="ml-2 flex-shrink-0">
            {getStatusBadge(test)}
          </div>
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <div className="space-y-2">
          <div className="flex items-center text-sm text-gray-600">
            <Clock className="w-4 h-4 mr-2 flex-shrink-0" />
            <span className="truncate">{test.timeLimit} minutes</span>
          </div>

          <div className="flex items-center text-sm text-gray-600">
            <BookOpen className="w-4 h-4 mr-2 flex-shrink-0" />
            <span className="truncate">{test.totalQuestions} questions</span>
          </div>

          {test.scheduledDateTime && (
            <div className="flex items-center text-sm text-gray-600">
              <Calendar className="w-4 h-4 mr-2 flex-shrink-0" />
              <span className="truncate">{formatDateTime(test.scheduledDateTime)}</span>
            </div>
          )}

          {test.testType && (
            <div className="flex items-center text-sm text-gray-600">
              <Users className="w-4 h-4 mr-2 flex-shrink-0" />
              <span className="truncate">{test.testType}</span>
            </div>
          )}

          <Button
            onClick={() => {
              if (!isTestAvailable(test)) return;
              // If test requires passcode, open modal to collect it
              if (requiresPasscode(test)) {
                setPendingTestToStart(test);
                setPasscodeValue('');
                setPasscodeError(null);
                setShowPasscodeModal(true);
                return;
              }

              handleStartTest(test.id);
            }}
            disabled={!isTestAvailable(test) || startingTest === test.id}
            className="w-full mt-3 text-sm py-2"
            size="sm"
          >
            {startingTest === test.id ? (
              'Starting...'
            ) : !isTestAvailable(test) ? (
              getTestStatus(test) === 'upcoming' ? 'Not Started Yet' : 'Test Expired'
            ) : (
              <>
                <PlayCircle className="w-4 h-4 mr-2" />
                Start Test
              </>
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  );

  // Safely derive arrays so we don't call .length or .map on undefined (TypeScript safety)
  const scheduledTests = platformTests?.scheduledTests ?? [];
  const openTests = platformTests?.openTests ?? [];
  // Completed tests are identified per-student by platform API which returns `hasCompleted` on each test
  const allScheduled = scheduledTests.filter((t) => !t.hasCompleted);
  const allOpen = openTests.filter((t) => !t.hasCompleted);
  const completedScheduled = scheduledTests.filter((t) => t.hasCompleted);
  const completedOpen = openTests.filter((t) => t.hasCompleted);
  const completedTests = [...completedScheduled, ...completedOpen];

  // Filter tests by status for the new tabs
  const upcomingTests = allScheduled.filter((test) => getTestStatus(test) === 'upcoming');
  const openAvailableTests = allOpen.filter((test) => getTestStatus(test) === 'open');

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 mx-auto"></div>
          <p className="mt-4 text-gray-600 text-sm">Loading platform tests...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
        <div className="max-w-md mx-auto text-center">
          <Alert variant="destructive" className="mb-4">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription className="text-sm">{error}</AlertDescription>
          </Alert>
          <Button onClick={fetchPlatformTests} className="w-full">
            Try Again
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Fixed Header */}
      <div className="fixed top-0 left-0 right-0 z-50 bg-white border-b border-gray-200 p-3 shadow-sm">
        <div className="container mx-auto px-2">
          <div className="max-w-4xl mx-auto">
            <div className="flex items-center">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => window.history.back()}
                className="mr-2 p-2 bg-gray-100"
              >
                <ChevronLeft className="w-4 h-4" />
              </Button>
              <h1 className="text-lg font-bold text-gray-900">Scheduled Tests</h1>
            </div>
          </div>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="sticky top-16 border-b border-gray-200">
        <nav className="flex" aria-label="Tabs">
          <button
            onClick={() => setActiveTab('open')}
            className={`flex-1 flex items-center justify-center gap-2 py-3 px-2 border-b-2 font-medium text-sm transition-colors duration-200 active:bg-gray-50 ${activeTab === 'open'
              ? 'border-blue-500 text-blue-600'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
          >
            <BookOpen className="h-4 w-4" />
            <span>Open Tests</span>
          </button>
          <button
            onClick={() => setActiveTab('upcoming')}
            className={`flex-1 flex items-center justify-center gap-2 py-3 px-2 border-b-2 font-medium text-sm transition-colors duration-200 active:bg-gray-50 ${activeTab === 'upcoming'
              ? 'border-blue-500 text-blue-600'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
          >
            <Calendar className="h-4 w-4" />
            <span>Upcoming Tests</span>
          </button>
        </nav>
      </div>

      <div className="container mx-auto px-4 py-4 pt-16">
        {/* Tab Content */}
        {activeTab === 'open' && (
          <div className="mt-4">
            {openAvailableTests.length > 0 ? (
              <div className="grid grid-cols-1 gap-4">
                {openAvailableTests.map((test) => (
                  <TestCard key={test.id} test={test} />
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <BookOpen className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <h3 className="text-base font-semibold text-gray-900 mb-2">No Open Tests</h3>
                <p className="text-gray-600 text-sm">There are no open tests available at this time.</p>
              </div>
            )}
          </div>
        )}

        {activeTab === 'upcoming' && (
          <div className="mt-4">
            {upcomingTests.length > 0 ? (
              <div className="grid grid-cols-1 gap-4">
                {upcomingTests.map((test) => (
                  <TestCard key={test.id} test={test} />
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <Calendar className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <h3 className="text-base font-semibold text-gray-900 mb-2">No Upcoming Tests</h3>
                <p className="text-gray-600 text-sm">There are no upcoming tests scheduled at this time.</p>
              </div>
            )}
          </div>
        )}

        {/* Completed Test Modal: shown when attempting to start a test already completed by this student */}
        {showCompletedModal && (
          <div className="fixed inset-0 bg-[#0F172A]/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-2xl shadow-2xl p-4 max-w-md mx-auto w-full border-2 border-[#4F83FF]/20">
              <div className="text-center">
                <div className="w-12 h-12 bg-[#FFEDEE] rounded-full flex items-center justify-center mx-auto mb-4">
                  <AlertCircle className="h-6 w-6 text-red-600" />
                </div>
                <h3 className="text-lg font-bold text-[#1F2937] mb-2">You already completed this test</h3>
                <p className="text-[#6B7280] mb-4 text-sm">{completedSessionInfo.message || 'You have already completed this test and cannot retake it.'}</p>

                {completedSessionInfo.sessionId && (
                  <p className="text-sm text-gray-600 mb-4">Completed on: {completedSessionInfo.completedAt ? new Date(completedSessionInfo.completedAt).toLocaleString() : 'N/A'}</p>
                )}

                {/* Passcode Modal: collect passcode when required by test */}
                {showPasscodeModal && pendingTestToStart && (
                  <div className="fixed inset-0 bg-[#0F172A]/50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white rounded-2xl shadow-2xl p-4 max-w-md mx-auto w-full border-2 border-[#E6EEF9]/20">
                      <div className="text-center">
                        <h3 className="text-lg font-bold text-[#1F2937] mb-2">Enter Passcode</h3>
                        <p className="text-[#6B7280] mb-4 text-sm">This test requires a passcode provided by the coaching institute.</p>

                        <div className="mb-3">
                          <input
                            type="password"
                            value={passcodeValue}
                            onChange={(e) => setPasscodeValue(e.target.value)}
                            className="w-full px-3 py-2 border rounded-md text-sm"
                            placeholder="Enter passcode"
                          />
                          {passcodeError && <p className="text-sm text-red-600 mt-2">{passcodeError}</p>}
                        </div>

                        <div className="flex flex-col space-y-2">
                          <Button
                            variant="outline"
                            onClick={() => {
                              setShowPasscodeModal(false);
                              setPasscodeValue('');
                              setPasscodeError(null);
                              setPendingTestToStart(null);
                            }}
                            className="w-full border-[#E2E8F0] text-[#64748B] hover:bg-[#F8FAFC]"
                          >
                            Cancel
                          </Button>
                          <Button
                            onClick={async () => {
                              if (!pendingTestToStart) return;
                              // Keep modal open while validating; startingTest state will show spinner text on button if needed
                              setShowPasscodeModal(false);
                              await handleStartTest(pendingTestToStart.id, passcodeValue);
                              // If there was a passcode error, it will re-open modal via error handling; otherwise clear
                              setPasscodeValue('');
                              setPendingTestToStart(null);
                            }}
                            className="w-full bg-[#4F83FF] hover:bg-[#3B82F6] text-white"
                          >
                            {startingTest === pendingTestToStart.id ? 'Starting...' : 'Start Test'}
                          </Button>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                <div className="flex flex-col space-y-2">
                  <Button
                    variant="outline"
                    onClick={() => setShowCompletedModal(false)}
                    className="w-full border-[#E2E8F0] text-[#64748B] hover:bg-[#F8FAFC]"
                  >
                    Close
                  </Button>
                  <Button
                    onClick={() => {
                      setShowCompletedModal(false);
                      // Navigate back to platform tests listing
                      setLocation('/scheduled-tests');
                    }}
                    className="w-full bg-[#4F83FF] hover:bg-[#3B82F6] text-white"
                  >
                    Back to Tests
                  </Button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

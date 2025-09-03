import { useState, useEffect } from 'react';
import { useLocation } from 'wouter';
import { Clock, Calendar, BookOpen, Users, PlayCircle, AlertCircle } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { getAvailablePlatformTests, startPlatformTest } from '@/config/api';
import { PlatformTest, AvailablePlatformTestsResponse } from '@/types/api';
import { useAuth } from '@/contexts/AuthContext';

export default function ScheduledTestsPage() {
  const [platformTests, setPlatformTests] = useState<AvailablePlatformTestsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [startingTest, setStartingTest] = useState<number | null>(null);
  const [showCompletedModal, setShowCompletedModal] = useState(false);
  const [completedSessionInfo, setCompletedSessionInfo] = useState<{ sessionId?: number | null; completedAt?: string | null; message?: string | null }>({ sessionId: null, completedAt: null, message: null });
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

  const handleStartTest = async (testId: number) => {
    try {
      setStartingTest(testId);
      const response = await startPlatformTest({ testId });
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

  const isTestAvailable = (test: PlatformTest) => {
    const status = getTestStatus(test);
    return status === 'active' || status === 'open';
  };

  const TestCard = ({ test }: { test: PlatformTest }) => (
    <Card className="h-full">
      <CardHeader>
        <div className="flex justify-between items-start">
          <div>
            <CardTitle className="text-lg">{test.testName}</CardTitle>
            <CardDescription className="mt-1">{test.description}</CardDescription>
          </div>
          {getStatusBadge(test)}
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          <div className="flex items-center text-sm text-gray-600">
            <Clock className="w-4 h-4 mr-2" />
            <span>{test.timeLimit} minutes</span>
          </div>
          
          <div className="flex items-center text-sm text-gray-600">
            <BookOpen className="w-4 h-4 mr-2" />
            <span>{test.totalQuestions} questions</span>
          </div>
          
          {test.scheduledDateTime && (
            <div className="flex items-center text-sm text-gray-600">
              <Calendar className="w-4 h-4 mr-2" />
              <span>{formatDateTime(test.scheduledDateTime)}</span>
            </div>
          )}
          
          {test.testType && (
            <div className="flex items-center text-sm text-gray-600">
              <Users className="w-4 h-4 mr-2" />
              <span>{test.testType}</span>
            </div>
          )}
          
          <Button
            onClick={() => handleStartTest(test.id)}
            disabled={!isTestAvailable(test) || startingTest === test.id}
            className="w-full mt-4"
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

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading platform tests...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto px-4 py-8">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
        <Button onClick={fetchPlatformTests} className="mt-4">
          Try Again
        </Button>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Platform Tests</h1>
        <p className="text-gray-600 mt-2">
          Take official practice tests and scheduled examinations
        </p>
      </div>

      <Tabs defaultValue="all" className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="all">All Tests</TabsTrigger>
          <TabsTrigger value="scheduled">Scheduled Tests</TabsTrigger>
          <TabsTrigger value="open">Open Tests</TabsTrigger>
          <TabsTrigger value="completed">Completed</TabsTrigger>
        </TabsList>
        
        <TabsContent value="all" className="mt-6">
          <div className="space-y-6">
            {allScheduled.length > 0 && (
              <div>
                <h2 className="text-xl font-semibold mb-4">Scheduled Tests</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {allScheduled.map((test) => (
                    <TestCard key={test.id} test={test} />
                  ))}
                </div>
              </div>
            )}
            
            {allOpen.length > 0 && (
              <div>
                <h2 className="text-xl font-semibold mb-4">Open Tests</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {allOpen.map((test) => (
                    <TestCard key={test.id} test={test} />
                  ))}
                </div>
              </div>
            )}
            
            {(allScheduled.length === 0 && allOpen.length === 0) && (
              <div className="text-center py-12">
                <BookOpen className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-gray-900 mb-2">No Platform Tests Available</h3>
                <p className="text-gray-600">Check back later for new tests.</p>
              </div>
            )}
          </div>
        </TabsContent>
        
        <TabsContent value="scheduled" className="mt-6">
          {allScheduled.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {allScheduled.map((test) => (
                <TestCard key={test.id} test={test} />
              ))}
            </div>
          ) : (
            <div className="text-center py-12">
              <Calendar className="w-16 h-16 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-gray-900 mb-2">No Scheduled Tests</h3>
              <p className="text-gray-600">There are no scheduled tests at this time.</p>
            </div>
          )}
        </TabsContent>
        
        <TabsContent value="open" className="mt-6">
          {allOpen.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {allOpen.map((test) => (
                <TestCard key={test.id} test={test} />
              ))}
            </div>
          ) : (
            <div className="text-center py-12">
              <BookOpen className="w-16 h-16 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-gray-900 mb-2">No Open Tests</h3>
              <p className="text-gray-600">There are no open tests available at this time.</p>
            </div>
          )}
        </TabsContent>

        <TabsContent value="completed" className="mt-6">
          {completedTests.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {completedTests.map((test) => (
                <Card key={test.id} className="h-full">
                  <CardHeader>
                    <div className="flex justify-between items-start">
                      <div>
                        <CardTitle className="text-lg">{test.testName}</CardTitle>
                        <CardDescription className="mt-1">{test.description}</CardDescription>
                      </div>
                      <Badge variant="outline">Completed</Badge>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      <div className="flex items-center text-sm text-gray-600">
                        <Clock className="w-4 h-4 mr-2" />
                        <span>{test.timeLimit} minutes</span>
                      </div>

                      <div className="flex items-center text-sm text-gray-600">
                        <BookOpen className="w-4 h-4 mr-2" />
                        <span>{test.totalQuestions} questions</span>
                      </div>

                      {test.scheduledDateTime && (
                        <div className="flex items-center text-sm text-gray-600">
                          <Calendar className="w-4 h-4 mr-2" />
                          <span>{formatDateTime(test.scheduledDateTime)}</span>
                        </div>
                      )}

                      <Button onClick={() => setLocation('/test-history')} className="w-full mt-4">
                        View Details
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <div className="text-center py-12">
              <BookOpen className="w-16 h-16 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-gray-900 mb-2">No Completed Tests</h3>
              <p className="text-gray-600">You haven't completed any platform tests yet.</p>
            </div>
          )}
        </TabsContent>
      </Tabs>

      {/* Completed Test Modal: shown when attempting to start a test already completed by this student */}
      {showCompletedModal && (
        <div className="fixed inset-0 bg-[#0F172A]/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-2xl p-6 max-w-md mx-4 border-2 border-[#4F83FF]/20">
            <div className="text-center">
              <div className="w-16 h-16 bg-[#FFEDEE] rounded-full flex items-center justify-center mx-auto mb-4">
                <AlertCircle className="h-8 w-8 text-red-600" />
              </div>
              <h3 className="text-xl font-bold text-[#1F2937] mb-2">You already completed this test</h3>
              <p className="text-[#6B7280] mb-4">{completedSessionInfo.message || 'You have already completed this test and cannot retake it.'}</p>

              {completedSessionInfo.sessionId && (
                <p className="text-sm text-gray-600 mb-4">Completed on: {completedSessionInfo.completedAt ? new Date(completedSessionInfo.completedAt).toLocaleString() : 'N/A'}</p>
              )}

              <div className="flex space-x-3">
                <Button
                  variant="outline"
                  onClick={() => setShowCompletedModal(false)}
                  className="flex-1 border-[#E2E8F0] text-[#64748B] hover:bg-[#F8FAFC]"
                >
                  Close
                </Button>
                <Button
                  onClick={() => {
                    setShowCompletedModal(false);
                    // Navigate back to platform tests listing
                    setLocation('/scheduled-tests');
                  }}
                  className="flex-1 bg-[#4F83FF] hover:bg-[#3B82F6] text-white"
                >
                  Back to Tests
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * PYQs (Previous Year Questions) Page for Students
 * Lists available PYQ papers and allows students to start tests
 */

import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { useLocation } from 'wouter';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useToast } from '@/hooks/use-toast';
import { 
  FileText, 
  Calendar, 
  BookOpen, 
  Play, 
  AlertCircle,
  Loader2
} from 'lucide-react';
import { API_CONFIG } from '@/config/api';
import { authenticatedFetch } from '@/lib/auth';
import MobileDock from '@/components/mobile-dock';
import HeaderDesktop from '@/components/header-desktop';

interface PYQ {
  id: number;
  name: string;
  questionCount: number;  // Changed to camelCase to match API response
  examType: string;       // Changed to camelCase to match API response
  uploadedAt: string;     // Changed to camelCase to match API response
  notes?: string;
  attemptCount: number;   // Changed to camelCase to match API response
}

interface PYQsResponse {
  pyqs: PYQ[];
  totalCount: number;     // Changed to camelCase to match API response
}

interface StartTestResponse {
  message: string;
  // Backend historically returned snake_case (session_id, pyq_info)
  // but some responses (or client-side transforms) may use camelCase.
  session_id?: number;
  sessionId?: number;
  session?: any;
  questions?: any[];
  // pyq_info (snake_case) or pyqInfo (camelCase)
  pyq_info?: {
    pyq_id: number;
    pyq_name: string;
    question_count: number;
    exam_type: string;
    notes?: string;
  };
  pyqInfo?: {
    pyqId: number;
    pyqName: string;
    questionCount: number;
    examType: string;
    notes?: string;
  };
}

export default function PYQsPage() {
  const [, navigate] = useLocation();
  const { toast } = useToast();
  const [startingTest, setStartingTest] = useState<number | null>(null);

  // Debug: Log component mount
  console.log('🚀 PYQsPage component mounted/re-rendered');

  // Fetch available PYQs
  const { data, isLoading, error } = useQuery<PYQsResponse>({
    queryKey: ['/api/pyqs/'],
    queryFn: async () => {
      console.log('🔍 Fetching PYQs from:', `${API_CONFIG.BASE_URL}/api/pyqs/`);
      const response = await authenticatedFetch(`${API_CONFIG.BASE_URL}/api/pyqs/`);
      console.log('📡 PYQ Response status:', response.status);
      if (!response.ok) {
        throw new Error('Failed to fetch PYQs');
      }
      const data = await response.json();
      console.log('✅ PYQ Data received:', data);
      return data;
    },
    staleTime: 0, // Force fresh fetch every time to bypass caching
    refetchOnMount: true,
  });

  // Debug logging
  console.log('PYQ Page State:', { isLoading, hasError: !!error, data });

  const handleStartTest = async (pyqId: number) => {
    setStartingTest(pyqId);

    try {
      console.log('🚀 Starting PYQ test:', pyqId);
      const response = await authenticatedFetch(
        `${API_CONFIG.BASE_URL}/api/pyqs/${pyqId}/start/`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );

      console.log('📡 Start test response status:', response.status);

      if (!response.ok) {
        const errorData = await response.json();
        console.error('❌ Error response:', errorData);
        
        // Handle different error formats
        let errorMessage = 'Failed to start test';
        if (errorData.error) {
          if (typeof errorData.error === 'string') {
            errorMessage = errorData.error;
          } else if (errorData.error.message) {
            errorMessage = errorData.error.message;
          }
        } else if (errorData.message) {
          errorMessage = errorData.message;
        } else if (errorData.detail) {
          errorMessage = errorData.detail;
        }
        
        throw new Error(errorMessage);
      }

      const data: StartTestResponse = await response.json();
      console.log('✅ Test session created:', data);

      // Resolve session id from either snake_case or camelCase or nested session
      const resolvedSessionId = data.session_id ?? data.sessionId ?? data.session?.id;

      // Resolve pyqInfo for toast display (prefer camelCase if available)
      const pyqInfo = data.pyqInfo ?? (data.pyq_info ? {
        pyqId: data.pyq_info.pyq_id,
        pyqName: data.pyq_info.pyq_name,
        questionCount: data.pyq_info.question_count,
        examType: data.pyq_info.exam_type,
        notes: data.pyq_info.notes,
      } : undefined);

      toast({
        title: 'Test Started',
        description: `${pyqInfo?.pyqName ?? 'PYQ'} - ${pyqInfo?.questionCount ?? (data.questions?.length ?? 'Unknown')} questions`,
      });

      // Navigate to test page with resolved session id
      if (resolvedSessionId) {
        navigate(`/test/${resolvedSessionId}`);
      } else {
        throw new Error('Session id missing in response');
      }
    } catch (err: any) {
      console.error('Error starting test:', err);
      toast({
        title: 'Failed to Start Test',
        description: err.message || 'Please try again',
        variant: 'destructive',
      });
    } finally {
      setStartingTest(null);
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  return (
    <>
      {/* Desktop Header */}
      <div className="hidden md:block">
        <HeaderDesktop />
      </div>

      <div className="min-h-screen bg-cover bg-center bg-no-repeat pb-20 md:pb-4" style={{ backgroundImage: "url('/testpage-bg.webp')" }}>
        {/* Hero Section */}
        <div className="bg-gradient-to-r from-blue-600 to-blue-800 text-white py-8 px-4">
          <div className="max-w-6xl mx-auto">
            <h1 className="text-3xl font-bold mb-2">Previous Year Questions</h1>
            <p className="text-blue-100">
              Practice with past exam papers to boost your preparation
            </p>
          </div>
        </div>

        {/* Main Content */}
        <div className="max-w-6xl mx-auto px-4 py-6">
          {/* Loading State */}
          {isLoading && (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
            </div>
          )}

          {/* Error State */}
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                Failed to load PYQs. Please try again later.
              </AlertDescription>
            </Alert>
          )}

          {/* Empty State */}
          {data && data.totalCount === 0 && (
            <Card className="bg-blue-50 rounded-2xl mx-4 overflow-visible" style={{ boxShadow: '0 8px 20px rgba(0,0,0,0.12), 0 2px 6px rgba(0,0,0,0.06)', border: '1px solid rgba(219,234,254,0.9)' }}>
              <CardContent className="p-12 text-center">
                <FileText className="h-12 w-12 text-slate-500 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-slate-900 mb-2">
                  No PYQs Available
                </h3>
                <p className="text-slate-600">
                  Previous year question papers will appear here once they are uploaded.
                </p>
              </CardContent>
            </Card>
          )}

          {/* PYQ Cards */}
          {data && data.totalCount > 0 && (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {data.pyqs.map((pyq) => (
                <Card
                  key={pyq.id}
                  className="bg-blue-50 rounded-2xl overflow-visible hover:shadow-lg transition-shadow duration-200"
                  style={{ boxShadow: '0 8px 20px rgba(0,0,0,0.12), 0 2px 6px rgba(0,0,0,0.06)', border: '1px solid rgba(219,234,254,0.9)' }}
                >
                  <CardContent className="p-6">
                    {/* Header */}
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex-1">
                        <h3 className="font-semibold text-lg text-slate-900 mb-2">
                          {pyq.name}
                        </h3>
                        <div className="flex items-center gap-2 flex-wrap">
                          <Badge variant="outline" className="text-xs">
                            {pyq.examType.toUpperCase()}
                          </Badge>
                          {pyq.attemptCount > 0 && (
                            <Badge variant="secondary" className="text-xs">
                              {pyq.attemptCount} Attempt{pyq.attemptCount !== 1 ? 's' : ''}
                            </Badge>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Metadata */}
                    <div className="space-y-2 mb-4">
                      <div className="flex items-center gap-2 text-sm text-slate-600">
                        <BookOpen className="h-4 w-4" />
                        <span>{pyq.questionCount} Questions</span>
                      </div>
                      {/* Uploaded date removed as requested */}
                    </div>

                    {/* Notes */}
                    {pyq.notes && (
                      <p className="text-sm text-slate-600 mb-4 line-clamp-2">
                        {pyq.notes}
                      </p>
                    )}

                    {/* Start Button */}
                    <Button
                      onClick={() => handleStartTest(pyq.id)}
                      disabled={startingTest === pyq.id}
                      className="w-full bg-blue-600 hover:bg-blue-700 text-white"
                    >
                      {startingTest === pyq.id ? (
                        <>
                          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                          Starting...
                        </>
                      ) : (
                        <>
                          <Play className="h-4 w-4 mr-2" />
                          Start Test
                        </>
                      )}
                    </Button>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}

          {/* Info Card removed as requested */}
        </div>
      </div>

      {/* Mobile Dock */}
      <div className="md:hidden">
        <MobileDock />
      </div>
    </>
  );
}

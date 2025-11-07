import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Loader2, BookOpen, Clock, FileQuestion, AlertCircle, Play } from 'lucide-react';
import { useLocation } from 'wouter';
import { getAccessToken, authenticatedFetch } from '@/lib/auth';

interface Institution {
  id: number;
  name: string;
  code: string;
  exam_types?: string[]; // optional because some payloads may omit this
}

interface InstitutionTest {
  id: number;
  test_name: string;
  test_code: string;
  exam_type: string;
  total_questions: number;
  time_limit: number;
  instructions: string;
  description: string;
  created_at: string;
}

interface InstitutionTestsListProps {
  institution: Institution;
  onBack: () => void;
}

export function InstitutionTestsList({ institution, onBack }: InstitutionTestsListProps) {
  // Normalize exam types to a stable array so TypeScript can reason about length/map safely
  const examTypes: string[] = institution.exam_types ?? ['neet'];
  const [selectedExamType, setSelectedExamType] = useState<string>(examTypes[0]);
  const [tests, setTests] = useState<InstitutionTest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [, setLocation] = useLocation();

  useEffect(() => {
    fetchTests();
  }, [selectedExamType, institution.id]);

  const fetchTests = async () => {
    setLoading(true);
    setError(null);

    try {
      // Use authenticatedFetch which handles token refresh
      const response = await authenticatedFetch(`/api/institutions/${institution.id}/tests/?exam_type=${selectedExamType}`);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.message || 'Failed to fetch tests');
      }

      setTests(data.tests || []);
    } catch (err: any) {
      setError(err.message || 'An error occurred while fetching tests');
    } finally {
      setLoading(false);
    }
  };

  const handleStartTest = async (testId: number) => {
    try {
      // Start test using authenticatedFetch to handle token refresh automatically
      const response = await authenticatedFetch(`/api/platform-tests/${testId}/start/`, { method: 'POST' } as RequestInit);
      const data = await response.json();

      if (!response.ok) {
        // Backend returns standardized AppError shape: { error: { code, message, details } }
        const errCode = data?.error?.code || data?.error;
        const errDetails = data?.error?.details || data?.details;
        if (errDetails?.institution_code_required) {
          throw new Error('Please verify your institution code before starting this test');
        }
        throw new Error(data?.error?.message || data?.message || 'Failed to start test');
      }

      // DEBUG: log response from start endpoint
      console.debug('start test response', data);

      // Navigate to test taking screen with session ID
      const sid = data?.session_id || data?.session?.id || data?.session?.session_id;
      if (sid) {
        // Use wouter navigation setter (app uses Wouter router)
        setLocation(`/test/${sid}`);
      } else {
        console.warn('No session id returned from start endpoint', data);
      }
    } catch (err: any) {
      alert(err.message || 'Failed to start test');
    }
  };

  const formatDuration = (minutes: number) => {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    if (hours > 0) {
      return `${hours}h ${mins}m`;
    }
    return `${mins}m`;
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">{institution.name}</h2>
          <p className="text-sm text-muted-foreground">Institution Tests</p>
        </div>
        <Button variant="outline" onClick={onBack}>
          Back
        </Button>
      </div>

  {examTypes.length > 1 && (
        <div className="flex items-center gap-4">
          <label className="text-sm font-medium">Select Exam:</label>
          <Select value={selectedExamType} onValueChange={setSelectedExamType}>
            <SelectTrigger className="w-[200px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {examTypes.map((exam) => (
                <SelectItem key={exam} value={exam}>
                  {exam.toUpperCase()}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      ) : error ? (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : tests.length === 0 ? (
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            No tests available for {selectedExamType.toUpperCase()} at this time.
          </AlertDescription>
        </Alert>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {tests.map((test) => (
            <Card key={test.id} className="flex flex-col">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <Badge variant="secondary" className="mb-2">
                    {test.exam_type.toUpperCase()}
                  </Badge>
                </div>
                <CardTitle className="line-clamp-2">{test.test_name}</CardTitle>
                {test.description && (
                  <CardDescription className="line-clamp-2">
                    {test.description}
                  </CardDescription>
                )}
              </CardHeader>
              
              <CardContent className="flex-1 space-y-3">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <FileQuestion className="h-4 w-4" />
                  <span>{test.total_questions} Questions</span>
                </div>
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Clock className="h-4 w-4" />
                  <span>{formatDuration(test.time_limit)}</span>
                </div>
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <BookOpen className="h-4 w-4" />
                  <span className="text-xs">{test.test_code}</span>
                </div>
              </CardContent>

              <CardFooter>
                <Button
                  className="w-full"
                  onClick={() => handleStartTest(test.id)}
                >
                  <Play className="mr-2 h-4 w-4" />
                  Start Test
                </Button>
              </CardFooter>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

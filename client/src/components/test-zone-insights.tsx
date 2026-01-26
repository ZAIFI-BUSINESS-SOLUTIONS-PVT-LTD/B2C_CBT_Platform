import { useState, useEffect } from 'react';
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Trophy, Target, TrendingUp, AlertCircle, Loader2, ChevronRight } from "lucide-react";
import { authenticatedFetch } from "@/lib/auth";
import { API_CONFIG } from "@/config/api";

// Type definitions for zone insights
interface ZoneInsight {
  subject: string;
  steady_zone: string[];
  focus_zone: string[];
}

interface SubjectMarks {
  score: number;
  correct: number;
  incorrect: number;
  unanswered: number;
  marks: number;
  max_marks: number;
}

interface TestInfo {
  id: number;
  test_name: string;
  start_time: string;
  end_time: string;
  total_marks: number;
  max_marks: number;
  percentage: number;
  subject_marks: {
    [key: string]: SubjectMarks;
  };
}

interface TestListItem {
  id: number;
  test_name: string;
  test_type: string;
  start_time: string;
  end_time: string;
  total_marks: number;
  max_marks: number;
  total_questions: number;
  correct_answers: number;
  incorrect_answers: number;
  unanswered: number;
}

interface TestZoneInsightsData {
  status: string;
  test_info: TestInfo;
  zone_insights: ZoneInsight[];
  // Accept both snake_case (from some backends) and camelCase (DRF camelCase renderer)
  testInfo?: TestInfo;
  zoneInsights?: ZoneInsight[];
}

export default function TestZoneInsights() {
  const [testList, setTestList] = useState<TestListItem[]>([]);
  const [selectedTestId, setSelectedTestId] = useState<number | null>(null);
  const [testInfo, setTestInfo] = useState<TestInfo | null>(null);
  const [zoneInsights, setZoneInsights] = useState<ZoneInsight[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [testsLoading, setTestsLoading] = useState(true);

  // Fetch test list on mount
  useEffect(() => {
    fetchTestList();
  }, []);

  // Fetch zone insights when test is selected
  useEffect(() => {
    if (selectedTestId) {
      fetchZoneInsights(selectedTestId);
    } else {
      setTestInfo(null);
      setZoneInsights([]);
    }
  }, [selectedTestId]);

  const fetchTestList = async () => {
    try {
      setTestsLoading(true);
      const url = `${API_CONFIG.BASE_URL}/api/zone-insights/tests/`;
      console.log('Fetching test list from:', url);
      const response = await authenticatedFetch(url);

      if (!response.ok) {
        const errorText = await response.text();
        console.error('API Error Response:', response.status, errorText);
        throw new Error(`Failed to fetch test list: ${response.status}`);
      }

      const data = await response.json();
      console.log('Test list API response:', data);
      console.log('Number of tests:', data.tests?.length);
      if (data.tests && data.tests.length > 0) {
        console.log('First test sample:', JSON.stringify(data.tests[0], null, 2));
      }

      // Normalize possible backend response shapes (snake_case or camelCase)
      const normalized = (data.tests || []).map((t: any) => ({
        id: t.id,
        test_name: t.test_name || t.testName || t.get_test_name || t.getTestName || 'Unnamed Test',
        test_type: t.test_type || t.testType || 'custom',
        start_time: t.start_time || t.startTime || null,
        end_time: t.end_time || t.endTime || null,
        total_marks: t.total_marks ?? t.totalMarks ?? t.total_marks_calc ?? t.totalMarksCalc ?? 0,
        max_marks: t.max_marks ?? t.maxMarks ?? 0,
        total_questions: t.total_questions ?? t.totalQuestions ?? 0,
        correct_answers: t.correct_answers ?? t.correctAnswers ?? 0,
        incorrect_answers: t.incorrect_answers ?? t.incorrectAnswers ?? 0,
        unanswered: t.unanswered ?? t.unansweredQuestions ?? t.unansweredQuestions ?? 0
      }));

  setTestList(normalized);
  // Auto-select the most recent test (first in list) when available so
  // the user immediately sees their latest test data. Do not override an
  // existing selection (e.g., if user already picked one).
  setSelectedTestId((prev) => prev ?? (normalized.length > 0 ? normalized[0].id : null));
  setError(null);
    } catch (err) {
      console.error('Error fetching test list:', err);
      setError('Failed to load test list. Please try refreshing the page.');
    } finally {
      setTestsLoading(false);
    }
  };

  const fetchZoneInsights = async (testId: number) => {
    try {
      setLoading(true);
      setError(null);
      const url = `${API_CONFIG.BASE_URL}/api/zone-insights/test/${testId}/`;
      console.log('🔍 Fetching zone insights from:', url);
      const response = await authenticatedFetch(url);

      console.log('📡 API Response status:', response.status, response.ok);
      if (!response.ok) {
        const errorText = await response.text();
        console.error('❌ API Error:', errorText);
        throw new Error('Failed to fetch zone insights');
      }

      const data: TestZoneInsightsData = await response.json();
      console.log('✅ Received data:', JSON.stringify(data, null, 2));
      // Normalize test_info shape (accept camelCase or snake_case)
      // DRF camelCase renderer returns testInfo, zoneInsights
      const ti: any = data.test_info || data.testInfo || {};
      const normalizedTestInfo: TestInfo = {
        id: ti.id,
        test_name: ti.test_name || ti.testName || ti.get_test_name || ti.getTestName || 'Unnamed Test',
        start_time: ti.start_time || ti.startTime || null,
        end_time: ti.end_time || ti.endTime || null,
        total_marks: ti.total_marks ?? ti.totalMarks ?? 0,
        max_marks: ti.max_marks ?? ti.maxMarks ?? 0,
        percentage: ti.percentage ?? 0,
        // Normalize inner subject marks objects (handle camelCase from DRF)
        subject_marks: (() => {
          const raw = ti.subject_marks || ti.subjectMarks || {};
          const normalized: { [k: string]: SubjectMarks } = {};
          Object.entries(raw).forEach(([subj, val]) => {
            const v: any = val || {};
            normalized[subj] = {
              score: v.score ?? v.score ?? 0,
              correct: v.correct ?? v.correct ?? v.correctAnswers ?? v.correct_answers ?? 0,
              incorrect: v.incorrect ?? v.incorrect ?? v.incorrectAnswers ?? v.incorrect_answers ?? 0,
              unanswered: v.unanswered ?? v.unanswered ?? v.unansweredQuestions ?? v.unanswered_questions ?? 0,
              marks: v.marks ?? v.marks ?? 0,
              max_marks: v.max_marks ?? v.maxMarks ?? v.max_marks ?? 0
            };
          });
          return normalized;
        })()
      };

      console.log('📊 Normalized test_info:', normalizedTestInfo);
      setTestInfo(normalizedTestInfo);
      // Primary: use endpoint's zone_insights. If none returned, fetch raw DB-backed insights as fallback.
      // DRF camelCase renderer returns zoneInsights
      const primaryZones = data.zone_insights || data.zoneInsights || [];
      console.log('🎯 Primary zone_insights count:', primaryZones.length);
      if (!primaryZones || primaryZones.length === 0) {
        try {
          console.debug('Primary zone_insights empty — fetching raw DB-backed insights as fallback');
          const rawUrl = `${API_CONFIG.BASE_URL}/api/zone-insights/raw/${testId}/`;
          const rawResp = await authenticatedFetch(rawUrl);
          if (rawResp.ok) {
            const rawData = await rawResp.json();
            console.debug('Raw insights response:', rawData);
            const rawInsights = rawData.raw_insights || rawData.rawInsights || [];
            setZoneInsights(rawInsights.map((r: any) => ({
              subject: r.subject,
              steady_zone: r.steady_zone || r.steadyZone || [],
              focus_zone: r.focus_zone || r.focusZone || []
            })));
          } else {
            console.warn('Raw insights fetch failed', rawResp.status);
            setZoneInsights([]);
          }
        } catch (err) {
          console.error('Error fetching raw insights fallback:', err);
          setZoneInsights([]);
        }
      } else {
        // Normalize camelCase to snake_case for consistency
        const normalized = primaryZones.map((z: any) => ({
          subject: z.subject,
          steady_zone: z.steady_zone || z.steadyZone || [],
          focus_zone: z.focus_zone || z.focusZone || []
        }));
        setZoneInsights(normalized);
      }
    } catch (err) {
      console.error('Error fetching zone insights:', err);
      setError('Failed to load zone insights');
      setTestInfo(null);
      setZoneInsights([]);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString: string | null | undefined) => {
    if (!dateString) {
      return 'No Date';
    }
    
    try {
      const date = new Date(dateString);
      if (isNaN(date.getTime())) {
        return 'Invalid Date';
      }
      
      // Format like Test History: "DD Mon YY" (e.g., "31 Aug 25")
      const day = date.getDate().toString().padStart(2, '0');
      const month = date.toLocaleString('default', { month: 'short' });
      const year = date.getFullYear().toString().slice(-2);
      return `${day} ${month} ${year}`;
    } catch (error) {
      console.error('Error formatting date:', dateString, error);
      return 'Invalid Date';
    }
  };

  const getSubjectColor = (subject: string) => {
    const colors: { [key: string]: string } = {
      'Physics': 'bg-blue-100 text-blue-700 border-blue-300',
      'Chemistry': 'bg-green-100 text-green-700 border-green-300',
      'Botany': 'bg-emerald-100 text-emerald-700 border-emerald-300',
      'Zoology': 'bg-teal-100 text-teal-700 border-teal-300',
      'Math': 'bg-purple-100 text-purple-700 border-purple-300'
    };
    return colors[subject] || 'bg-gray-100 text-gray-700 border-gray-300';
  };

  if (testsLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
        <span className="ml-2 text-gray-600">Loading tests...</span>
      </div>
    );
  }

  if (testList.length === 0) {
    return (
      <Card>
        <CardContent className="p-8 text-center">
          <Trophy className="h-16 w-16 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">No Tests Available</h3>
          <p className="text-gray-600 mb-4">
            Complete a test to see your subject-wise performance insights with AI-powered recommendations.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* Test Selector */}
      <Card>
        <CardContent className="p-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Select a Test to Analyze
          </label>
          <Select
            value={selectedTestId?.toString() || ''}
            onValueChange={(value) => setSelectedTestId(value ? Number(value) : null)}
          >
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Choose a test..." />
            </SelectTrigger>
            <SelectContent>
              {testList.map((test) => {
                const dateStr = formatDate(test.start_time);
                const marks = `${test.total_marks ?? 0}/${test.max_marks ?? 0}`;
                return (
                  <SelectItem key={test.id} value={test.id.toString()}>
                    {test.test_name || 'Unnamed Test'} - {dateStr} ({marks})
                  </SelectItem>
                );
              })}
            </SelectContent>
          </Select>
        </CardContent>
      </Card>

      {/* Loading State */}
      {loading && (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
          <span className="ml-2 text-gray-600">Loading insights...</span>
        </div>
      )}

      {/* Error State */}
      {error && !loading && (
        <Card className="border-red-200 bg-red-50">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 text-red-700">
              <AlertCircle className="h-5 w-5" />
              <p className="font-medium">{error}</p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Test Summary */}
      {testInfo && !loading && (
        <Card className="bg-gradient-to-br from-blue-50 to-indigo-50 border-blue-200">
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-lg font-bold text-gray-900">{testInfo.test_name}</h3>
              <Badge variant="secondary" className="bg-white">
                {testInfo.percentage.toFixed(1)}%
              </Badge>
            </div>

            <div className="grid grid-cols-2 gap-3 mb-3">
              <div className="bg-white rounded-lg p-3 border border-blue-100">
                <p className="text-sm text-gray-600 mb-1">Total Score</p>
                <p className="text-2xl font-bold text-blue-600">
                  {testInfo.total_marks} <span className="text-sm font-normal text-gray-500">/ {testInfo.max_marks}</span>
                </p>
              </div>
              <div className="bg-white rounded-lg p-3 border border-blue-100">
                <p className="text-sm text-gray-600 mb-1">Test Date</p>
                <p className="text-sm font-semibold text-gray-900">
                  {formatDate(testInfo.start_time)}
                </p>
              </div>
            </div>

            {/* Subject Scores (only show subjects present in this test) */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {Object.entries(testInfo.subject_marks)
                .filter(([_, marks]) => {
                  const max = (marks?.max_marks ?? 0);
                  const counts = (marks?.correct ?? 0) + (marks?.incorrect ?? 0) + (marks?.unanswered ?? 0);
                  return max > 0 || counts > 0;
                })
                .map(([subject, marks]) => (
                  <div key={subject} className="bg-white rounded-lg p-2 border border-blue-100">
                    <p className="text-xs text-gray-600">{subject}</p>
            <div className="flex items-baseline gap-1 min-w-0 flex-wrap">
              <p className="text-lg font-bold text-gray-900">{marks.marks}</p>
             <p className="text-xs text-gray-500">/ {marks.max_marks}</p>
              <div className="ml-auto flex items-center gap-2 flex-wrap">
                        {/*
                        {marks.score !== undefined && (
                          <Badge variant="outline" className="text-xs">
                            {marks.score.toFixed(0)}%
                          </Badge>
                        )}
                        */}
                        {/* Small count badges: correct / incorrect / unanswered */}
                        <span className="inline-flex items-center px-2 sm:px-3 py-0.5 sm:py-1 rounded-full text-xs sm:text-sm font-medium bg-green-50 text-green-800 border border-green-100">
                          <svg className="h-3.5 w-3.5 mr-1 text-green-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                            <polyline points="20 6 9 17 4 12" />
                          </svg>
                          {marks.correct ?? 0}
                        </span>

                        <span className="inline-flex items-center px-2 sm:px-3 py-0.5 sm:py-1 rounded-full text-xs sm:text-sm font-medium bg-red-50 text-red-800 border border-red-100">
                          <svg className="h-3.5 w-3.5 mr-1 text-red-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                            <line x1="18" y1="6" x2="6" y2="18" />
                            <line x1="6" y1="6" x2="18" y2="18" />
                          </svg>
                          {marks.incorrect ?? 0}
                        </span>

                        <span className="inline-flex items-center px-2 sm:px-3 py-0.5 sm:py-1 rounded-full text-xs sm:text-sm font-medium bg-gray-50 text-gray-800 border border-gray-100">
                          {/* Outlined ring-style circle for 'unanswered' (better visual than a filled dot) - now grey */}
                          <svg className="h-3.5 w-3.5 mr-1 text-gray-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                            <circle cx="12" cy="12" r="7" />
                            <circle cx="12" cy="12" r="3" fill="currentColor" className="text-gray-600" />
                          </svg>
                          {marks.unanswered ?? 0}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Zone Insights - Subject Cards */}
      {zoneInsights.length > 0 && !loading && (
        <div className="space-y-4">
          <h3 className="text-lg font-bold text-gray-900 px-1">Subject-Wise Performance Zones</h3>

          {zoneInsights.map((insight) => (
            <Card key={insight.subject} className="overflow-hidden">
              <div className={`${getSubjectColor(insight.subject)} border-b-2 px-4 py-2`}>
                <h4 className="font-bold text-lg">{insight.subject}</h4>
              </div>

              <CardContent className="p-0">
                {/* Steady Zone */}
                <div className="p-4 border-b bg-green-50/50">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="bg-green-500 rounded-full p-1">
                      <Target className="h-4 w-4 text-white" />
                    </div>
                    <h5 className="font-semibold text-green-800">Steady Zone</h5>
                    <Badge variant="outline" className="ml-auto text-xs bg-green-100 text-green-700 border-green-300">
                      Strong Areas
                    </Badge>
                  </div>
                  <ul className="space-y-2">
                    {insight.steady_zone.map((point, idx) => (
                      <li key={idx} className="flex items-start gap-2">
                        <ChevronRight className="h-4 w-4 text-green-600 mt-0.5 flex-shrink-0" />
                        <span className="text-sm text-gray-700 leading-relaxed">{point}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Focus Zone */}
                <div className="p-4 bg-red-50/50">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="bg-red-500 rounded-full p-1">
                      <AlertCircle className="h-4 w-4 text-white" />
                    </div>
                    <h5 className="font-semibold text-red-800">Focus Zone</h5>
                    <Badge variant="outline" className="ml-auto text-xs bg-red-100 text-red-700 border-red-300">
                      Priority Areas
                    </Badge>
                  </div>
                  <ul className="space-y-2">
                    {insight.focus_zone.map((point, idx) => (
                      <li key={idx} className="flex items-start gap-2">
                        <ChevronRight className="h-4 w-4 text-red-600 mt-0.5 flex-shrink-0" />
                        <span className="text-sm text-gray-700 leading-relaxed">{point}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* No Test Selected */}
      {!selectedTestId && !loading && (
        <Card>
          <CardContent className="p-8 text-center">
            <Target className="h-16 w-16 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Select a Test to Begin</h3>
            <p className="text-gray-600">
              Choose a test from the dropdown above to see detailed subject-wise performance insights with AI-powered recommendations.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

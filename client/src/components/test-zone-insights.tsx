import { useState, useEffect } from 'react';
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Trophy, AlertTriangle, CheckCircle, Loader2, ChevronRight, Target } from "lucide-react";
import { authenticatedFetch } from "@/lib/auth";
import { API_CONFIG } from "@/config/api";

// Type definitions for checkpoint insights
interface Checkpoint {
  topic: string;
  subject: string;
  subtopic: string;
  accuracy: number;
  checklist: string;
  actionPlan: string;
  citation: number[];
}

interface SubjectCheckpoints {
  subject: string;
  checkpoints: Checkpoint[];
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

interface TestCheckpointsData {
  status: string;
  test_info: TestInfo;
  checkpoints: SubjectCheckpoints[];
}

export default function TestZoneInsights() {
  const [testList, setTestList] = useState<TestListItem[]>([]);
  const [selectedTestId, setSelectedTestId] = useState<number | null>(null);
  const [testInfo, setTestInfo] = useState<TestInfo | null>(null);
  const [subjectCheckpoints, setSubjectCheckpoints] = useState<SubjectCheckpoints[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [testsLoading, setTestsLoading] = useState(true);

  // Fetch test list on mount
  useEffect(() => {
    fetchTestList();
  }, []);

  // Fetch checkpoints when test is selected
  useEffect(() => {
    if (selectedTestId) {
      fetchCheckpoints(selectedTestId);
    } else {
      setTestInfo(null);
      setSubjectCheckpoints([]);
    }
  }, [selectedTestId]);

  const fetchTestList = async () => {
    try {
      setTestsLoading(true);
      const url = `${API_CONFIG.BASE_URL}/api/zone-insights/tests/`;
      const response = await authenticatedFetch(url);

      if (!response.ok) {
        throw new Error(`Failed to fetch test list: ${response.status}`);
      }

      const data = await response.json();
      const normalized = (data.tests || []).map((t: any) => ({
        id: t.id,
        test_name: t.test_name || t.testName || 'Unnamed Test',
        test_type: t.test_type || t.testType || 'custom',
        start_time: t.start_time || t.startTime || null,
        end_time: t.end_time || t.endTime || null,
        total_marks: t.total_marks ?? t.totalMarks ?? 0,
        max_marks: t.max_marks ?? t.maxMarks ?? 0,
        total_questions: t.total_questions ?? t.totalQuestions ?? 0,
        correct_answers: t.correct_answers ?? t.correctAnswers ?? 0,
        incorrect_answers: t.incorrect_answers ?? t.incorrectAnswers ?? 0,
        unanswered: t.unanswered ?? 0
      }));

      setTestList(normalized);
      setSelectedTestId((prev) => prev ?? (normalized.length > 0 ? normalized[0].id : null));
      setError(null);
    } catch (err) {
      console.error('Error fetching test list:', err);
      setError('Failed to load test list. Please try refreshing the page.');
    } finally {
      setTestsLoading(false);
    }
  };

  const fetchCheckpoints = async (testId: number) => {
    try {
      setLoading(true);
      setError(null);
      const url = `${API_CONFIG.BASE_URL}/api/zone-insights/test/${testId}/`;
      const response = await authenticatedFetch(url);

      if (!response.ok) {
        throw new Error('Failed to fetch checkpoints');
      }

      const data: TestCheckpointsData = await response.json();
      
      // DEBUG: Log raw API response
      console.log('API Response:', JSON.stringify(data, null, 2));
      if (data.checkpoints && data.checkpoints.length > 0) {
        console.log('First checkpoint:', data.checkpoints[0]);
        if (data.checkpoints[0].checkpoints && data.checkpoints[0].checkpoints.length > 0) {
          console.log('First item actionPlan:', data.checkpoints[0].checkpoints[0].actionPlan);
        }
      }
      
      // Normalize test_info - handle both camelCase and snake_case from backend
      const ti: any = data.test_info || data.testInfo || {};
      const normalizedTestInfo: TestInfo = {
        id: ti.id,
        test_name: ti.test_name || ti.testName || 'Unnamed Test',
        start_time: ti.start_time || ti.startTime || null,
        end_time: ti.end_time || ti.endTime || null,
        total_marks: ti.total_marks ?? ti.totalMarks ?? 0,
        max_marks: ti.max_marks ?? ti.maxMarks ?? 0,
        percentage: ti.percentage ?? 0,
        subject_marks: (() => {
          const raw = ti.subject_marks || ti.subjectMarks || {};
          const normalized: { [k: string]: SubjectMarks } = {};
          Object.entries(raw).forEach(([subj, val]) => {
            const v: any = val || {};
            normalized[subj] = {
              score: v.score ?? 0,
              correct: v.correct ?? 0,
              incorrect: v.incorrect ?? 0,
              unanswered: v.unanswered ?? 0,
              marks: v.marks ?? 0,
              max_marks: v.max_marks ?? v.maxMarks ?? 0
            };
          });
          return normalized;
        })()
      };

      setTestInfo(normalizedTestInfo);
      setSubjectCheckpoints(data.checkpoints || []);
    } catch (err) {
      console.error('Error fetching checkpoints:', err);
      setError('Failed to load checkpoints');
      setTestInfo(null);
      setSubjectCheckpoints([]);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString: string | null | undefined) => {
    if (!dateString) return 'No Date';
    
    try {
      const date = new Date(dateString);
      if (isNaN(date.getTime())) return 'Invalid Date';
      
      const day = date.getDate().toString().padStart(2, '0');
      const month = date.toLocaleString('default', { month: 'short' });
      const year = date.getFullYear().toString().slice(-2);
      return `${day} ${month} ${year}`;
    } catch (error) {
      return 'Invalid Date';
    }
  };

  const getSubjectColor = (subject: string) => {
    const colors: { [key: string]: string } = {
      'Physics': 'bg-blue-100 text-blue-700 border-blue-300',
      'Chemistry': 'bg-green-100 text-green-700 border-green-300',
      'Botany': 'bg-emerald-100 text-emerald-700 border-emerald-300',
      'Zoology': 'bg-teal-100 text-teal-700 border-teal-300',
      'Math': 'bg-purple-100 text-purple-700 border-purple-300',
      'Biology': 'bg-lime-100 text-lime-700 border-lime-300'
    };
    return colors[subject] || 'bg-gray-100 text-gray-700 border-gray-300';
  };

  const getAccuracyColor = (accuracy: number) => {
    if (accuracy >= 0.7) return 'text-green-600';
    if (accuracy >= 0.5) return 'text-yellow-600';
    return 'text-red-600';
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
            Complete a test to see your performance analysis with AI-powered checkpoints.
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
              <AlertTriangle className="h-5 w-5" />
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

            {/* Subject Scores */}
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
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-50 text-green-800 border border-green-100">
                          <CheckCircle className="h-3.5 w-3.5 mr-1" />
                          {marks.correct ?? 0}
                        </span>
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-50 text-red-800 border border-red-100">
                          ✕ {marks.incorrect ?? 0}
                        </span>
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-50 text-gray-800 border border-gray-100">
                          ○ {marks.unanswered ?? 0}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Checkpoints - Subject Cards */}
      {subjectCheckpoints.length > 0 && !loading && (
        <div className="space-y-4">
          <h3 className="text-lg font-bold text-gray-900 px-1">Subject-Wise Performance Checkpoints</h3>

          {subjectCheckpoints.map((subjectData) => (
            <Card key={subjectData.subject} className="overflow-hidden">
              <div className={`${getSubjectColor(subjectData.subject)} border-b-2 px-4 py-2`}>
                <h4 className="font-bold text-lg">{subjectData.subject}</h4>
              </div>

              <CardContent className="p-4 space-y-4">
                {subjectData.checkpoints.map((checkpoint, idx) => (
                  <div key={idx} className="border rounded-lg p-4 bg-gray-50">
                    {/* Topic Header */}
                    <div className="flex items-center justify-between mb-3">
                      <div>
                        <h5 className="font-semibold text-gray-900">{checkpoint.topic}</h5>
                        <p className="text-xs text-gray-600">{checkpoint.subtopic}</p>
                      </div>
                      <Badge variant="outline" className={`${getAccuracyColor(checkpoint.accuracy)} border-current`}>
                        {(checkpoint.accuracy * 100).toFixed(0)}%
                      </Badge>
                    </div>

                    {/* Checklist - What went wrong */}
                    <div className="mb-3 p-3 bg-red-50 rounded-lg border border-red-200">
                      <div className="flex items-start gap-2">
                        <AlertTriangle className="h-4 w-4 text-red-600 mt-0.5 flex-shrink-0" />
                        <div className="flex-1">
                          <p className="text-xs font-semibold text-red-800 mb-1">Problem Identified:</p>
                          <p className="text-sm text-gray-700">{checkpoint.checklist}</p>
                        </div>
                      </div>
                    </div>

                    {/* Action Plan - How to fix it */}
                    <div className="p-3 bg-green-50 rounded-lg border border-green-200">
                      <div className="flex items-start gap-2">
                        <Target className="h-4 w-4 text-green-600 mt-0.5 flex-shrink-0" />
                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-semibold text-green-800 mb-1">Action Plan:</p>
                          <p className="text-sm text-gray-900 leading-relaxed whitespace-normal break-words">{checkpoint.actionPlan}</p>
                        </div>
                      </div>
                    </div>

                    {/* Citation */}
                    {checkpoint.citation && checkpoint.citation.length > 0 && (
                      <div className="mt-2 text-xs text-gray-500">
                        Based on questions: {checkpoint.citation.join(', ')}
                      </div>
                    )}
                  </div>
                ))}
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
              Choose a test from the dropdown above to see detailed performance checkpoints with AI-powered recommendations.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

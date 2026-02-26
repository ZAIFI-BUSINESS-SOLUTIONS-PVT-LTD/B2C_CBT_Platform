import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Eye, Loader2, AlertCircle, AlertTriangle, Lightbulb, BookOpen } from "lucide-react";
import { authenticatedFetch } from "@/lib/auth";
import { API_CONFIG } from "@/config/api";

export interface ResultsDisplayProps {
  results: {
    sessionId?: number;
    totalQuestions: number;
    correctAnswers: number;
    incorrectAnswers: number;
    unansweredQuestions: number;
    scorePercentage: number;
    timeTaken: number;
    subjectPerformance: Array<{ subject: string; correct: number; total: number }>;
    detailedAnswers: Array<{
      questionId: number;
      question: string;
      selectedAnswer: string | null;
      correctAnswer: string;
      isCorrect: boolean;
      explanation: string;
      optionA: string;
      optionB: string;
      optionC: string;
      optionD: string;
      markedForReview: boolean;
    }>;
  };
  onReviewClick?: () => void;
}

interface SubjectMetrics {
  subject: string;
  correct: number;
  incorrect: number;
  skipped: number;
  total: number;
  marks: number;
  maxMarks: number;
}

interface ZoneInsightsData {
  status: string;
  testInfo?: {
    totalMarks: number;
    maxMarks: number;
    percentage: number;
    subjectMarks: {
      [key: string]: {
        correct: number;
        incorrect: number;
        unanswered: number;
        marks: number;
        maxMarks: number;
      };
    };
    timeSpent?: {
      totalTimeSpent: number;
      correctTimeSpent: number;
      incorrectTimeSpent: number;
      skippedTimeSpent: number;
    };
  };
  test_info?: {
    total_marks: number;
    max_marks: number;
    percentage: number;
    subject_marks: {
      [key: string]: {
        correct: number;
        incorrect: number;
        unanswered: number;
        marks: number;
        max_marks: number;
      };
    };
    time_spent?: {
      total_time_spent: number;
      correct_time_spent: number;
      incorrect_time_spent: number;
      skipped_time_spent: number;
    };
  };
  subjectWiseData?: Array<{
    subjectName: string;
    totalQuestions: number;
    correctAnswers: number;
    incorrectAnswers: number;
    skippedAnswers: number;
    totalMark: number;
    marks: number;
    accuracy: number;
  }>;
  subject_wise_data?: Array<{
    subject_name: string;
    total_questions: number;
    correct_answers: number;
    incorrect_answers: number;
    skipped_answers: number;
    total_mark: number;
    marks: number;
    accuracy: number;
  }>;
}

export function ResultsDisplay({ results, onReviewClick }: ResultsDisplayProps) {
  const [zoneInsights, setZoneInsights] = useState<ZoneInsightsData | null>(null);
  const [selectedSubject, setSelectedSubject] = useState<string>("Overall");
  const [loading, setLoading] = useState(true);
  const [advancedMetrics, setAdvancedMetrics] = useState<any>(null);
  const [advancedLoading, setAdvancedLoading] = useState(false);
  const [selectedMistake, setSelectedMistake] = useState<any>(null);
  const [showMistakeDialog, setShowMistakeDialog] = useState(false);

  useEffect(() => {
    if (results.sessionId) {
      fetchZoneInsights(results.sessionId);
      fetchAdvancedMetrics(results.sessionId);
    }
  }, [results.sessionId]);

  const fetchZoneInsights = async (sessionId: number) => {
    try {
      setLoading(true);
      const url = `${API_CONFIG.BASE_URL}/api/zone-insights/test/${sessionId}/`;
      const response = await authenticatedFetch(url);

      if (!response.ok) {
        throw new Error('Failed to fetch zone insights');
      }

      const data: ZoneInsightsData = await response.json();
      console.log('Zone Insights Data:', data);
      setZoneInsights(data);
    } catch (error) {
      console.error('Error fetching zone insights:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchAdvancedMetrics = async (sessionId: number) => {
    try {
      setAdvancedLoading(true);
      const url = `${API_CONFIG.BASE_URL}/api/zone-insights/advanced/${sessionId}/`;
      const response = await authenticatedFetch(url);

      if (!response.ok) {
        throw new Error('Failed to fetch advanced metrics');
      }

      const data = await response.json();
      console.log('Advanced Metrics Data:', data);

      // Normalize camelCase/snake_case from API
      const testType = data.testType || data.test_type;
      const isReady = data.isReady ?? data.is_ready;
      const gPhrase = data.gPhrase || data.g_phrase;
      const focusZone = data.focusZone || data.focus_zone;
      const repeatedMistakes = data.repeatedMistakes || data.repeated_mistakes;

      // Skip polling for custom tests
      if (testType === 'custom') {
        setAdvancedLoading(false);
        return;
      }

      if (isReady) {
        setAdvancedMetrics({
          is_ready: isReady,
          g_phrase: gPhrase,
          focus_zone: focusZone,
          repeated_mistakes: repeatedMistakes,
        });
        setAdvancedLoading(false);
      } else {
        // Poll every 3 seconds until data is ready
        setTimeout(() => {
          fetchAdvancedMetrics(sessionId);
        }, 3000);
      }
    } catch (error) {
      console.error('Error fetching advanced metrics:', error);
      setAdvancedLoading(false);
    }
  };

  // Normalize data from either camelCase or snake_case
  const testInfo = zoneInsights?.testInfo || zoneInsights?.test_info;
  const subjectMarks = testInfo?.subjectMarks || testInfo?.subject_marks || {};
  const timeSpent = testInfo?.timeSpent || testInfo?.time_spent;
  const subjectWiseData = zoneInsights?.subjectWiseData || zoneInsights?.subject_wise_data || [];
  const zoneSubjects = (zoneInsights as any)?.subjects || [];
  
  console.log('Zone insights:', zoneInsights);
  console.log('Subject wise data:', subjectWiseData);
  console.log('Zone subjects:', zoneSubjects);
  console.log('Subject marks:', subjectMarks);
  
  const totalMarks = testInfo?.totalMarks ?? testInfo?.total_marks ?? (results.correctAnswers * 4 - results.incorrectAnswers * 1);
  const maxMarks = testInfo?.maxMarks ?? testInfo?.max_marks ?? (results.totalQuestions * 4);
  const accuracy = testInfo?.percentage ?? ((results.correctAnswers / results.totalQuestions) * 100);

  // Format time from seconds to readable format
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    if (mins === 0) {
      return `${secs} sec`;
    }
    if (secs === 0) {
      return `${mins} min`;
    }
    return `${mins} min ${secs} sec`;
  };

  // Get overall metrics
  const overallMetrics = {
    correct: results.correctAnswers,
    incorrect: results.incorrectAnswers,
    unanswered: results.unansweredQuestions,
    total: results.totalQuestions
  };

  // Get subject-specific metrics
  const getSubjectMetrics = (): { correct: number; incorrect: number; unanswered: number } => {
    if (selectedSubject === "Overall") {
      return overallMetrics;
    }
    
    console.log('Getting metrics for subject:', selectedSubject);

    // 1) Try subjectMarks from testInfo (object keyed by subject)
    const subjectData = subjectMarks[selectedSubject];
    if (subjectData) {
      console.log('Found in subjectMarks:', subjectData);
      return {
        correct: subjectData.correct ?? subjectData.correct_answers ?? 0,
        incorrect: subjectData.incorrect ?? subjectData.incorrect_answers ?? 0,
        unanswered: subjectData.unanswered ?? subjectData.skipped_answers ?? 0
      };
    }

    // 2) Try zoneInsights.subjects array (each item contains subject and subjectData)
    if (Array.isArray(zoneSubjects) && zoneSubjects.length > 0) {
      const zs = zoneSubjects.find((s: any) => {
        const name = s.subject || (s.subjectData && (s.subjectData.subjectName || s.subjectData.subject_name));
        return name === selectedSubject;
      });
      if (zs) {
        const sd = zs.subjectData || zs.subject_data || {};
        console.log('Found in zoneSubjects:', sd);
        return {
          correct: sd.correctAnswers ?? sd.correct_answers ?? sd.correct ?? 0,
          incorrect: sd.incorrectAnswers ?? sd.incorrect_answers ?? sd.incorrect ?? 0,
          unanswered: sd.skippedAnswers ?? sd.skipped_answers ?? sd.skippedAnswers ?? sd.skippedAnswers ?? sd.unanswered ?? 0
        };
      }
    }

    // 3) Fallback to subjectWiseData array
    const subjectItem = subjectWiseData.find((s: any) => 
      (s.subjectName || s.subject_name) === selectedSubject
    );
    if (subjectItem) {
      console.log('Found in subjectWiseData:', subjectItem);
      return {
        correct: subjectItem.correctAnswers ?? subjectItem.correct_answers ?? 0,
        incorrect: subjectItem.incorrectAnswers ?? subjectItem.incorrect_answers ?? 0,
        unanswered: subjectItem.skippedAnswers ?? subjectItem.skipped_answers ?? 0
      };
    }

    console.log('No data found for subject:', selectedSubject);
    return { correct: 0, incorrect: 0, unanswered: 0 };
  };

  const currentMetrics = getSubjectMetrics();
  
  // Get time breakdown - use zone insights data
  const totalTimeSpent = timeSpent?.totalTimeSpent ?? timeSpent?.total_time_spent ?? 0;
  const correctTimeSpent = timeSpent?.correctTimeSpent ?? timeSpent?.correct_time_spent ?? 0;
  const incorrectTimeSpent = timeSpent?.incorrectTimeSpent ?? timeSpent?.incorrect_time_spent ?? 0;
  const skippedTimeSpent = timeSpent?.skippedTimeSpent ?? timeSpent?.skipped_time_spent ?? 0;

  // Calculate percentages for time bars
  const correctTimePercent = totalTimeSpent > 0 ? (correctTimeSpent / totalTimeSpent) * 100 : 0;
  const incorrectTimePercent = totalTimeSpent > 0 ? (incorrectTimeSpent / totalTimeSpent) * 100 : 0;
  const skippedTimePercent = totalTimeSpent > 0 ? (skippedTimeSpent / totalTimeSpent) * 100 : 0;

  // Build subjects list from zoneInsights.subjects, subjectWiseData or subjectMarks
  let availableSubjects: string[] = [];

  // 1) Prefer zoneInsights.subjects array
  if (Array.isArray(zoneSubjects) && zoneSubjects.length > 0) {
    availableSubjects = zoneSubjects.map((s: any) => s.subject || (s.subjectData && (s.subjectData.subjectName || s.subjectData.subject_name))).filter(Boolean);
  }

  // 2) Try subjectWiseData next
  if (availableSubjects.length === 0 && Array.isArray(subjectWiseData) && subjectWiseData.length > 0) {
    availableSubjects = subjectWiseData.map((s: any) => s.subjectName || s.subject_name).filter(Boolean);
  }

  // 3) Fallback to subjectMarks keys
  if (availableSubjects.length === 0 && subjectMarks) {
    availableSubjects = Object.keys(subjectMarks);
  }
  
  console.log('Available subjects:', availableSubjects);
  
  const subjects = ["Overall", ...availableSubjects];

  return (
    <div 
      className="min-h-screen pb-6 pt-4 px-4 bg-cover bg-center bg-no-repeat"
      style={{
        backgroundImage: 'url(/testpage-bg.png)'
      }}
    >
      <div className="max-w-2xl mx-auto space-y-4">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="text-center">
              <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
              <p className="text-gray-600">Loading detailed insights...</p>
            </div>
          </div>
        ) : (
          <>
            {/* Penguin Card with Marks - use mark-bg.png as full card background */}
            <Card
              className="rounded-2xl border border-[#E2E8F0] bg-transparent"
              style={{
                backgroundImage: "url('/mark-bg.png')",
                backgroundRepeat: 'no-repeat',
                backgroundPosition: 'center',
                backgroundSize: 'cover'
              }}
            >
            <CardContent className="p-3">
            {/* Top Section: Summary (Attempted, Marks, Accuracy) without icons */}
            <div className="flex items-center justify-between mb-4">
              {/* Left: Attempted */}
              <div
                className="flex flex-col items-center -ml-1 -mt-19"
                style={{
                  backgroundImage: "url('/clock.png')",
                  backgroundRepeat: 'no-repeat',
                  backgroundPosition: 'center 6px',
                  backgroundSize: '65px',
                  paddingTop: '130px'
                }}
              >
                <div className="text-2xl font-bold text-gray-800 -mt-14">
                  {results.totalQuestions - results.unansweredQuestions}
                  <span className="text-lg text-gray-500">/{results.totalQuestions}</span>
                </div>
                <div className="text-xs text-gray-600 -mt-1">Attempted</div>
              </div>

              {/* Center: Marks Obtained */}
                <div
                  className="flex flex-col items-center flex-1 mx-4 bg-no-repeat bg-center -mt-16"
                  style={{ backgroundImage: "url('/score.png')", backgroundRepeat: 'no-repeat', backgroundPosition: 'center 6px', backgroundSize: '220px' }}
                >
                  <div className="text-3xl font-bold text-white mt-40">
                    {totalMarks}
                    <span className="text-xl text-white/90">/{maxMarks}</span>
                  </div>
                </div>

              {/* Right: Accuracy */}
              <div
                className="flex flex-col items-center -mr-1 -mt-12"
                style={{
                  backgroundImage: "url('/target.png')",
                  backgroundRepeat: 'no-repeat',
                  backgroundPosition: 'center 6px',
                  backgroundSize: '60px',
                  paddingTop: '100px'
                }}
              >
                <div className="text-2xl font-bold text-gray-800 mt-1">
                  {accuracy.toFixed(0)}%
                </div>
                <div className="text-xs text-gray-600 -mt-1">Accuracy</div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Subject-wise Breakdown */}
        <Card className="bg-white rounded-2xl border border-[#E2E8F0] shadow-lg">
          <CardContent className="p-4">
            <div className="mb-3">
              <div className="text-sm font-semibold text-gray-700 mb-2">Subject-wise Breakdown</div>
              <div className="flex gap-2 flex-wrap">
                {subjects.map((subject) => (
                  <button
                    key={subject}
                    onClick={() => setSelectedSubject(subject)}
                    className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                      selectedSubject === subject
                        ? 'bg-blue-500 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    {subject}
                  </button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-3 gap-3">
              <div className="text-center p-3 bg-green-50 rounded-lg border border-green-200">
                <div className="text-2xl font-bold text-green-700">{currentMetrics.correct}</div>
                <div className="text-xs text-green-700 font-medium">Correct</div>
              </div>
              <div className="text-center p-3 bg-red-50 rounded-lg border border-red-200">
                <div className="text-2xl font-bold text-red-700">{currentMetrics.incorrect}</div>
                <div className="text-xs text-red-700 font-medium">Incorrect</div>
              </div>
              <div className="text-center p-3 bg-amber-50 rounded-lg border border-amber-200">
                <div className="text-2xl font-bold text-amber-700">{currentMetrics.unanswered}</div>
                <div className="text-xs text-amber-700 font-medium">Unattempted</div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Detailed Analysis - Time Breakdown */}
        <Card className="bg-white rounded-2xl border border-[#E2E8F0] shadow-lg">
          <CardContent className="p-4">
            <div className="text-sm font-semibold text-gray-700 mb-3">Detailed Analysis</div>
            
            <div className="space-y-3">
              {/* Total Time */}
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-700">Total Time Taken: {formatTime(totalTimeSpent)}</span>
                <span className="text-sm font-semibold text-gray-800">{formatTime(totalTimeSpent)}</span>
              </div>

              {/* Time on Correct */}
              <div>
                <div className="flex justify-between items-center mb-1">
                  <span className="text-xs text-gray-600">Time Spent on Correct</span>
                  <span className="text-xs font-semibold text-green-700">{formatTime(correctTimeSpent)}</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div 
                    className="bg-green-500 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${correctTimePercent}%` }}
                  />
                </div>
              </div>

              {/* Time on Incorrect */}
              <div>
                <div className="flex justify-between items-center mb-1">
                  <span className="text-xs text-gray-600">Time Spent on Incorrect</span>
                  <span className="text-xs font-semibold text-red-700">{formatTime(incorrectTimeSpent)}</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div 
                    className="bg-red-500 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${incorrectTimePercent}%` }}
                  />
                </div>
              </div>

              {/* Time on Unattempted */}
              <div>
                <div className="flex justify-between items-center mb-1">
                  <span className="text-xs text-gray-600">Time Spent on Unattempted</span>
                  <span className="text-xs font-semibold text-amber-700">{formatTime(skippedTimeSpent)}</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div 
                    className="bg-amber-500 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${skippedTimePercent}%` }}
                  />
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Advanced Metrics Sections */}
        {advancedLoading ? (
          <Card className="bg-white rounded-2xl border border-[#E2E8F0] shadow-lg">
            <CardContent className="p-6">
              <div className="flex items-center justify-center space-x-3">
                <Loader2 className="h-5 w-5 animate-spin text-purple-600" />
                <span className="text-sm text-gray-600">Loading advanced insights...</span>
              </div>
            </CardContent>
          </Card>
        ) : advancedMetrics && advancedMetrics.is_ready ? (
          <>
            {/* G-Phrase Section (transparent, no icon/title) */}
            {advancedMetrics.g_phrase && (
              <Card className="bg-white rounded-xl border border-[#E2E8F0] shadow-lg">
                <CardContent className="p-4">
                  <p className="text-sm text-gray-700 italic leading-relaxed">
                    "{advancedMetrics.g_phrase}"
                  </p>
                </CardContent>
              </Card>
            )}

            {/* Focus Zone Section */}
            {advancedMetrics.focus_zone && Object.keys(advancedMetrics.focus_zone).length > 0 && (
              <Card className="bg-white rounded-xl border border-[#E2E8F0] shadow-lg">
                <CardContent className="p-0">
                  <div className="px-4 py-3 flex items-center justify-between border-b border-gray-100 bg-gradient-to-r from-blue-50 to-indigo-50">
                    <div className="flex items-center space-x-2">
                      <div className="p-1.5 bg-blue-100 rounded-lg">
                        <AlertCircle className="h-4 w-4 text-blue-700" />
                      </div>
                      <div className="text-sm font-bold text-blue-900">Performance Report</div>
                    </div>
                    <div className="text-xs text-blue-700 font-medium">
                      {Object.keys(advancedMetrics.focus_zone).length} insight{Object.keys(advancedMetrics.focus_zone).length > 1 ? 's' : ''}
                    </div>
                  </div>
                  <div className="divide-y divide-gray-100">
                    {Object.entries(advancedMetrics.focus_zone).map(([subject, zones]: [string, any]) => {
                      if (zones && zones.length > 0) {
                        const firstLine = String(zones[0]).split('\n')[0];
                        return (
                          <div key={subject} className="flex items-center gap-3 px-4 py-3 hover:bg-blue-50 transition-colors">
                            <div className="p-1.5 bg-indigo-50 rounded-md">
                              <BookOpen className="h-3.5 w-3.5 text-indigo-600" />
                            </div>
                            <div className="text-sm font-medium text-gray-800 flex-1">{firstLine}</div>
                          </div>
                        );
                      }
                      return null;
                    })}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Repeated Mistakes Section */}
            {advancedMetrics.repeated_mistakes && Object.keys(advancedMetrics.repeated_mistakes).length > 0 && (
              <Card className="bg-white rounded-xl border border-[#E2E8F0] shadow-lg mt-4">
                <CardContent className="p-0">
                      <div className="px-4 py-3 flex items-center justify-between border-b border-gray-100 bg-gradient-to-r from-blue-50 to-blue-100">
                        <div className="flex items-center space-x-2">
                          <div className="p-1.5 bg-blue-100 rounded-lg">
                            <AlertCircle className="h-4 w-4 text-blue-700" />
                          </div>
                          <div className="text-sm font-bold text-blue-900">Repeated Mistakes</div>
                        </div>
                        <div className="text-xs text-blue-700 font-medium">
                          {Object.keys(advancedMetrics.repeated_mistakes).length} topic{Object.keys(advancedMetrics.repeated_mistakes).length > 1 ? 's' : ''}
                        </div>
                      </div>
                  <div className="divide-y divide-gray-100">
                    {Object.entries(advancedMetrics.repeated_mistakes).map(([subject, mistakes]: [string, any]) => {
                      const topic = mistakes && mistakes.length > 0 ? (mistakes[0].topic || subject) : subject;
                      return (
                        <div
                          key={subject}
                          className="flex items-center justify-between px-4 py-3 hover:bg-blue-50 cursor-pointer transition-colors group"
                          onClick={() => {
                            if (mistakes && mistakes.length > 0) {
                              setSelectedMistake({ subject, ...mistakes[0] });
                              setShowMistakeDialog(true);
                            }
                          }}
                        >
                          <div className="flex items-center gap-3">
                            <div className="p-1.5 bg-red-50 rounded-md group-hover:bg-red-100 transition-colors">
                              <AlertTriangle className="h-3.5 w-3.5 text-red-600" />
                            </div>
                            <div className="text-sm font-medium text-gray-800">{topic}</div>
                          </div>
                          <div className="text-amber-600 group-hover:text-amber-700 font-bold">›</div>
                        </div>
                      );
                    })}
                  </div>
                </CardContent>
              </Card>
            )}
          </>
        ) : null}

        {/* Review Answers Button */}
        <Button
          variant="outline"
          onClick={onReviewClick}
          className="w-full bg-white border border-[#E2E8F0] hover:bg-blue-50 text-blue-700 font-semibold shadow-lg"
          size="lg"
        >
          <Eye className="h-5 w-5 mr-2" />
          Review Answers
        </Button>
          </>
        )}
      </div>

      {/* Repeated Mistakes Dialog */}
      <Dialog open={showMistakeDialog} onOpenChange={setShowMistakeDialog}>
        <DialogContent className="max-w-2xl bg-gradient-to-br from-blue-50 to-blue-100 border-2 border-blue-200">
          <DialogHeader className="border-b border-blue-200 pb-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-100 rounded-lg">
                <AlertCircle className="h-6 w-6 text-blue-700" />
              </div>
              <div>
                <DialogTitle className="text-xl font-bold text-blue-900">
                  {selectedMistake?.topic}
                </DialogTitle>
                <p className="text-sm text-blue-700 font-medium mt-1">{selectedMistake?.subject}</p>
              </div>
            </div>
          </DialogHeader>
          {selectedMistake && (
            <div className="space-y-4 pt-4">
              {/* Problem Pattern Card */}
              <div className="bg-white rounded-xl border border-red-200 shadow-sm p-4">
                <div className="flex items-start gap-3 mb-3">
                  <div className="p-2 bg-red-50 rounded-lg shrink-0">
                    <AlertTriangle className="h-5 w-5 text-red-600" />
                  </div>
                  <div className="flex-1">
                    <h3 className="text-base font-bold text-red-900 mb-1">Problem Pattern</h3>
                    <p className="text-xs text-red-700">What's causing the mistakes</p>
                  </div>
                </div>
                <p className="text-sm text-gray-700 leading-relaxed pl-12 pr-2">{selectedMistake.line1}</p>
              </div>

              {/* Action Plan Card */}
              <div className="bg-white rounded-xl border border-green-200 shadow-sm p-4">
                <div className="flex items-start gap-3 mb-3">
                  <div className="p-2 bg-green-50 rounded-lg shrink-0">
                    <Lightbulb className="h-5 w-5 text-green-600" />
                  </div>
                  <div className="flex-1">
                    <h3 className="text-base font-bold text-green-900 mb-1">Action Plan</h3>
                    <p className="text-xs text-green-700">How to improve</p>
                  </div>
                </div>
                <p className="text-sm text-gray-700 leading-relaxed pl-12 pr-2">{selectedMistake.line2}</p>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

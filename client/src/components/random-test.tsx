import { useState, useMemo, useEffect } from "react";
import { useMutation } from "@tanstack/react-query";
import { useLocation } from "wouter";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Slider } from "@/components/ui/slider";
// replaced Dialog usage below with a full-screen overlay to render like a page
import { useToast } from "@/hooks/use-toast";
import { apiRequest } from "@/lib/queryClient";
import { API_CONFIG } from "@/config/api";
import { Shuffle, Target, BookOpen, ChevronLeft } from "lucide-react";
import { Topic, CreateTestSessionResponse } from '../types/api';
import { useAuth } from "@/hooks/use-auth";

interface RandomTestProps {
  testType: "random" | "custom";
  topics: Topic[];
  onCancel?: () => void;
}

export function RandomTest({ testType, topics, onCancel }: RandomTestProps) {
  // Slider bounds
  const SLIDER_MIN = 1;
  const SLIDER_MAX = 50;
  const SLIDER_STEP = 1;
  const MAX_TIME_MULTIPLIER = 1.5; // 1 minute actual + 0.5 minute buffer per question

  const [questionCount, setQuestionCount] = useState<number>(20);
  const [timeLimit, setTimeLimit] = useState<number>(10);
  const [lastChanged, setLastChanged] = useState<'time' | 'questions'>('questions');

  const timeMin = SLIDER_MIN;
  const timeMax = useMemo(() => Math.max(SLIDER_MIN, Math.ceil(questionCount * MAX_TIME_MULTIPLIER)), [questionCount]);

  const { toast } = useToast();
  const { student } = useAuth();
  const [, navigate] = useLocation();

  const [showInsufficientDialog, setShowInsufficientDialog] = useState<boolean>(false);
  const [insufficientQuestionsData, setInsufficientQuestionsData] = useState<{ available: number; requested: number; message: string } | null>(null);

  useEffect(() => {
    if (timeLimit > timeMax) {
      setTimeLimit(timeMax);
    }
  }, [timeMax, timeLimit]);

  const createTestMutation = useMutation({
    mutationFn: async (data: any) => {
      const payload = { ...data, studentId: student?.studentId };
      const response = await apiRequest(API_CONFIG.ENDPOINTS.TEST_SESSIONS, "POST", payload);
      return response as CreateTestSessionResponse;
    },
    onSuccess: (data) => navigate(`/test/${data.session.id}`),
    onError: (error: any) => {
      let errorData = null;
      try {
        if (error.message) {
          const match = error.message.match(/^\d+:\s*(.+)$/);
          if (match) errorData = JSON.parse(match[1]);
        }
      } catch (e) {
        // ignore
      }

      if (errorData?.error === "Insufficient questions available") {
        setInsufficientQuestionsData({
          available: errorData.available_questions,
          requested: errorData.requested_questions,
          message: errorData.message || "Not enough questions available for this test configuration."
        });
        setShowInsufficientDialog(true);
      } else {
        toast({ title: "Error", description: "Failed to create test session. Please try again.", variant: "destructive" });
      }
    }
  });

  const generateRandomTopics = (totalQuestions: number) => {
    const subjects = ["Physics", "Chemistry", "Botany", "Zoology"];
    const questionsPerSubject = Math.floor(totalQuestions / 4);
    const randomTopics: string[] = [];

    subjects.forEach(subject => {
      const subjectTopics = topics.filter(topic => topic.subject.toLowerCase() === subject.toLowerCase());
      const shuffled = [...subjectTopics].sort(() => 0.5 - Math.random());
      const selected = shuffled.slice(0, Math.min(questionsPerSubject, subjectTopics.length));
      randomTopics.push(...selected.map(t => t.id.toString()));
    });

    return randomTopics;
  };

  const handleCreateRandom = () => {
    if (!questionCount || questionCount <= 0) {
      toast({ title: "Invalid question count", description: "Please set a valid number of questions for random tests.", variant: "destructive" });
      return;
    }
    if (!timeLimit || timeLimit <= 0) {
      toast({ title: "Invalid time limit", description: "Please set a valid time limit for random tests.", variant: "destructive" });
      return;
    }

    const payloadRandom: any = {
      selected_topics: [], // empty signals random selection on backend
      selection_mode: lastChanged === 'questions' ? 'question_count' : 'time_limit',
      question_count: questionCount,
      time_limit: timeLimit,
      test_type: 'random'
    };

    createTestMutation.mutate(payloadRandom);
  };

  return (
    <div className="pb-60">

      {testType === 'random' && (
        <Card className="mt-4">
          <CardContent>
            {/* Card is now empty - sliders moved to fixed positions */}
          </CardContent>
        </Card>
      )}

      {/* Questions Selection - Positioned above time slider */}
      {testType === 'random' && (
        <div className="fixed bottom-40 left-0 right-0 z-30 p-4 bg-white border-t">
          <div className="text-sm font-medium text-gray-700 mb-3">Number of Questions</div>
          <div className="grid grid-cols-3 gap-2">
            {[5, 10, 15, 20, 25, 30, 60, 90, 180].map((count) => (
              <Button
                key={count}
                variant={questionCount === count ? "default" : "outline"}
                size="sm"
                onClick={() => {
                  setQuestionCount(count);
                  setTimeLimit(count);
                  setLastChanged('questions');
                }}
                className="text-sm"
              >
                {count} Qs
              </Button>
            ))}
          </div>
        </div>
      )}

      {/* Time Limit Slider - Positioned above footer */}
      {testType === 'random' && (
        <div className="fixed bottom-20 left-0 right-0 z-40 p-4 bg-white border-t">
          <div className="text-sm font-medium text-gray-700 mb-2">Time Limit: {timeLimit} minutes</div>
          <Slider value={[timeLimit]} onValueChange={(v) => { let val = v[0]; if (val < timeMin) val = timeMin; if (val > timeMax) val = timeMax; setTimeLimit(val); setLastChanged('time'); }} min={timeMin} max={timeMax} step={SLIDER_STEP} />
        </div>
      )}

      {/* Footer with Create Button - Fixed to bottom of screen */}
      {testType === 'random' && (
        <footer className="fixed bottom-0 left-0 right-0 z-50 p-4 border-t bg-white" style={{ paddingBottom: 'env(safe-area-inset-bottom, 16px)' }}>
          <div className="flex flex-row space-x-2 items-center mb-3">
            <Button
              variant="outline"
              size="lg"
              onClick={onCancel}
            >
              Cancel
            </Button>
            <Button
              variant="default"
              size="lg"
              onClick={handleCreateRandom}
              disabled={createTestMutation.isPending}
              className="w-full"
            >
              {createTestMutation.isPending ? 'Creating...' : 'Create Random Test'}
            </Button>
          </div>
        </footer>
      )}

      {/* Insufficient questions — full screen page-style overlay (replaces Dialog) */}
      {showInsufficientDialog && (
        <div role="dialog" aria-modal="true" className="fixed inset-0 z-[99999] bg-white min-h-screen overflow-hidden">
          <div className="max-w-3xl mx-auto h-full flex flex-col">
            {/* Header - mobile first */}
            <header className="w-full mx-auto py-3 px-4 border-b border-gray-200 inline-flex items-center gap-3">
              <Button variant="secondary" size="icon" className="size-8" onClick={() => setShowInsufficientDialog(false)}>
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <h1 className="text-lg font-bold text-gray-900">Insufficient Questions</h1>
            </header>            {/* Main scrollable content */}
            <main className="flex-1 overflow-auto p-4 sm:p-6">
              <div className="space-y-4">
                <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium text-orange-800">Available Questions:</span>
                    <span className="text-lg font-bold text-orange-600">{insufficientQuestionsData?.available}</span>
                  </div>
                  <div className="flex justify-between items-center mt-2">
                    <span className="text-sm font-medium text-orange-800">Requested Questions:</span>
                    <span className="text-lg font-bold text-red-600">{insufficientQuestionsData?.requested}</span>
                  </div>
                </div>

                {/* Additional explanatory text can go here for mobile users */}
                <p className="text-sm text-gray-700">You can reduce the number of questions, or use the available questions to continue the test.</p>
              </div>
            </main>

            {/* Footer - safe-area aware, buttons stack on mobile */}
            <footer className="p-3 sm:p-6 border-t bg-white" style={{ paddingBottom: 'env(safe-area-inset-bottom, 16px)' }}>
              <div className="flex flex-col sm:flex-row gap-3">
                <Button variant="outline" onClick={() => setShowInsufficientDialog(false)} className="w-full">
                  <BookOpen className="h-4 w-4 mr-2" />
                  Back to Selection
                </Button>
                <Button
                  onClick={() => {
                    if (insufficientQuestionsData?.available) setQuestionCount(insufficientQuestionsData.available);
                    setShowInsufficientDialog(false);
                  }}
                  className="w-full bg-blue-600 hover:bg-blue-700"
                >
                  <Target className="h-4 w-4 mr-2" />
                  Use {insufficientQuestionsData?.available} Questions
                </Button>
              </div>
            </footer>
          </div>
        </div>
      )}
    </div>
  );
}

export default RandomTest;

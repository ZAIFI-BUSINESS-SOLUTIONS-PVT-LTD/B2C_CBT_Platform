import { useState, useMemo, useEffect } from "react";
import { useMutation } from "@tanstack/react-query";
import { useLocation } from "wouter";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Slider } from "@/components/ui/slider";
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
  onInsufficientQuestions?: (data: { available: number; requested: number; message: string }) => void;
}

export function RandomTest({ testType, topics, onCancel, onInsufficientQuestions }: RandomTestProps) {
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
        if (onInsufficientQuestions) {
          onInsufficientQuestions({
            available: errorData.available_questions,
            requested: errorData.requested_questions,
            message: errorData.message || "Not enough questions available for this test configuration."
          });
        }
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
    <div className="hidden md:block">
      <div className="space-y-6">
      {testType === 'random' && (
        <>
          {/* Questions Selection */}
          <div>
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

          {/* Time Limit Slider */}
          <div>
            <div className="text-sm font-medium text-gray-700 mb-2">Time Limit: {timeLimit} minutes</div>
            <Slider value={[timeLimit]} onValueChange={(v) => { let val = v[0]; if (val < timeMin) val = timeMin; if (val > timeMax) val = timeMax; setTimeLimit(val); setLastChanged('time'); }} min={timeMin} max={timeMax} step={SLIDER_STEP} />
          </div>

          {/* Footer with Create Button */}
          <div className="flex flex-row space-x-2 items-center pt-4">
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
              className="flex-1"
            >
              {createTestMutation.isPending ? 'Creating...' : 'Create Random Test'}
            </Button>
          </div>
        </>
      )}
    </div>
    </div>
  );
}

export default RandomTest;

/**
 * Question of the Day Modal Component
 * 
 * Displays a daily question challenge with immediate feedback.
 * Features:
 * - Shows one question per day
 * - Allows user to select an answer
 * - Shows immediate feedback (correct/incorrect)
 * - Displays penguin mascot based on result
 * - Shows correct answer if wrong
 */

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { X } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import { API_CONFIG } from "@/config/api";
import { authenticatedFetch } from "@/lib/auth";
import normalizeImageSrc from "@/lib/media";

interface QuestionOfTheDayModalProps {
  isOpen: boolean;
  onClose: () => void;
}

interface Question {
  id: number;
  topicId: number;
  question: string;
  optionA: string;
  optionB: string;
  optionC: string;
  optionD: string;
  correctAnswer: string;
  explanation: string;
  questionImage?: string | null;
  optionAImage?: string | null;
  optionBImage?: string | null;
  optionCImage?: string | null;
  optionDImage?: string | null;
  explanationImage?: string | null;
}

interface QODResponse {
  alreadyAttempted: boolean;
  qod: {
    id: number;
    student: string;
    question: number;
    questionData: Question;
    date: string;
    selectedOption: string | null;
    isCorrect: boolean | null;
    createdAt: string;
  };
}

interface SubmitResponse {
  isCorrect: boolean;
  correctAnswer: string;
  explanation: string;
  explanationImage?: string | null;
  qod: QODResponse['qod'];
}

export default function QuestionOfTheDayModal({ isOpen, onClose }: QuestionOfTheDayModalProps) {
  const [selectedAnswer, setSelectedAnswer] = useState<string | null>(null);
  const [showResult, setShowResult] = useState(false);
  const [resultData, setResultData] = useState<SubmitResponse | null>(null);
  const { toast } = useToast();
  const queryClient = useQueryClient();

  // Fetch today's question
  const { data: qodData, isLoading, error } = useQuery<QODResponse>({
    queryKey: ['question-of-the-day'],
    queryFn: async () => {
      const response = await authenticatedFetch(`${API_CONFIG.BASE_URL}/api/qod/`);
      if (!response.ok) {
        throw new Error(`Failed to fetch question: ${response.status}`);
      }
      return response.json();
    },
    enabled: isOpen,
    staleTime: 5 * 60 * 1000, // Consider data fresh for 5 minutes
  });

  // Reset state when modal closes; when opening, allow QOD API to control showing results
  useEffect(() => {
    if (!isOpen) {
      setSelectedAnswer(null);
      setShowResult(false);
      setResultData(null);
    }
  }, [isOpen]);

  // If already attempted, show result immediately (even if selectedOption wasn't returned)
  // Watch both qodData AND isOpen so this runs when modal reopens with cached data
  useEffect(() => {
    if (isOpen && qodData?.alreadyAttempted && qodData.qod) {
      // Use selectedOption if provided, otherwise keep null
      const sel = qodData.qod.selectedOption ?? null;
      setSelectedAnswer(sel);
      setShowResult(true);
      setResultData({
        isCorrect: qodData.qod.isCorrect ?? false,
        correctAnswer: qodData.qod.questionData.correctAnswer,
        explanation: qodData.qod.questionData.explanation,
        explanationImage: qodData.qod.questionData.explanationImage,
        qod: qodData.qod,
      });
    }
  }, [qodData, isOpen]);

  // Submit answer mutation
  const submitMutation = useMutation({
    mutationFn: async (answer: string) => {
      const payload: any = { selected_option: answer };
      if (question && (question as any).id) payload.question_id = (question as any).id;
      const response = await authenticatedFetch(`${API_CONFIG.BASE_URL}/api/qod/submit/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to submit answer');
      }
      return response.json();
    },
    onSuccess: (data: SubmitResponse) => {
      setResultData(data);
      setShowResult(true);
      // Invalidate query to refresh data
      queryClient.invalidateQueries({ queryKey: ['question-of-the-day'] });
    },
    onError: (error: Error) => {
      toast({
        title: "Error",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  const handleSubmit = () => {
    if (!selectedAnswer) {
      toast({
        title: "Select an answer",
        description: "Please select an option before submitting",
        variant: "destructive",
      });
      return;
    }
    submitMutation.mutate(selectedAnswer);
  };

  if (!isOpen) return null;

  const question = qodData?.qod.questionData;
  const isCorrect = resultData?.isCorrect ?? false;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4 animate-in fade-in duration-200">
      <Card 
        className="relative w-full max-w-2xl rounded-2xl shadow-2xl border-0 overflow-hidden"
      >
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 z-10 p-2 rounded-full bg-white/90 hover:bg-white shadow-md transition-colors"
          aria-label="Close"
        >
          <X className="w-5 h-5 text-gray-600" />
        </button>

        <CardContent
          className="p-6 sm:p-8 bg-gradient-to-b from-blue-50 to-blue-100 rounded-2xl max-h-[90vh] overflow-y-auto"
          style={{
            overscrollBehavior: 'auto',
            WebkitOverflowScrolling: 'touch'
          }}
        >{/* Header */}
          <div className="mb-6">
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Question of the Day</h2>
          </div>

          {/* Loading state */}
          {isLoading && (
            <div className="flex flex-col items-center justify-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mb-4"></div>
              <p className="text-gray-500">Loading today's question...</p>
            </div>
          )}

          {/* Error state */}
          {error && (
            <div className="flex flex-col items-center justify-center py-12">
              <p className="text-gray-700 font-medium text-lg">Failed to load question</p>
              <p className="text-sm text-gray-500 mt-2">Please try again later</p>
            </div>
          )}

          {/* Question content */}
          {question && !showResult && (
            <div className={submitMutation.isPending ? 'opacity-50 pointer-events-none' : ''}>
              {/* Question text */}
              <div className="mb-6 p-4 bg-blue-50 rounded-xl">
                <h3 className="text-lg font-semibold text-gray-800 leading-relaxed">
                  Q. {question.question}
                </h3>
                {question.questionImage && (
                  <div className="mt-4">
                    <img
                      src={normalizeImageSrc(question.questionImage)}
                      alt="question"
                      className="block max-w-full h-auto rounded-lg border border-gray-200"
                      style={{ maxHeight: '300px', objectFit: 'contain' }}
                      onError={(e) => { e.currentTarget.style.display = 'none'; }}
                    />
                  </div>
                )}
              </div>

              {/* Options */}
              <RadioGroup
                value={selectedAnswer || ""}
                onValueChange={setSelectedAnswer}
                disabled={qodData?.alreadyAttempted}
              >
                <div className="space-y-3">
                  {["A", "B", "C", "D"].map((option) => {
                    const isSelected = selectedAnswer === option;
                    const optionId = `qod-option-${option}`;
                    return (
                      <Label
                        key={option}
                        htmlFor={optionId}
                        className={`flex items-center p-4 rounded-xl cursor-pointer transition-all border-2 ${
                          isSelected
                            ? 'bg-blue-50 border-blue-400 shadow-sm'
                            : 'bg-white border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                        }`}
                      >
                        <RadioGroupItem value={option} id={optionId} className="sr-only" />
                        <span className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold mr-3 flex-shrink-0 ${
                          isSelected ? 'bg-blue-500 text-white' : 'bg-gray-200 text-gray-700'
                        }`}>
                          {option}
                        </span>
                        <span className="text-base text-gray-800 font-medium leading-relaxed flex-1">
                          {question[`option${option}` as keyof typeof question] as string}
                        </span>
                        {(question as any)[`option${option}Image`] && (
                          <div className="ml-2">
                            <img
                              src={normalizeImageSrc((question as any)[`option${option}Image`])}
                              alt={`option ${option}`}
                              className="block max-w-[120px] h-auto rounded-md border border-gray-200"
                              style={{ maxHeight: '100px', objectFit: 'contain' }}
                              onError={(e) => { e.currentTarget.style.display = 'none'; }}
                            />
                          </div>
                        )}
                      </Label>
                    );
                  })}
                </div>
              </RadioGroup>

              {/* Submit button */}
              {!qodData?.alreadyAttempted && (
                <div className="mt-6 flex justify-end">
                  <Button
                    onClick={handleSubmit}
                    disabled={!selectedAnswer || submitMutation.isPending}
                    className="px-8 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 font-semibold shadow-md disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {submitMutation.isPending ? 'Submitting...' : 'Submit Answer'}
                  </Button>
                </div>
              )}
            </div>
          )}

          {/* Result overlay */}
          {showResult && resultData && question && (
            <div className="relative min-h-[400px]">
              {/* Blurred question background */}
              <div className="filter blur-md opacity-30 pointer-events-none">
                <div className="p-4 bg-blue-50 rounded-xl mb-4">
                  <h3 className="text-lg font-semibold text-gray-800">
                    Q. {question.question}
                  </h3>
                </div>
                <div className="space-y-3">
                  {["A", "B", "C", "D"].map((option) => (
                    <div key={option} className="p-4 rounded-xl border-2 border-gray-200 bg-white">
                      <span className="font-medium">{option}. {question[`option${option}` as keyof typeof question] as string}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Result overlay - centered */}
              <div className="absolute top-24 inset-x-0 bottom-0 flex flex-col items-center justify-start pt-4 px-2 gap-2 -mt-7">
                  {/* Question attempted - placed on top of penguin */}
                  <div className="mb-2 text-center px-2 -mt-20 -mb-9">
                    <p className="text-sm text-gray-700 font-medium leading-relaxed">Q. {question.question}</p>
                  </div>

                  {/* Penguin image (increased by additional 20%) */}
                  <img
                    src={isCorrect ? '/happy-penguin.webp' : '/sad-penguin.webp'}
                    alt={isCorrect ? 'Success' : 'Try again'}
                    className="object-contain -mb-11"
                    style={{ width: '12.5rem', height: '14.5rem' }}
                  />

                  {/* Result message (reduced sizes by ~20%) */}
                  {isCorrect ? (
                    <h3 className="text-3xl font-bold text-green-600 mb-1">Correct!</h3>
                  ) : (
                    <>
                      <h3 className="text-3xl font-bold text-red-600 mb-1">Sorry!</h3>
                      <p className="text-sm text-gray-700 font-medium mb-2">Not quite right. Keep learning! 💪</p>
                      <div className="bg-white/90 backdrop-blur-sm px-4 py-2 rounded-xl">
                        <p className="text-sm text-gray-700 font-medium mb-1">Correct Answer:</p>
                        <p className="text-sm font-bold text-green-700 font-medium
                        ">
                          {resultData.correctAnswer}. {question[`option${resultData.correctAnswer}` as keyof typeof question] as string}
                        </p>
                      </div>
                    </>
                  )}

                  {/* Close button */}
                  <Button
                    onClick={onClose}
                    className="mt-2 px-6 py-2 bg-blue-600 text-white rounded-xl hover:bg-blue-700 font-semibold shadow-lg"
                  >
                    Done
                  </Button>
                </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

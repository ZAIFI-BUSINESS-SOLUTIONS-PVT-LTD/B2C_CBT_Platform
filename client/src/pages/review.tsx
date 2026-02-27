import { useParams, useLocation } from "wouter";
import { useQuery } from "@tanstack/react-query";
import { QuestionReview } from "@/components/question-review";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { ChevronLeft } from "lucide-react";

interface ReviewResults {
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
    questionImage?: string | null;
    optionAImage?: string | null;
    optionBImage?: string | null;
    optionCImage?: string | null;
    optionDImage?: string | null;
    explanationImage?: string | null;
    markedForReview: boolean;
  }>;
  correctAnswers: number;
  incorrectAnswers: number;
  unansweredQuestions: number;
}

export default function Review() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const [, navigate] = useLocation();

  const { data: results, isLoading } = useQuery<ReviewResults, Error>({
    queryKey: [`/api/test-sessions/${sessionId}/results/`],
    enabled: !!sessionId,
  });

  if (isLoading) {
    return (
      <div 
        className="min-h-screen bg-cover bg-center bg-no-repeat bg-fixed relative pb-20"
        style={{ backgroundImage: "url('/testpage-bg.webp')", backgroundAttachment: 'fixed' }}
      >
        <div className="absolute inset-0 bg-transparent"></div>
        <div className="relative z-10 flex items-center justify-center min-h-screen px-4">
          <div className="space-y-3 w-full max-w-sm">
            <Skeleton className="h-6 w-48 bg-transparent mx-auto" />
            <Skeleton className="h-24 w-full bg-transparent" />
            <Skeleton className="h-4 w-32 bg-transparent mx-auto" />
          </div>
        </div>
      </div>
    );
  }

  if (!results) {
    return (
      <div 
        className="min-h-screen bg-cover bg-center bg-no-repeat bg-fixed relative pb-20"
        style={{ backgroundImage: "url('/testpage-bg.webp')", backgroundAttachment: 'fixed' }}
      >
        <div className="absolute inset-0 bg-transparent"></div>
        <div className="relative z-10 flex items-center justify-center min-h-screen px-4">
          <div className="text-center bg-white/80 backdrop-blur-md rounded-2xl shadow-lg border border-transparent p-6 max-w-sm mx-4 w-full">
            <h2 className="text-lg font-bold text-gray-900 mb-3">
              Results Not Found
            </h2>
            <p className="text-gray-700 text-sm">
              The test results you're looking for don't exist.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div 
      className="min-h-screen bg-cover bg-center bg-no-repeat bg-fixed relative pb-20"
      style={{ backgroundImage: "url('/testpage-bg.webp')", backgroundAttachment: 'fixed' }}
    >
      {/* Removed overlay so background image shows through */}
      <div className="absolute inset-0 bg-transparent"></div>

      {/* Content */}
      <div className="relative z-10">
        {/* Header */}
        <div className="sticky top-0 bg-white/90 backdrop-blur-md z-30 border-b border-white/90">
          <div className="w-full mx-auto py-3 px-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Button
                variant="ghost"
                size="icon"
                className="bg-transparent border border-transparent text-gray-900 hover:bg-white/5 h-10 w-10"
                onClick={() => navigate(`/results/${sessionId}`)}
              >
                <ChevronLeft className="h-5 w-5" />
              </Button>
              <h1 className="text-lg font-bold text-gray-900">Review Answers</h1>
            </div>
          </div>
        </div>
        
        <QuestionReview
          detailedAnswers={results.detailedAnswers}
          correctAnswers={results.correctAnswers}
          incorrectAnswers={results.incorrectAnswers}
          unansweredQuestions={results.unansweredQuestions}
        />
      </div>
    </div>
  );
}

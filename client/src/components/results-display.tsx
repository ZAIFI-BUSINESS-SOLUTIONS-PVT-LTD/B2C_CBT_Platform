import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { useLocation } from "wouter";
import {
  RotateCcw,
  Atom,
  FlaskConical,
  Dna,
  BookOpen,
  BarChart3,
  Eye
} from "lucide-react";
import MiniChatbot from "./mini-chatbot";

export interface ResultsDisplayProps {
  results: {
    sessionId?: number;
    totalQuestions: number;
    correctAnswers: number;
    incorrectAnswers: number;
    unansweredQuestions: number;
    scorePercentage: number;
    timeTaken: number;
    // changed to an array so each entry carries the subject name explicitly
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

export function ResultsDisplay({ results, onReviewClick }: ResultsDisplayProps) {
  const [, navigate] = useLocation();

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const getSubjectIcon = (subject: string) => {
    switch (subject) {
      case "Physics":
        return <Atom className="h-5 w-5 text-blue-600" />;
      case "Chemistry":
        return <FlaskConical className="h-5 w-5 text-green-600" />;
      case "Biology":
        return <Dna className="h-5 w-5 text-emerald-600" />;
      default:
        return null;
    }
  };

  const getSubjectColor = (subject: string) => {
    switch (subject) {
      case "Physics":
        return "bg-gradient-to-r from-blue-400 to-blue-500";
      case "Chemistry":
        return "bg-gradient-to-r from-blue-400 to-blue-500";
      case "Biology":
        return "bg-gradient-to-r from-blue-400 to-blue-500";
      default:
        return "bg-gradient-to-r from-blue-400 to-blue-500";
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-sky-50 via-blue-50 to-indigo-50 pb-3">
      {/* Overall Score Card */}
      <Card className="dashboard-card shadow-xl my-2 mx-2">
        <CardContent className="p-3">
          <div className="text-center mb-3">
            <div className="relative inline-flex items-center justify-center w-20 h-20 mb-3">
              <svg className="w-20 h-20 transform -rotate-90" viewBox="0 0 36 36">
                <path
                  d="m18,2.0845 a 15.9155,15.9155 0 0,1 0,31.831 a 15.9155,15.9155 0 0,1 0,-31.831"
                  fill="none"
                  stroke="#e2e8f0"
                  strokeWidth="2"
                />
                <path
                  d="m18,2.0845 a 15.9155,15.9155 0 0,1 0,31.831 a 15.9155,15.9155 0 0,1 0,-31.831"
                  fill="none"
                  stroke="#3b82f6"
                  strokeWidth="2"
                  strokeDasharray={`${results.scorePercentage}, 100`}
                  strokeLinecap="round"
                />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="text-slate-700 text-center">
                  <div className="text-lg font-bold">{results.scorePercentage}%</div>
                  <div className="text-xs opacity-90 font-medium text-slate-700">Score</div>
                </div>
              </div>
            </div>
            <h3 className="text-lg font-bold text-neet-gray-900 mb-1 tracking-tight">
              {results.scorePercentage >= 80 ? "Excellent Work!" :
                results.scorePercentage >= 60 ? "Good Job!" :
                  "Keep Practicing!"}
            </h3>
            <p className="text-sm text-neet-gray-600">
              You scored <span className="font-bold text-neet-gray-900">{results.correctAnswers}</span> out of{" "}
              <span className="font-bold text-neet-gray-900">{results.totalQuestions}</span> questions correctly.
            </p>
          </div>

          {/* Score Breakdown */}
          <div className="grid grid-cols-2 gap-2 mb-3">
            <div className="text-center p-2 bg-gradient-to-br from-green-50 to-emerald-50 rounded-lg border border-green-200">
              <div className="text-xl font-bold text-green-700 mb-0.5">
                {results.correctAnswers}
              </div>
              <div className="text-green-700 text-xs font-medium">Correct</div>
            </div>
            <div className="text-center p-2 bg-gradient-to-br from-red-50 to-rose-50 rounded-lg border border-red-200">
              <div className="text-xl font-bold text-red-700 mb-0.5">
                {results.incorrectAnswers}
              </div>
              <div className="text-red-700 text-xs font-medium">Incorrect</div>
            </div>
            <div className="text-center p-2 bg-gradient-to-br from-amber-50 to-yellow-50 rounded-lg border border-amber-200">
              <div className="text-xl font-bold text-amber-700 mb-0.5">
                {results.unansweredQuestions}
              </div>
              <div className="text-amber-700 text-xs font-medium">Unanswered</div>
            </div>
            <div className="text-center p-2 bg-gradient-to-br from-blue-50 to-indigo-50 rounded-lg border border-blue-200">
              <div className="text-xl font-bold text-blue-700 mb-0.5">
                {formatTime(results.timeTaken)}
              </div>
              <div className="text-blue-700 text-xs font-medium">Time Taken</div>
            </div>
          </div>

          {/* Subject-wise Performance */}
          <div className="mb-4">
            <h4 className="text-base font-semibold text-slate-900 mb-3">
              Subject-wise Performance
            </h4>
            <div className="space-y-3">
              {results.subjectPerformance.map(({ subject, correct, total }) => {
                const percentage = total > 0 ? Math.round((correct / total) * 100) : 0;
                return (
                  <div
                    key={subject}
                    className="flex items-center justify-between p-2 bg-slate-50 rounded-lg"
                  >
                    <div className="flex items-center">
                      {getSubjectIcon(subject)}
                      <div className="ml-2">
                        <div className="font-medium text-slate-900 text-sm">{subject}</div>
                        <div className="text-xs text-slate-600">
                          {correct}/{total} questions
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center">
                      <div className="w-20 mr-2">
                        <Progress value={percentage} className="h-1.5" indicatorClassName={getSubjectColor(subject)} />
                      </div>
                      <span className="text-xs font-medium text-slate-900">
                        {percentage}%
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </CardContent>
      </Card>
      {/* Action Buttons */}
      <div className="flex flex-col space-y-2 px-2 mt-4">

        <Button
          variant="outline"
          onClick={onReviewClick}
          className="w-full"
        >
          <Eye className="h-4 w-4 mr-2" />
          Review Answers
        </Button>
        <Button
          variant="default"
          onClick={() => navigate('/topics')}
          className="w-full"
        >
          <RotateCcw className="h-4 w-4 mr-2" />
          Take Another Test
        </Button>
      </div>

      <div className="px-2 pt-4">
        <h1 className="text-lg font-semibold text-slate-900 mb-2 ml-2">Ask the Chatbot</h1>
        <MiniChatbot className="max-w-full" />
      </div>

    </div>
  );
}

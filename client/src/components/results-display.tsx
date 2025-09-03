import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useLocation } from "wouter";
import { 
  Eye, 
  EyeOff,
  RotateCcw, 
  CheckCircle, 
  XCircle, 
  Clock,
  Atom,
  FlaskConical,
  Dna,
  Filter,
  BookOpen,
  BarChart3,
  Home
} from "lucide-react";

export interface ResultsDisplayProps {
  results: {
    sessionId: number;
    totalQuestions: number;
    correctAnswers: number;
    incorrectAnswers: number;
    unansweredQuestions: number;
    scorePercentage: number;
    timeTaken: number;
    subjectPerformance: Record<string, { correct: number; total: number }>;
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
}

export function ResultsDisplay({ results }: ResultsDisplayProps) {
  const [, navigate] = useLocation();
  const [showReview, setShowReview] = useState(false);
  const [reviewFilter, setReviewFilter] = useState<"all" | "correct" | "incorrect" | "unanswered">("all");

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
        return "bg-blue-600";
      case "Chemistry":
        return "bg-green-600";
      case "Biology":
        return "bg-emerald-600";
      default:
        return "bg-slate-600";
    }
  };

  const getFilteredAnswers = () => {
    switch (reviewFilter) {
      case "correct":
        return results.detailedAnswers.filter(answer => answer.isCorrect);
      case "incorrect":
        return results.detailedAnswers.filter(answer => !answer.isCorrect && answer.selectedAnswer);
      case "unanswered":
        return results.detailedAnswers.filter(answer => answer.selectedAnswer === null || answer.selectedAnswer === undefined || answer.selectedAnswer === "");
      default:
        return results.detailedAnswers;
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50 py-4">
      <div className="container mx-auto px-3 max-w-4xl">
        <Card className="shadow-2xl border-0 bg-white/80 backdrop-blur-sm">
          <CardContent className="p-4">
            <div className="text-center mb-3">
              <h1 className="text-xl font-bold text-slate-800 mb-2">Test Results</h1>
              <p className="text-slate-600 text-sm">Here's how you performed on your NEET practice test</p>
            </div>

        {/* Overall Score Card */}
        <Card className="dashboard-card shadow-xl mb-3">
          <CardContent className="p-3">
            <div className="text-center mb-3">
              <div className="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-neet-blue to-blue-600 rounded-full mb-3 shadow-lg">
                  <div className="text-slate-700 text-center">
                  <div className="text-lg font-bold">{results.scorePercentage}%</div>
                    <div className="text-xs opacity-90 font-medium text-slate-700">Score</div>
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
            <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mb-4">
              <div className="text-center p-3 bg-gradient-to-br from-green-50 to-emerald-50 rounded-xl border border-green-200">
                <div className="text-2xl font-bold text-neet-green mb-0.5">
                  {results.correctAnswers}
                </div>
                <div className="text-green-700 text-xs font-medium">Correct</div>
              </div>
              <div className="text-center p-3 bg-gradient-to-br from-red-50 to-rose-50 rounded-xl border border-red-200">
                <div className="text-2xl font-bold text-neet-red mb-0.5">
                  {results.incorrectAnswers}
                </div>
                <div className="text-red-700 text-xs font-medium">Incorrect</div>
              </div>
              <div className="text-center p-3 bg-gradient-to-br from-amber-50 to-yellow-50 rounded-xl border border-amber-200">
                <div className="text-2xl font-bold text-neet-amber mb-0.5">
                  {results.unansweredQuestions}
                </div>
                <div className="text-amber-700 text-xs font-medium">Unanswered</div>
              </div>
              <div className="text-center p-3 bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl border border-blue-200">
                <div className="text-2xl font-bold text-neet-blue mb-0.5">
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
                {Object.entries(results.subjectPerformance).map(([subject, performance]) => {
                  const percentage = Math.round((performance.correct / performance.total) * 100);
                  return (
                    <div
                      key={subject}
                      className="flex items-center justify-between p-3 bg-slate-50 rounded-lg"
                    >
                      <div className="flex items-center">
                        {getSubjectIcon(subject)}
                        <div className="ml-2">
                          <div className="font-medium text-slate-900 text-sm">{subject}</div>
                          <div className="text-xs text-slate-600">
                            {performance.correct}/{performance.total} questions
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center">
                        <div className="w-28 bg-slate-200 rounded-full h-1.5 mr-2.5">
                          <div
                            className={`h-1.5 rounded-full ${getSubjectColor(subject)}`}
                            style={{ width: `${percentage}%` }}
                          ></div>
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

            {/* Action Buttons */}
            <div className="flex justify-center space-x-2 mb-2">
              <Button
                variant="outline"
                onClick={() => setShowReview(!showReview)}
                className="btn-secondary px-4 py-2 text-xs font-medium"
              >
                {showReview ? <EyeOff className="h-3 w-3 mr-1" /> : <Eye className="h-3 w-3 mr-1" />}
                {showReview ? "Hide Review" : "Review Answers"}
              </Button>
              <Button
                onClick={() => navigate('/dashboard')}
                className="bg-gradient-to-r from-purple-600 to-blue-600 text-white px-4 py-2 text-xs font-medium shadow-lg hover:shadow-xl transform hover:scale-[1.02] transition-all duration-200"
              >
                <BarChart3 className="h-3 w-3 mr-1" />
                Performance Analytics
              </Button>
              <Button
                onClick={() => navigate('/test-history')}
                className="bg-gradient-to-r from-purple-600 to-blue-600 text-white px-4 py-2 text-xs font-medium shadow-lg hover:shadow-xl transform hover:scale-[1.02] transition-all duration-200"
              >
                <BarChart3 className="h-3 w-3 mr-1" />
                Test History
              </Button>
              <Button
                onClick={() => navigate('/')}
                className="bg-gradient-to-r from-purple-600 to-blue-600 text-white px-4 py-2 text-xs font-medium shadow-lg hover:shadow-xl transform hover:scale-[1.02] transition-all duration-200"
              >
                <RotateCcw className="h-3 w-3 mr-1" />
                Take Another Test
              </Button>
            </div>
          </CardContent>
        </Card>
          </CardContent>
        </Card>

        {/* Detailed Question Review */}
        {showReview && (
          <Card className="bg-white rounded-2xl shadow-lg">
            <CardContent className="p-4">
              <div className="flex justify-between items-center mb-3">
                <h4 className="text-lg font-bold text-slate-900 flex items-center">
                  <BookOpen className="h-5 w-5 mr-2 text-neet-blue" />
                  Question Review
                </h4>
                <div className="flex items-center space-x-2">
                  <Filter className="h-4 w-4 text-slate-600" />
                  <span className="text-xs text-slate-600">Filter:</span>
                </div>
              </div>

              {/* Filter Tabs */}
              <Tabs value={reviewFilter} onValueChange={(value: any) => setReviewFilter(value)} className="mb-6">
                <TabsList className="grid w-full grid-cols-4">
                  <TabsTrigger value="all" className="flex items-center">
                    All ({results.detailedAnswers.length})
                  </TabsTrigger>
                  <TabsTrigger value="correct" className="flex items-center text-green-700">
                    <CheckCircle className="h-4 w-4 mr-1" />
                    Correct ({results.correctAnswers})
                  </TabsTrigger>
                  <TabsTrigger value="incorrect" className="flex items-center text-red-700">
                    <XCircle className="h-4 w-4 mr-1" />
                    Incorrect ({results.incorrectAnswers})
                  </TabsTrigger>
                  <TabsTrigger value="unanswered" className="flex items-center text-amber-700">
                    <Clock className="h-4 w-4 mr-1" />
                    Unanswered ({results.unansweredQuestions})
                  </TabsTrigger>
                </TabsList>

                <TabsContent value={reviewFilter} className="mt-6">
                  <div className="space-y-6">
                    {getFilteredAnswers().map((answer, index) => {
                      const originalIndex = results.detailedAnswers.findIndex(a => a.questionId === answer.questionId);
                      return (
                        <div
                          key={answer.questionId}
                          className="border border-slate-200 rounded-lg p-6 hover:shadow-md transition-shadow"
                        >
                          <div className="flex justify-between items-start mb-4">
                            <div className="flex items-center">
                              <span className="bg-neet-blue text-white w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold mr-3">
                                {originalIndex + 1}
                              </span>
                              <Badge variant="outline" className="text-sm">
                                Question {originalIndex + 1}
                              </Badge>
                              {answer.markedForReview && (
                                <Badge variant="secondary" className="ml-2 text-xs">
                                  Marked for Review
                                </Badge>
                              )}
                            </div>
                            <div className="flex items-center">
                              {answer.isCorrect ? (
                                <>
                                  <CheckCircle className="h-5 w-5 text-neet-green mr-1" />
                                  <span className="text-sm text-neet-green font-medium">
                                    Correct
                                  </span>
                                </>
                              ) : (
                                <>
                                  <XCircle className="h-5 w-5 text-neet-red mr-1" />
                                  <span className="text-sm text-neet-red font-medium">
                                    {answer.selectedAnswer ? "Incorrect" : "Unanswered"}
                                  </span>
                                </>
                              )}
                            </div>
                          </div>
                          
                          <h5 className="font-medium text-slate-900 mb-4 leading-relaxed">
                            {answer.question}
                          </h5>
                          
                          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                            <div className="space-y-2">
                              <h6 className="text-sm font-medium text-slate-700 mb-3">Answer Options</h6>
                              {["A", "B", "C", "D"].map((option) => {
                                const isSelected = answer.selectedAnswer === option;
                                const isCorrect = answer.correctAnswer === option;
                                
                                let bgColor = "bg-slate-50 border-slate-200";
                                let textColor = "text-slate-700";
                                let borderColor = "border-slate-200";
                                
                                if (isCorrect) {
                                  bgColor = "bg-green-50 border-green-200";
                                  textColor = "text-green-800";
                                  borderColor = "border-green-200";
                                } else if (isSelected && !isCorrect) {
                                  bgColor = "bg-red-50 border-red-200";
                                  textColor = "text-red-800";
                                  borderColor = "border-red-200";
                                }
                                
                                return (
                                  <div
                                    key={option}
                                    className={`flex items-center text-sm p-3 rounded-lg border ${bgColor} ${borderColor}`}
                                  >
                                    <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs mr-3 font-medium ${
                                      isCorrect ? "bg-neet-green text-white" : 
                                      isSelected ? "bg-neet-red text-white" : 
                                      "bg-slate-200 text-slate-700"
                                    }`}>
                                      {option}
                                    </span>
                                    <span className={`${textColor} flex-1`}>
                                      {answer[`option${option}` as keyof typeof answer]}
                                    </span>
                                    {isCorrect && (
                                      <Badge variant="outline" className="ml-2 text-xs text-green-600 border-green-300">
                                        Correct Answer
                                      </Badge>
                                    )}
                                    {isSelected && !isCorrect && (
                                      <Badge variant="outline" className="ml-2 text-xs text-red-600 border-red-300">
                                        Your Answer
                                      </Badge>
                                    )}
                                  </div>
                                );
                              })}
                            </div>
                            
                            <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
                              <h6 className="font-medium text-blue-900 mb-2 flex items-center">
                                <BookOpen className="h-4 w-4 mr-2" />
                                Explanation
                              </h6>
                              <p className="text-sm text-blue-800 leading-relaxed">{answer.explanation}</p>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                  
                  {getFilteredAnswers().length === 0 && (
                    <div className="text-center py-12">
                      <div className="text-slate-400 mb-4">
                        <Filter className="h-12 w-12 mx-auto" />
                      </div>
                      <p className="text-slate-600">No questions match the selected filter.</p>
                    </div>
                  )}
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}

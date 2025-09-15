import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
    CheckCircle,
    XCircle,
    Clock,
    Filter,
    BookOpen,
    SlidersHorizontal
} from "lucide-react";

export interface QuestionReviewProps {
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
    correctAnswers: number;
    incorrectAnswers: number;
    unansweredQuestions: number;
}

export function QuestionReview({
    detailedAnswers,
    correctAnswers,
    incorrectAnswers,
    unansweredQuestions
}: QuestionReviewProps) {
    const [reviewFilter, setReviewFilter] = useState<"all" | "correct" | "incorrect" | "unanswered">("all");

    const getFilteredAnswers = () => {
        switch (reviewFilter) {
            case "correct":
                return detailedAnswers.filter(answer => answer.isCorrect);
            case "incorrect":
                return detailedAnswers.filter(answer => !answer.isCorrect && answer.selectedAnswer);
            case "unanswered":
                return detailedAnswers.filter(answer => answer.selectedAnswer === null || answer.selectedAnswer === undefined || answer.selectedAnswer === "");
            default:
                return detailedAnswers;
        }
    };

    return (
        <div>
            <div className="px-3">
                {/* Filter Section */}
                <div className="sticky top-28 -mx-3 px-3 py-3 mb-2 bg-white">
                    <div className="flex items-center gap-2">
                        {/* Filter Label */}
                        <div className="flex items-center space-x-2">
                            <SlidersHorizontal className="h-4 w-4 text-slate-600" />
                            <span className="text-xs text-slate-600">Filter:</span>
                        </div>

                        {/* Horizontal Scroll Container for Filter Options */}
                        <div className="flex-1 overflow-x-auto hide-scrollbar">
                            <div className="flex items-center gap-2 min-w-max">
                                <div className="flex items-center gap-1">
                                    <Button
                                        variant={reviewFilter === "all" ? "secondary" : "outline"}
                                        size="sm"
                                        onClick={() => setReviewFilter("all")}
                                        className="rounded-lg text-xs border"
                                    >
                                        All ({detailedAnswers.length})
                                    </Button>
                                    <Button
                                        variant={reviewFilter === "correct" ? "secondary" : "outline"}
                                        size="sm"
                                        onClick={() => setReviewFilter("correct")}
                                        className="rounded-lg text-xs text-green-700 border"
                                    >
                                        <CheckCircle className="h-3 w-3 mr-1" />
                                        Correct ({correctAnswers})
                                    </Button>
                                    <Button
                                        variant={reviewFilter === "incorrect" ? "secondary" : "outline"}
                                        size="sm"
                                        onClick={() => setReviewFilter("incorrect")}
                                        className="rounded-lg text-xs text-red-700 border"
                                    >
                                        <XCircle className="h-3 w-3 mr-1" />
                                        Incorrect ({incorrectAnswers})
                                    </Button>
                                    <Button
                                        variant={reviewFilter === "unanswered" ? "secondary" : "outline"}
                                        size="sm"
                                        onClick={() => setReviewFilter("unanswered")}
                                        className="rounded-lg text-xs text-amber-700 border"
                                    >
                                        <Clock className="h-3 w-3 mr-1" />
                                        Unanswered ({unansweredQuestions})
                                    </Button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Questions List */}
                <div className="mt-6">
                    {getFilteredAnswers().length === 0 ? (
                        <div className="text-center py-12">
                            <div className="text-slate-400 mb-4">
                                <SlidersHorizontal className="h-12 w-12 mx-auto" />
                            </div>
                            <p className="text-slate-600">No questions match the selected filter.</p>
                        </div>
                    ) : (
                        <div className="space-y-6">
                            {getFilteredAnswers().map((answer, index) => {
                                const originalIndex = detailedAnswers.findIndex(a => a.questionId === answer.questionId);
                                return (
                                    <Card key={answer.questionId} className="mb-4 hover:shadow-md transition-shadow">
                                        <CardContent className="p-4">
                                            <div className="flex flex-col space-y-2 mb-3">
                                                <div className="flex items-center justify-between">
                                                    <div className="flex items-center">
                                                        <Badge variant="outline" className="text-xs">
                                                            Question {originalIndex + 1}
                                                        </Badge>
                                                        {answer.markedForReview && (
                                                            <Badge variant="secondary" className="ml-1 text-xs">
                                                                Marked for Review
                                                            </Badge>
                                                        )}
                                                    </div>
                                                    <div className="flex items-center">
                                                        {answer.isCorrect ? (
                                                            <>
                                                                <CheckCircle className="h-4 w-4 text-green-600 mr-1" />
                                                                <span className="text-xs text-green-600 font-medium">
                                                                    Correct
                                                                </span>
                                                            </>
                                                        ) : (
                                                            <>
                                                                <XCircle className="h-4 w-4 text-red-600 mr-1" />
                                                                <span className="text-xs text-red-600 font-medium">
                                                                    {answer.selectedAnswer ? "Incorrect" : "Unanswered"}
                                                                </span>
                                                            </>
                                                        )}
                                                    </div>
                                                </div>

                                                <h5 className="font-medium text-slate-900 mb-3 leading-relaxed text-sm">
                                                    {answer.question}
                                                </h5>

                                                <div className="grid grid-cols-1 gap-4">
                                                    <div className="space-y-2">
                                                        <h6 className="text-sm font-medium text-slate-700 mb-2">Answer Options</h6>
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

                                                            const optionKey = `option${option}`;
                                                            const optionText = (answer as any)[optionKey];

                                                            return (
                                                                <div key={option} className={`flex items-center text-sm p-2 rounded-lg border ${bgColor} ${borderColor}`}>
                                                                    <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs mr-3 font-medium ${isCorrect ? "bg-green-600 text-white" : isSelected ? "bg-red-600 text-white" : "bg-slate-200 text-slate-700"}`}>
                                                                        {option}
                                                                    </span>
                                                                    <span className={`${textColor} flex-1`}>{optionText}</span>
                                                                    {isCorrect && <Badge variant="outline" className="ml-2 text-xs text-green-600 border-green-300">Correct Answer</Badge>}
                                                                    {isSelected && !isCorrect && <Badge variant="outline" className="ml-2 text-xs text-red-600 border-red-300">Your Answer</Badge>}
                                                                </div>
                                                            );
                                                        })}
                                                    </div>

                                                    <div className="bg-blue-50 p-3 rounded-lg border border-blue-200 mt-3">
                                                        <h6 className="font-medium text-blue-900 mb-2 flex items-center">
                                                            <BookOpen className="h-4 w-4 mr-2" />
                                                            Explanation
                                                        </h6>
                                                        <p className="text-xs text-blue-800 leading-relaxed">{answer.explanation}</p>
                                                    </div>
                                                </div>
                                            </div>
                                        </CardContent>
                                    </Card>
                                );
                            })}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
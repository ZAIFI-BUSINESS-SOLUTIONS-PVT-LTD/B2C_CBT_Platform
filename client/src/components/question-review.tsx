import { useState, useRef, useEffect } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
    CheckCircle,
    XCircle,
    Clock,
    Filter,
    BookOpen,
    SlidersHorizontal,
    ChevronLeft,
    ChevronRight
} from "lucide-react";
import normalizeImageSrc from "@/lib/media";

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
        // optional base64 image data URIs (camelCase keys from API)
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

export function QuestionReview({
    detailedAnswers,
    correctAnswers,
    incorrectAnswers,
    unansweredQuestions
}: QuestionReviewProps) {
    const [reviewFilter, setReviewFilter] = useState<"all" | "correct" | "incorrect" | "unanswered">("all");
    const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
    const touchStartX = useRef<number | null>(null);
    const touchEndX = useRef<number | null>(null);

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

    const filteredAnswers = getFilteredAnswers();
    
    // Reset to first question when filter changes
    useEffect(() => {
        setCurrentQuestionIndex(0);
    }, [reviewFilter]);

    // Swipe handlers
    const handleTouchStart = (e: React.TouchEvent) => {
        touchStartX.current = e.touches[0].clientX;
    };

    const handleTouchMove = (e: React.TouchEvent) => {
        touchEndX.current = e.touches[0].clientX;
    };

    const handleTouchEnd = () => {
        if (!touchStartX.current || !touchEndX.current) return;
        
        const diff = touchStartX.current - touchEndX.current;
        const minSwipeDistance = 50;

        if (Math.abs(diff) > minSwipeDistance) {
            if (diff > 0 && currentQuestionIndex < filteredAnswers.length - 1) {
                // Swiped left - go to next question
                setCurrentQuestionIndex(prev => prev + 1);
            } else if (diff < 0 && currentQuestionIndex > 0) {
                // Swiped right - go to previous question
                setCurrentQuestionIndex(prev => prev - 1);
            }
        }

        touchStartX.current = null;
        touchEndX.current = null;
    };

    const goToPrevious = () => {
        if (currentQuestionIndex > 0) {
            setCurrentQuestionIndex(prev => prev - 1);
        }
    };

    const goToNext = () => {
        if (currentQuestionIndex < filteredAnswers.length - 1) {
            setCurrentQuestionIndex(prev => prev + 1);
        }
    };

    return (
        <div>
            <div className="px-3">
                {/* Filter Section */}
                <div className="sticky top-14 -mx-3 px-3 py-3 mb-2 bg-white/90 backdrop-blur-md border-b border-white/90 z-30">
                    <div className="flex items-center gap-2">
                        {/* Filter Label */}
                        <div className="flex items-center space-x-2">
                            <SlidersHorizontal className="h-4 w-4 text-gray-700" />
                            <span className="text-xs text-gray-700">Filter:</span>
                        </div>

                        {/* Horizontal Scroll Container for Filter Options */}
                        <div 
                            className="flex-1 overflow-x-auto hide-scrollbar"
                            style={{
                              overscrollBehaviorX: 'auto',
                              WebkitOverflowScrolling: 'touch'
                            }}
                        >
                            <div className="flex items-center gap-2 min-w-max">
                                <div className="flex items-center gap-1">
                                    <Button
                                        variant={reviewFilter === "all" ? "secondary" : "outline"}
                                        size="sm"
                                        onClick={() => setReviewFilter("all")}
                                        className="rounded-lg text-xs border bg-transparent text-gray-900 hover:bg-white/5"
                                    >
                                        All ({detailedAnswers.length})
                                    </Button>
                                    <Button
                                        variant={reviewFilter === "correct" ? "secondary" : "outline"}
                                        size="sm"
                                        onClick={() => setReviewFilter("correct")}
                                        className="rounded-lg text-xs text-green-700 border bg-transparent hover:bg-white/5"
                                    >
                                        <CheckCircle className="h-3 w-3 mr-1" />
                                        Correct ({correctAnswers})
                                    </Button>
                                    <Button
                                        variant={reviewFilter === "incorrect" ? "secondary" : "outline"}
                                        size="sm"
                                        onClick={() => setReviewFilter("incorrect")}
                                        className="rounded-lg text-xs text-red-700 border bg-transparent hover:bg-white/5"
                                    >
                                        <XCircle className="h-3 w-3 mr-1" />
                                        Incorrect ({incorrectAnswers})
                                    </Button>
                                    <Button
                                        variant={reviewFilter === "unanswered" ? "secondary" : "outline"}
                                        size="sm"
                                        onClick={() => setReviewFilter("unanswered")}
                                        className="rounded-lg text-xs text-amber-700 border bg-transparent hover:bg-white/5"
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
                    {filteredAnswers.length === 0 ? (
                        <div className="text-center py-12">
                            <div className="text-gray-400 mb-4">
                                <SlidersHorizontal className="h-12 w-12 mx-auto" />
                            </div>
                            <p className="text-gray-700">No questions match the selected filter.</p>
                        </div>
                    ) : (
                        <div className="relative">
                            

                            {/* Swipeable Question Card */}
                            <div 
                                className="relative overflow-hidden"
                                onTouchStart={handleTouchStart}
                                onTouchMove={handleTouchMove}
                                onTouchEnd={handleTouchEnd}
                            >
                                {filteredAnswers.map((answer, index) => {
                                    if (index !== currentQuestionIndex) return null;
                                    
                                    const originalIndex = detailedAnswers.findIndex(a => a.questionId === answer.questionId);
                                    return (
                                        <Card key={answer.questionId} className="mb-4 bg-white/80 backdrop-blur-sm border-transparent hover:bg-white/90 transition-all duration-200 shadow-lg">
                                            <CardContent className="p-4">
                                                <div className="flex flex-col space-y-2 mb-3">
                                                    <div className="flex items-center justify-between">
                                                        <div className="flex items-center">
                                                            <Badge variant="outline" className="text-xs bg-transparent text-gray-900 border-transparent">
                                                                Question {originalIndex + 1}
                                                            </Badge>
                                                            {answer.markedForReview && (
                                                                <Badge className="ml-1 text-xs bg-amber-500/30 text-gray-900 border-amber-400/40">
                                                                    Marked for Review
                                                                </Badge>
                                                            )}
                                                        </div>
                                                        <div className="flex items-center">
                                                            {answer.isCorrect ? (
                                                                <>
                                                                    <CheckCircle className="h-4 w-4 text-green-600 mr-1" />
                                                                    <span className="text-xs text-green-600 font-medium">Correct</span>
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

                                                    <h5 className="font-medium text-gray-900 mb-3 leading-relaxed text-sm">
                                                        {answer.question}
                                                    </h5>

                                                    {/* Question image (if any) */}
                                                    {normalizeImageSrc((answer as any).questionImage) && (
                                                        <img
                                                            src={normalizeImageSrc((answer as any).questionImage)}
                                                            alt={`Question ${originalIndex + 1} image`}
                                                            className="w-full max-w-full rounded-md mt-2 object-contain max-h-48"
                                                        />
                                                    )}
                                                    <div className="grid grid-cols-1 gap-4">
                                                        <div className="space-y-2">
                                                            <h6 className="text-sm font-medium text-gray-700 mb-2">Answer Options</h6>
                                                            {["A", "B", "C", "D"].map((option) => {
                                                                const isSelected = answer.selectedAnswer === option;
                                                                const isCorrect = answer.correctAnswer === option;

                                                                // Make options use the same glassmorphic translucent container as bookmarks
                                                                let bgColor = "bg-white/25";
                                                                let textColor = "text-gray-900";
                                                                let borderColor = "border border-transparent";

                                                                if (isCorrect) {
                                                                    bgColor = "bg-green-500/20";
                                                                    textColor = "text-green-800";
                                                                    borderColor = "border-2 border-green-400";
                                                                } else if (isSelected && !isCorrect) {
                                                                    bgColor = "bg-red-500/20";
                                                                    textColor = "text-red-800";
                                                                    borderColor = "border-2 border-red-400";
                                                                }

                                                                const optionKey = `option${option}`;
                                                                const optionText = (answer as any)[optionKey];
                                                                const optionImageKey = `${optionKey}Image`;
                                                                const optionImage = (answer as any)[optionImageKey];
                                                                const optionImageSrc = normalizeImageSrc(optionImage);

                                                                return (
                                                                    <div key={option} className={`flex items-center text-sm p-2 rounded-lg ${bgColor} ${borderColor}`}>
                                                                        <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs mr-3 font-medium ${isCorrect ? "bg-green-600 text-white" : isSelected ? "bg-red-600 text-white" : "bg-white/30 text-gray-900"}`}>
                                                                            {option}
                                                                        </span>
                                                                        <span className={`${textColor} flex-1`}>{optionText}</span>
                                                                        {/* Option image (if any) */}
                                                                        {optionImageSrc && (
                                                                            <img
                                                                                src={optionImageSrc}
                                                                                alt={`Option ${option} image`}
                                                                                className="ml-3 rounded-md max-h-36 object-contain"
                                                                            />
                                                                        )}
                                                                        {isCorrect && <Badge variant="outline" className="ml-2 text-xs text-green-600 border-green-300">Correct Answer</Badge>}
                                                                        {isSelected && !isCorrect && <Badge variant="outline" className="ml-2 text-xs text-red-600 border-red-300">Your Answer</Badge>}
                                                                    </div>
                                                                );
                                                            })}
                                                        </div>

                                                        <div className="bg-white/90 p-3 rounded-lg border border-transparent mt-3">
                                                            <h6 className="font-medium text-gray-900 mb-2 flex items-center">
                                                                <BookOpen className="h-4 w-4 mr-2" />
                                                                Explanation
                                                            </h6>
                                                                {/* Explanation image (if any) */}
                                                                {normalizeImageSrc((answer as any).explanationImage) && (
                                                                    <img
                                                                        src={normalizeImageSrc((answer as any).explanationImage)}
                                                                        alt={`Explanation for Question ${originalIndex + 1}`}
                                                                        className="w-full rounded-md mb-3 object-contain max-h-48"
                                                                    />
                                                                )}
                                                                <p className="text-xs text-gray-800 leading-relaxed">{answer.explanation}</p>
                                                        </div>
                                                    </div>
                                                </div>
                                            </CardContent>
                                        </Card>
                                    );
                                })}
                            </div>

                            {/* Navigation Arrows */}
                            <div className="flex items-center justify-between mt-4 px-4">
                                <Button
                                    variant="outline"
                                    size="icon"
                                    onClick={goToPrevious}
                                    disabled={currentQuestionIndex === 0}
                                    className="h-10 w-10 rounded-full bg-white/80 hover:bg-white disabled:opacity-30"
                                >
                                    <ChevronLeft className="h-5 w-5" />
                                </Button>

                                {/* Question Dots Indicator */}
                                <div className="flex gap-1.5">
                                    {filteredAnswers.map((_, index) => (
                                        <button
                                            key={index}
                                            onClick={() => setCurrentQuestionIndex(index)}
                                            className={`h-2 rounded-full transition-all ${
                                                index === currentQuestionIndex 
                                                    ? 'w-6 bg-blue-600' 
                                                    : 'w-2 bg-gray-300 hover:bg-gray-400'
                                            }`}
                                            aria-label={`Go to question ${index + 1}`}
                                        />
                                    ))}
                                </div>

                                <Button
                                    variant="outline"
                                    size="icon"
                                    onClick={goToNext}
                                    disabled={currentQuestionIndex === filteredAnswers.length - 1}
                                    className="h-10 w-10 rounded-full bg-white/80 hover:bg-white disabled:opacity-30"
                                >
                                    <ChevronRight className="h-5 w-5" />
                                </Button>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
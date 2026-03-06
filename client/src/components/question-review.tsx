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

// Helper: accept camelCase key and fall back to snake_case key on the answer object
function getImageValue(answer: any, camelKey: string) {
    const snake = camelKey.replace(/([A-Z])/g, '_$1').toLowerCase();
    return answer?.[camelKey] ?? answer?.[snake];
}

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
    // Pointer-based drag support (works for mouse + stylus + touch where Pointer Events are available)
    const pointerStart = useRef<{ x: number; y: number; id?: number } | null>(null);
    const pointerEnd = useRef<{ x: number; y: number } | null>(null);
    const pointerActive = useRef(false);

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
        // keep for compatibility but prefer pointer handlers
        touchStartX.current = e.touches[0].clientX;
    };

    const handleTouchMove = (e: React.TouchEvent) => {
        touchEndX.current = e.touches[0].clientX;
    };

    const handleTouchEnd = () => {
        // Fallback to legacy touch only if pointer events did not run
        if (pointerActive.current) {
            // pointer handlers already handled it
            touchStartX.current = null;
            touchEndX.current = null;
            return;
        }

        if (touchStartX.current == null || touchEndX.current == null) return;

        const diff = touchStartX.current - touchEndX.current;
        const minSwipeDistance = 50;

        if (Math.abs(diff) > minSwipeDistance) {
            if (diff > 0 && currentQuestionIndex < filteredAnswers.length - 1) {
                setCurrentQuestionIndex(prev => prev + 1);
            } else if (diff < 0 && currentQuestionIndex > 0) {
                setCurrentQuestionIndex(prev => prev - 1);
            }
        }

        touchStartX.current = null;
        touchEndX.current = null;
    };

    // Pointer event handlers (mouse + touch unified)
    const handlePointerDown = (e: React.PointerEvent) => {
        pointerActive.current = true;
        pointerStart.current = { x: e.clientX, y: e.clientY, id: e.pointerId };
        pointerEnd.current = null;
        try { (e.target as Element).setPointerCapture?.(e.pointerId); } catch (err) { /* ignore */ }
    };

    const handlePointerMove = (e: React.PointerEvent) => {
        if (!pointerActive.current || !pointerStart.current) return;
        pointerEnd.current = { x: e.clientX, y: e.clientY };
    };

    const handlePointerUp = (e?: React.PointerEvent | undefined) => {
        if (!pointerActive.current || !pointerStart.current || !pointerEnd.current) {
            pointerActive.current = false;
            pointerStart.current = null;
            pointerEnd.current = null;
            return;
        }

        const start = pointerStart.current;
        const end = pointerEnd.current;
        const dx = end.x - start.x;
        const dy = end.y - start.y;
        const absDx = Math.abs(dx);
        const absDy = Math.abs(dy);
        const minSwipeDistance = 50;

        // Only treat as horizontal swipe if horizontal movement is dominant
        if (absDx > absDy && absDx > minSwipeDistance) {
            if (dx < 0 && currentQuestionIndex < filteredAnswers.length - 1) {
                setCurrentQuestionIndex(prev => prev + 1);
            } else if (dx > 0 && currentQuestionIndex > 0) {
                setCurrentQuestionIndex(prev => prev - 1);
            }
        }

        // Reset pointer state
        pointerActive.current = false;
        pointerStart.current = null;
        pointerEnd.current = null;
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
                                onPointerDown={handlePointerDown}
                                onPointerMove={handlePointerMove}
                                onPointerUp={handlePointerUp}
                                onPointerCancel={handlePointerUp}
                                // Allow vertical scrolling by default; capture horizontal drags for swipe
                                style={{ touchAction: 'pan-y' }}
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

                                                    <h5 className="font-medium text-gray-900 mb-3 leading-relaxed text-sm whitespace-pre-line">
                                                        {answer.question}
                                                    </h5>

                                                    {/* Question image (if any) */}
                                                    {normalizeImageSrc(getImageValue(answer, 'questionImage')) && (
                                                        <img
                                                            src={normalizeImageSrc(getImageValue(answer, 'questionImage'))}
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
                                                                const optionImage = getImageValue(answer, optionImageKey);
                                                                const optionImageSrc = normalizeImageSrc(optionImage);

                                                                return (
                                                                    <div key={option} className={`flex items-center text-sm p-2 rounded-lg ${bgColor} ${borderColor}`}>
                                                                        <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs mr-3 font-medium ${isCorrect ? "bg-green-600 text-white" : isSelected ? "bg-red-600 text-white" : "bg-white/30 text-gray-900"}`}>
                                                                            {option}
                                                                        </span>
                                                                        <span className={`${textColor} flex-1 whitespace-pre-line`}>{optionText}</span>
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
                                                                {normalizeImageSrc(getImageValue(answer, 'explanationImage')) && (
                                                                    <img
                                                                        src={normalizeImageSrc(getImageValue(answer, 'explanationImage'))}
                                                                        alt={`Explanation for Question ${originalIndex + 1}`}
                                                                        className="w-full rounded-md mb-3 object-contain max-h-48"
                                                                    />
                                                                )}
                                                                <p className="text-xs text-gray-800 leading-relaxed whitespace-pre-line">{answer.explanation}</p>
                                                        </div>
                                                    </div>
                                                </div>
                                            </CardContent>
                                        </Card>
                                    );
                                })}
                            </div>

                            {/* Simplified three-dot indicator */}
                            <div className="flex items-center justify-center mt-4 px-4">
                                <div className="flex items-center gap-4">
                                    {/* Left dot (previous) */}
                                    <button
                                        onClick={() => { if (currentQuestionIndex > 0) setCurrentQuestionIndex(currentQuestionIndex - 1); }}
                                        aria-label={currentQuestionIndex > 0 ? `Previous question ${currentQuestionIndex}` : 'No previous question'}
                                        className={`w-3 h-3 rounded-full transition-transform ${currentQuestionIndex > 0 ? 'bg-white/95 hover:scale-110 border border-white/30' : 'bg-white/60 opacity-40 cursor-default'}`}
                                        disabled={currentQuestionIndex === 0}
                                    />

                                    {/* Center dot (current) - slightly larger and shows current number */}
                                    <button
                                        onClick={() => { /* no-op or could open answer index */ }}
                                        aria-label={`Current question ${currentQuestionIndex + 1}`}
                                        className="flex items-center justify-center w-10 h-10 rounded-full bg-white border border-slate-100 shadow-sm"
                                        title={`Question ${currentQuestionIndex + 1}`}
                                    >
                                        <span className="text-sm font-semibold text-slate-700">{currentQuestionIndex + 1}</span>
                                    </button>

                                    {/* Right dot (next) */}
                                    <button
                                        onClick={() => { if (currentQuestionIndex < filteredAnswers.length - 1) setCurrentQuestionIndex(currentQuestionIndex + 1); }}
                                        aria-label={currentQuestionIndex < filteredAnswers.length - 1 ? `Next question ${currentQuestionIndex + 2}` : 'No next question'}
                                        className={`w-3 h-3 rounded-full transition-transform ${currentQuestionIndex < filteredAnswers.length - 1 ? 'bg-white/95 hover:scale-110 border border-white/30' : 'bg-white/60 opacity-40 cursor-default'}`}
                                        disabled={currentQuestionIndex >= filteredAnswers.length - 1}
                                    />
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
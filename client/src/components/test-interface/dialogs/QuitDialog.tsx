import { X } from "lucide-react";
import { createPortal } from "react-dom";
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from "@/components/ui/alert-dialog";

interface QuitDialogProps {
    isOpen: boolean;
    answersCount: number;
    totalQuestions: number;
    isPending?: boolean;
    onConfirm: () => void;
    onCancel: () => void;
}

export function QuitDialog({ isOpen, answersCount, totalQuestions, onConfirm, onCancel, isPending }: QuitDialogProps) {
    return (
        <AlertDialog open={isOpen} onOpenChange={() => { }} >
            {isOpen && typeof document !== "undefined"
                ? createPortal(
                      <img
                          src="/quit-penguin.webp"
                          alt="quit-penguin"
                          className="pointer-events-none"
                          style={{
                              position: "fixed",
                              left: "50%",
                              transform: "translateX(-50%) scale(1.5)",
                              top: "calc(50% - 220px)",
                              width: "96px",
                              zIndex: 2147483647,
                              pointerEvents: "none",
                          }}
                      />,
                      document.body
                  )
                : null}
            <AlertDialogContent className="relative overflow-visible bg-gradient-to-b from-blue-50 to-white border border-blue-100 rounded-2xl shadow-2xl w-[90%] max-w-sm px-6 sm:px-8 fixed left-1/2 top-1/2 translate-x-[-50%] translate-y-[-50%] max-h-[90vh] overflow-auto">
                {/* Glossy sheen overlay */}
                <div className="absolute left-4 right-4 top-4 h-24 rounded-t-2xl pointer-events-none z-20" style={{ background: 'linear-gradient(180deg, rgba(255,255,255,0.9), rgba(255,255,255,0.35))', mixBlendMode: 'overlay', opacity: 0.9 }} />
                <AlertDialogHeader className="space-y-4 pt-16 relative z-10">
                    <AlertDialogTitle className="text-blue-600 font-bold text-2xl text-center">
                        Quit Exam?
                    </AlertDialogTitle>
                    <AlertDialogDescription className="text-slate-600 text-sm text-center leading-relaxed px-2 max-w-xs mx-auto">
                        Are you sure you want to quit the exam? Your test will be submitted and marked as completed. You won't be able to resume it later. You have answered {answersCount} out of {totalQuestions} questions.
                    </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter className="flex-col gap-4 mt-6 relative z-10">
                    <AlertDialogAction onClick={onConfirm} className="bg-red-600 hover:bg-red-700 text-white w-full py-3.5 rounded-xl text-base font-semibold shadow-md hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-red-100 disabled:opacity-50 disabled:cursor-not-allowed" disabled={isPending}>
                        {isPending ? (
                            <div className="flex items-center justify-center">
                                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />
                                Quitting...
                            </div>
                        ) : (
                            "Quit Exam"
                        )}
                    </AlertDialogAction>
                    <AlertDialogCancel onClick={onCancel} className="bg-emerald-500 hover:bg-emerald-600 text-white w-full py-3.5 rounded-xl text-base font-semibold shadow-md focus:outline-none focus:ring-2 focus:ring-emerald-100">Continue Exam</AlertDialogCancel>
                </AlertDialogFooter>
            </AlertDialogContent>
        </AlertDialog>
    );
}

export default QuitDialog;

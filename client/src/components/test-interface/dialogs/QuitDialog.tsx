import { AlertTriangle } from "lucide-react";
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
            <AlertDialogContent className="bg-white border border-[#E2E8F0] rounded-xl sm:rounded-2xl shadow-lg my-8 w-[90%] max-w-sm px-6 sm:px-8">
                <AlertDialogHeader className="space-y-3">
                    <AlertDialogTitle className="text-slate-900 flex items-center justify-center font-bold text-lg text-center">
                        <AlertTriangle className="h-5 w-5 mr-2 text-rose-500" />
                        Quit Exam?
                    </AlertDialogTitle>
                    <AlertDialogDescription className="text-slate-500 text-sm text-center leading-relaxed">
                        Are you sure you want to quit the exam? Your test will be marked as incomplete and you won't be able to resume it later. You have answered {answersCount} out of {totalQuestions} questions.
                    </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter className="flex-col gap-3 mt-4">
                    <AlertDialogCancel onClick={onCancel} className="bg-emerald-500 hover:bg-emerald-600 text-white w-full py-3 rounded-lg">Continue Exam</AlertDialogCancel>
                    <AlertDialogAction onClick={onConfirm} className="bg-blue-600 hover:bg-blue-700 text-white w-full py-3 rounded-lg" disabled={isPending}>
                        {isPending ? (
                            <div className="flex items-center justify-center">
                                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />
                                Quitting...
                            </div>
                        ) : (
                            "Quit Exam"
                        )}
                    </AlertDialogAction>
                </AlertDialogFooter>
            </AlertDialogContent>
        </AlertDialog>
    );
}

export default QuitDialog;

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
            <AlertDialogContent className="max-w-sm">
                <AlertDialogHeader>
                    <AlertDialogTitle className="text-gray-800 flex items-center justify-center font-bold text-lg text-center">
                        <AlertTriangle className="h-4 w-4 mr-2 text-red-500" />
                        Quit Exam?
                    </AlertDialogTitle>
                    <AlertDialogDescription className="text-gray-600 text-sm text-center">
                        Are you sure you want to quit the exam? Your test will be marked as incomplete and
                        you won't be able to resume it later. You have answered {answersCount} out of {totalQuestions} questions.
                    </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter className="flex-col gap-2">
                    <AlertDialogCancel onClick={onCancel} className="bg-emerald-500 hover:bg-emerald-600 text-white border-none w-full">
                        Continue Exam
                    </AlertDialogCancel>
                    <AlertDialogAction onClick={onConfirm} className="bg-blue-500 hover:bg-blue-600 text-white w-full" disabled={isPending}>
                        {isPending ? (
                            <>
                                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />
                                Quitting...
                            </>
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

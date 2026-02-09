import { Check } from "lucide-react";
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

interface SubmitDialogProps {
  isOpen: boolean;
  answersCount: number;
  totalQuestions: number;
  onConfirm: () => void;
  onCancel: () => void;
}

export function SubmitDialog({
  isOpen,
  answersCount,
  totalQuestions,
  onConfirm,
  onCancel,
}: SubmitDialogProps) {
  return (
    <AlertDialog
      open={isOpen}
      onOpenChange={(open) => {
        if (!open) onCancel();
      }}
    >
      <AlertDialogContent className="bg-white border border-[#E2E8F0] rounded-xl sm:rounded-2xl shadow-lg my-8 w-[90%] max-w-sm px-6 sm:px-8">
        <AlertDialogHeader className="space-y-3">
          <AlertDialogTitle className="text-slate-900 font-bold text-base sm:text-xl text-center">Submit Test?</AlertDialogTitle>
          <div className="flex flex-col items-center gap-3">
            <div className="w-full bg-sky-50 rounded-lg p-3">
              <div className="flex justify-between gap-3">
                <div className="flex-1 text-center p-3 bg-white rounded-md border border-slate-100 shadow-sm">
                  <div className="text-sm text-slate-400">Attempted</div>
                  <div className="text-2xl font-semibold text-slate-900 mt-1">{answersCount}</div>
                </div>
                <div className="flex-1 text-center p-3 bg-white rounded-md border border-slate-100 shadow-sm">
                  <div className="text-sm text-slate-400">Skipped</div>
                  <div className="text-2xl font-semibold text-slate-900 mt-1">{Math.max(0, totalQuestions - answersCount)}</div>
                </div>
              </div>
            </div>
            {totalQuestions - answersCount > 0 && (
              <div className="w-full text-sm text-amber-700 bg-amber-50 border border-amber-100 rounded-md p-2">You still have {totalQuestions - answersCount} unanswered question{totalQuestions - answersCount > 1 ? "s" : ""}</div>
            )}
          </div>
        </AlertDialogHeader>
        <AlertDialogFooter className="flex-col sm:flex-row gap-3 mt-4">
          <AlertDialogAction onClick={onConfirm} className="bg-blue-600 hover:bg-blue-700 text-white w-full sm:w-auto order-1 sm:order-2 flex items-center justify-center py-3 rounded-lg">
            <Check className="h-4 w-4 mr-2" />
            Submit Test
          </AlertDialogAction>
          <AlertDialogCancel className="border border-slate-200 text-slate-700 bg-white hover:bg-slate-50 w-full sm:w-auto order-2 sm:order-1 py-3 rounded-lg">Continue Test</AlertDialogCancel>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

export default SubmitDialog;

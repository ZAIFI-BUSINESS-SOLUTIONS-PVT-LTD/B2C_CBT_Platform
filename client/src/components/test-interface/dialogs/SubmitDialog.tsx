import { Check } from "lucide-react";
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

interface SubmitDialogProps {
  isOpen: boolean;
  answersCount: number;
  totalQuestions: number;
  markedCount?: number;
  onConfirm: () => void;
  onCancel: () => void;
}

export function SubmitDialog({
  isOpen,
  answersCount,
  totalQuestions,
  markedCount = 0,
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
      {isOpen && typeof document !== "undefined"
        ? createPortal(
            <img
              src="/submit-penguin.webp"
              alt="submit-penguin"
              className="pointer-events-none"
              style={{
                position: "fixed",
                left: "50%",
                transform: "translateX(-50%) scale(1.5)",
                top: "calc(50% - 220px)",
                width: "100px",
                zIndex: 2147483647,
                pointerEvents: "none",
              }}
            />,
            document.body
          )
        : null}

      <AlertDialogContent className="bg-white border border-[#E2E8F0] rounded-xl sm:rounded-2xl shadow-lg my-8 w-[90%] max-w-sm px-6 sm:px-8">
        <AlertDialogHeader className="space-y-3">
          <AlertDialogTitle className="text-slate-900 font-bold text-base sm:text-xl text-center">Submit Test?</AlertDialogTitle>
          <div className="flex flex-col items-center gap-3">
            <div className="w-full bg-sky-100 rounded-lg p-2">
                <div className="grid grid-cols-3 gap-2">
                  <div className="min-w-0 text-center p-2 bg-white rounded-md border border-slate-200 shadow-sm">
                    <div className="text-xs text-slate-500">Attempted</div>
                    <div className="text-xl sm:text-2xl font-semibold text-slate-900 mt-1">{answersCount}</div>
                  </div>
                  <div className="min-w-0 text-center p-2 bg-white rounded-md border border-slate-200 shadow-sm">
                    <div className="text-xs text-slate-500">Skipped</div>
                    <div className="text-xl sm:text-2xl font-semibold text-slate-900 mt-1">{Math.max(0, totalQuestions - answersCount)}</div>
                  </div>
                  <div className="min-w-0 text-center p-2 bg-white rounded-md border border-slate-200 shadow-sm">
                    <div className="text-xs text-slate-500">Marked</div>
                    <div className="text-xl sm:text-2xl font-semibold text-slate-900 mt-1">{markedCount}</div>
                  </div>
                </div>
              </div>
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

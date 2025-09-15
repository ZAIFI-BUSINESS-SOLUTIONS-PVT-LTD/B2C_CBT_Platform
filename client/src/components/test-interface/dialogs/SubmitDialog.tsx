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
      <AlertDialogContent className="bg-white border border-[#E2E8F0] rounded-xl sm:rounded-2xl shadow-lg mx-4 max-w-sm sm:max-w-md">
        <AlertDialogHeader>
          <AlertDialogTitle className="text-[#1F2937] font-bold text-lg sm:text-xl">Submit Test?</AlertDialogTitle>
          <AlertDialogDescription className="text-[#6B7280] text-sm sm:text-base">
            Are you sure you want to submit your test? This action cannot be undone.
            You have answered {answersCount} out of {totalQuestions} questions.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter className="flex-col sm:flex-row gap-2 sm:gap-0">
          <AlertDialogCancel className="border-[#E2E8F0] text-[#6B7280] hover:bg-[#F8FAFC] w-full sm:w-auto">Cancel</AlertDialogCancel>
          <AlertDialogAction onClick={onConfirm} className="bg-[#DC2626] hover:bg-[#B91C1C] text-white w-full sm:w-auto">
            <Check className="h-4 w-4 mr-2" />
            Submit Test
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

export default SubmitDialog;

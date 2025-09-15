import { Check, Clock } from "lucide-react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

interface TimeOverDialogProps {
  isOpen: boolean;
  answersCount: number;
  totalQuestions: number;
  onSubmit: () => void;
}

export function TimeOverDialog({ isOpen, answersCount, totalQuestions, onSubmit }: TimeOverDialogProps) {
  return (
    <AlertDialog open={isOpen} onOpenChange={() => {}}>
      <AlertDialogContent className="border-[#FCA5A5] bg-[#FEF2F2] rounded-xl sm:rounded-2xl shadow-lg mx-4 max-w-sm sm:max-w-md">
        <AlertDialogHeader>
          <AlertDialogTitle className="text-[#DC2626] flex items-center font-bold text-lg sm:text-xl">
            <Clock className="h-4 w-4 sm:h-5 sm:w-5 mr-2" />
            Time Over!
          </AlertDialogTitle>
          <AlertDialogDescription className="text-[#DC2626] text-sm sm:text-base">
            Your test time has expired. Your test will be automatically submitted in 10 seconds,
            or you can submit it now manually. You have answered {answersCount} out of {totalQuestions} questions.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogAction onClick={onSubmit} className="bg-[#DC2626] hover:bg-[#B91C1C] text-white w-full">
            <Check className="h-4 w-4 mr-2" />
            Submit Test Now
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

export default TimeOverDialog;

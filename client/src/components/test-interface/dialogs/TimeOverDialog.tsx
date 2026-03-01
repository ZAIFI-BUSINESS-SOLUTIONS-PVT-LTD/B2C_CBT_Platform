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
      {/* Use same centered fixed layout as other popups for visual consistency */}
      <AlertDialogContent className="relative overflow-visible bg-gradient-to-b from-blue-50 to-white border border-blue-100 rounded-2xl shadow-2xl w-[90%] max-w-sm px-6 sm:px-8 fixed left-1/2 top-1/2 translate-x-[-50%] translate-y-[-50%] max-h-[90vh] overflow-auto">
        {/* Glossy sheen overlay */}
        <div className="absolute left-4 right-4 top-4 h-20 rounded-t-2xl pointer-events-none z-20" style={{ background: 'linear-gradient(180deg, rgba(255,255,255,0.9), rgba(255,255,255,0.35))', mixBlendMode: 'overlay', opacity: 0.9 }} />
        <AlertDialogHeader className="space-y-4 pt-12 relative z-10 text-center">
          <AlertDialogTitle className="text-blue-600 font-bold text-2xl">
            <span className="inline-flex items-center justify-center gap-2">
              <Clock className="h-5 w-5" />
              Time Over!
            </span>
          </AlertDialogTitle>
          <AlertDialogDescription className="text-slate-600 text-sm leading-relaxed px-2 max-w-xs mx-auto">
            Your test time has expired. Your test will be automatically submitted in 10 seconds, or you can submit it now manually. You have answered {answersCount} out of {totalQuestions} questions.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter className="flex-col gap-4 mt-6 relative z-10">
          <AlertDialogAction onClick={onSubmit} className="bg-blue-600 hover:bg-blue-700 text-white w-full py-3.5 rounded-xl text-base font-semibold shadow-md hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-blue-100 flex items-center justify-center">
            <Check className="h-4 w-4 mr-2" />
            Submit Test Now
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

export default TimeOverDialog;

/**
 * Question Feedback Dialog Component
 * 
 * Allows students to report issues with questions during a test.
 * Feedback types include: incorrect question, out of syllabus, 
 * incorrect options, unclear question, or other.
 */

import { useState } from "react";
import { Flag } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface QuestionFeedbackDialogProps {
  isOpen: boolean;
  questionId: number;
  onClose: () => void;
  onSubmit: (feedbackType: string, remarks: string) => Promise<void>;
  isSubmitting?: boolean;
}

const FEEDBACK_OPTIONS = [
  { value: "INCORRECT_QUESTION", label: "Incorrect Question" },
  { value: "OUT_OF_SYLLABUS", label: "Out of Syllabus" },
  { value: "OPTIONS_INCORRECT", label: "Options are Incorrect" },
  { value: "QUESTION_UNCLEAR", label: "Question is Unclear" },
  { value: "OTHER", label: "Other" },
];

export function QuestionFeedbackDialog({
  isOpen,
  questionId,
  onClose,
  onSubmit,
  isSubmitting = false,
}: QuestionFeedbackDialogProps) {
  const [feedbackType, setFeedbackType] = useState<string>("");
  const [remarks, setRemarks] = useState<string>("");
  const [validationError, setValidationError] = useState<string>("");

  const handleSubmit = async () => {
    // Validate feedback type is selected
    if (!feedbackType) {
      setValidationError("Please select a feedback type");
      return;
    }

    setValidationError("");

    try {
      await onSubmit(feedbackType, remarks);
      // Reset form on success
      setFeedbackType("");
      setRemarks("");
      onClose();
    } catch (error) {
      // Error is handled by parent component
      console.error("Failed to submit feedback:", error);
    }
  };

  const handleClose = () => {
    if (!isSubmitting) {
      setFeedbackType("");
      setRemarks("");
      setValidationError("");
      onClose();
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="bg-white border border-[#E2E8F0] rounded-xl sm:rounded-2xl shadow-lg w-[90%] max-w-md">
        <DialogHeader className="space-y-2">
          <DialogTitle className="text-slate-900 font-bold text-lg flex items-center gap-2">
            <Flag className="h-5 w-5 text-orange-500" />
            Question Feedback
          </DialogTitle>
          <DialogDescription className="text-slate-600 text-sm">
            Report an issue with this question. Your feedback helps us improve the quality of our questions.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Feedback Type Selection */}
          <div className="space-y-2">
            <Label htmlFor="feedback-type" className="text-sm font-medium text-slate-700">
              Feedback Type <span className="text-red-500">*</span>
            </Label>
            <Select
              value={feedbackType}
              onValueChange={(value) => {
                setFeedbackType(value);
                setValidationError("");
              }}
              disabled={isSubmitting}
            >
              <SelectTrigger
                id="feedback-type"
                className={`w-full ${validationError ? "border-red-500" : ""}`}
              >
                <SelectValue placeholder="Select an issue type" />
              </SelectTrigger>
              <SelectContent>
                {FEEDBACK_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {validationError && (
              <p className="text-xs text-red-500">{validationError}</p>
            )}
          </div>

          {/* Remarks (Optional) */}
          <div className="space-y-2">
            <Label htmlFor="remarks" className="text-sm font-medium text-slate-700">
              Additional Comments <span className="text-slate-400">(Optional)</span>
            </Label>
            <Textarea
              id="remarks"
              placeholder="Provide additional details about the issue..."
              value={remarks}
              onChange={(e) => setRemarks(e.target.value)}
              disabled={isSubmitting}
              className="min-h-[100px] resize-none"
              maxLength={500}
            />
            <p className="text-xs text-slate-400 text-right">
              {remarks.length}/500 characters
            </p>
          </div>
        </div>

        <DialogFooter className="flex-col sm:flex-row gap-2">
          <Button
            variant="outline"
            onClick={handleClose}
            disabled={isSubmitting}
            className="w-full sm:w-auto"
          >
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={isSubmitting || !feedbackType}
            className="w-full sm:w-auto bg-blue-600 hover:bg-blue-700 text-white"
          >
            {isSubmitting ? (
              <>
                <span className="inline-block animate-spin mr-2">⏳</span>
                Submitting...
              </>
            ) : (
              <>
                <Flag className="h-4 w-4 mr-2" />
                Submit Feedback
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default QuestionFeedbackDialog;

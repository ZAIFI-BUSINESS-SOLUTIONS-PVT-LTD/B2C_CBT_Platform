import { AlertTriangle } from "lucide-react";

interface SecurityBannerProps {
  enabled: boolean;
}

export default function SecurityBanner({ enabled }: SecurityBannerProps) {
  if (!enabled) return null;
  return (
    <div className="max-w-7xl mx-auto mb-2 sm:mb-4 px-2 sm:px-0">
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg sm:rounded-xl p-2 sm:p-3 flex items-center space-x-2 sm:space-x-3">
        <AlertTriangle className="h-4 w-4 sm:h-5 sm:w-5 text-yellow-600 flex-shrink-0" />
        <div className="text-xs sm:text-sm text-yellow-800">
          <span className="font-medium">Secure Test Mode:</span> Tab switching and window navigation are blocked during the test. Use "Quit Exam" to leave.
        </div>
      </div>
    </div>
  );
}

import { useEffect, useState } from 'react';
import { useLocation } from 'wouter';
import { Lock } from 'lucide-react';

interface SubscriptionRequiredModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  message?: string;
  autoRedirectSeconds?: number;
}

export default function SubscriptionRequiredModal({
  open,
  onOpenChange,
  message = 'Active subscription required to access this test.',
  autoRedirectSeconds = 5
}: SubscriptionRequiredModalProps) {
  const [, setLocation] = useLocation();
  const [countdown, setCountdown] = useState(autoRedirectSeconds);

  useEffect(() => {
    if (!open) {
      setCountdown(autoRedirectSeconds);
      return;
    }

    // Countdown timer
    const interval = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          setLocation('/payment');
          onOpenChange(false);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [open, autoRedirectSeconds, setLocation, onOpenChange]);

  const handleGoToPayment = () => {
    onOpenChange(false);
    setLocation('/payment');
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/40 backdrop-blur-sm"
        onClick={() => onOpenChange(false)}
      />
      
      {/* Modal */}
      <div className="relative bg-white rounded-2xl shadow-2xl max-w-sm w-full p-8 animate-in fade-in zoom-in duration-200">
        {/* Lock Icon */}
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-blue-100 mb-6">
          <Lock className="h-8 w-8 text-blue-600" strokeWidth={2} />
        </div>
        
        {/* Title */}
        <h2 className="text-2xl font-bold text-center text-gray-900 mb-3">
          Subscription Required
        </h2>
        
        {/* Description */}
        <p className="text-center text-gray-600 mb-6 leading-relaxed">
          {message}
        </p>

        {/* Countdown Info */}
        <div className="bg-blue-50 rounded-lg p-3 mb-6 text-center">
          <p className="text-sm text-blue-800">
            Auto-redirecting in <span className="font-bold text-lg">{countdown}s</span>
          </p>
        </div>
        
        {/* Action Button */}
        <button
          onClick={handleGoToPayment}
          className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3.5 px-6 rounded-xl transition-all duration-200 shadow-lg hover:shadow-xl active:scale-[0.98] mb-3"
        >
          Go to Payment Page
        </button>

        {/* Dismiss Button */}
        <button
          onClick={() => onOpenChange(false)}
          className="w-full text-gray-500 hover:text-gray-700 font-medium py-2 transition-colors"
        >
          Maybe Later
        </button>
      </div>
    </div>
  );
}

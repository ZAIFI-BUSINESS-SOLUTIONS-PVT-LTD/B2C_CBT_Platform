/**
 * Offline Indicator Banner Component
 * 
 * Displays a banner at the top of the page when the user is offline,
 * informing them that they're viewing cached data.
 * 
 * Usage:
 * ```tsx
 * import { OfflineIndicator } from '@/components/OfflineIndicator';
 * 
 * function App() {
 *   return (
 *     <>
 *       <OfflineIndicator />
 *       {/* rest of your app *\/}
 *     </>
 *   );
 * }
 * ```
 */

import { useOfflineDetection } from '@/hooks/use-offline';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { WifiOff, Wifi } from 'lucide-react';
import { useState, useEffect } from 'react';

export function OfflineIndicator() {
  const { isOffline, isOnline } = useOfflineDetection();
  const [showOnlineMessage, setShowOnlineMessage] = useState(false);
  const [wasOffline, setWasOffline] = useState(false);

  useEffect(() => {
    if (isOffline) {
      setWasOffline(true);
    } else if (wasOffline && isOnline) {
      // User just came back online - show success message briefly
      setShowOnlineMessage(true);
      const timer = setTimeout(() => {
        setShowOnlineMessage(false);
        setWasOffline(false);
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [isOffline, isOnline, wasOffline]);

  if (!isOffline && !showOnlineMessage) {
    return null;
  }

  if (showOnlineMessage) {
    return (
      <div className="fixed top-0 left-0 right-0 z-50 animate-in slide-in-from-top">
        <Alert className="rounded-none border-green-200 bg-green-50 text-green-800">
          <Wifi className="h-4 w-4" />
          <AlertDescription className="ml-2">
            <strong>Back online!</strong> Data is now being synchronized.
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="fixed top-0 left-0 right-0 z-50 animate-in slide-in-from-top">
      <Alert className="rounded-none border-orange-200 bg-orange-50 text-orange-800">
        <WifiOff className="h-4 w-4" />
        <AlertDescription className="ml-2">
          <strong>You're offline.</strong> Showing cached data. Some features may be unavailable.
        </AlertDescription>
      </Alert>
    </div>
  );
}

// Compact version for smaller UI areas
export function OfflineBadge() {
  const { isOffline } = useOfflineDetection();

  if (!isOffline) {
    return null;
  }

  return (
    <div className="inline-flex items-center gap-1.5 rounded-full bg-orange-100 px-2.5 py-1 text-xs font-medium text-orange-800">
      <WifiOff className="h-3 w-3" />
      <span>Offline</span>
    </div>
  );
}

// Hook variant for custom implementations
export { useOfflineDetection };

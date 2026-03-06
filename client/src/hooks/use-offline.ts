/**
 * PWA Offline Detection Hook
 * 
 * Detects and monitors online/offline status using the Network Information API
 * and navigator.onLine property.
 * 
 * Usage:
 * ```tsx
 * const { isOffline, isOnline } = useOfflineDetection();
 * 
 * if (isOffline) {
 *   return <OfflineBanner />;
 * }
 * ```
 */

import { useState, useEffect } from 'react';

export interface OfflineState {
  isOffline: boolean;
  isOnline: boolean;
}

export function useOfflineDetection(): OfflineState {
  const [isOffline, setIsOffline] = useState(!navigator.onLine);

  useEffect(() => {
    const handleOnline = () => {
      console.log("🌐 Network status: ONLINE");
      setIsOffline(false);
    };

    const handleOffline = () => {
      console.log("📴 Network status: OFFLINE");
      setIsOffline(true);
    };

    // Add event listeners
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    // Check initial state
    setIsOffline(!navigator.onLine);

    // Cleanup
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  return {
    isOffline,
    isOnline: !isOffline,
  };
}

// Re-export as default for convenience
export default useOfflineDetection;

/**
 * Trusted Web Activity (TWA) Utilities
 * 
 * Utilities to detect when the app is running inside a TWA (Android wrapper)
 * and provide platform-specific functionality.
 */

/**
 * Detects if the app is running inside a Trusted Web Activity (TWA)
 * 
 * TWA apps set document.referrer to "android-app://<package-name>"
 * 
 * @returns {boolean} true if running in TWA, false otherwise
 * 
 * @example
 * if (isTWA()) {
 *   // Use Android billing
 *   window.Android.purchase(productId);
 * } else {
 *   // Use web payment (Razorpay)
 *   initiateRazorpayCheckout();
 * }
 */
export const isTWA = (): boolean => {
  return document.referrer.includes("android-app://");
};

/**
 * Check if Android bridge is available
 * The Android bridge should be injected by the TWA native layer
 * 
 * @returns {boolean} true if Android bridge is available
 */
export const isAndroidBridgeAvailable = (): boolean => {
  return typeof (window as any).Android !== 'undefined';
};

/**
 * Get the TWA package name from document.referrer
 * 
 * @returns {string | null} Package name or null if not in TWA
 * 
 * @example
 * getTWAPackageName() // "com.neetbro"
 */
export const getTWAPackageName = (): string | null => {
  if (!isTWA()) return null;
  
  const match = document.referrer.match(/android-app:\/\/([^\/]+)/);
  return match ? match[1] : null;
};

/**
 * Register Play Billing purchase success callback
 * This is called by Android native code when a purchase completes
 * 
 * @param callback Function to handle purchase token and product ID
 */
export const registerPlayPurchaseCallback = (
  callback: (purchaseToken: string, productId: string) => void | Promise<void>
) => {
  (window as any).onPlayPurchaseSuccess = callback;
};

/**
 * Verify Play Store purchase with backend
 * 
 * @param purchaseToken Google Play purchase token
 * @param productId Product ID (e.g., "basic-3m", "pro-3m")
 * @param accessToken JWT access token for authentication
 * @returns Verification response from backend
 */
export const verifyPlayPurchase = async (
  purchaseToken: string,
  productId: string,
  accessToken: string
): Promise<any> => {
  console.log('[verifyPlayPurchase] Sending to backend:', {
    purchaseToken: purchaseToken.substring(0, 30) + '...',
    productId,
    authHeader: `Bearer ${accessToken.substring(0, 20)}...`
  });

  const response = await fetch("/api/payments/play/verify-subscription/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify({
      purchaseToken,
      productId,
    }),
  });

  if (!response.ok) {
    const error = await response.json();
    console.error('[verifyPlayPurchase] Backend returned error:', {
      status: response.status,
      statusText: response.statusText,
      errorBody: error
    });
    throw new Error(error.error || error.details || "Play purchase verification failed");
  }

  return response.json();
};

/**
 * Poll for purchase result from Android bridge
 * Used after initiating a purchase to check if it completed
 * 
 * @param onSuccess Callback when purchase succeeds
 * @param onError Callback when polling times out
 * @param timeout Maximum time to poll in milliseconds (default: 5 minutes)
 * @param interval Polling interval in milliseconds (default: 1 second)
 */
export const pollForPurchaseResult = (
  onSuccess: (purchaseToken: string, productId: string) => void,
  onError?: () => void,
  timeout: number = 300000, // 5 minutes
  interval: number = 1000 // 1 second
) => {
  if (!isAndroidBridgeAvailable()) {
    onError?.();
    return;
  }

  const startTime = Date.now();
  
  const checkPurchase = () => {
    try {
      // Check if there's a pending purchase
      if (window.Android?.hasPendingPurchase()) {
        const resultJson = window.Android?.getPurchaseResult();
        
        if (resultJson) {
          const result = JSON.parse(resultJson);
          if (result.purchaseToken && result.productId) {
            onSuccess(result.purchaseToken, result.productId);
            return; // Stop polling
          }
        }
      }
      
      // Continue polling if not timed out
      if (Date.now() - startTime < timeout) {
        setTimeout(checkPurchase, interval);
      } else {
        // Timeout
        onError?.();
      }
    } catch (error) {
      console.error('[TWA] Error polling for purchase result:', error);
      onError?.();
    }
  };
  
  // Start polling after a short delay
  setTimeout(checkPurchase, 500);
};

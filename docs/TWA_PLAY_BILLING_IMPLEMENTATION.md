# Google Play Billing Integration for TWA

## Overview
Added Google Play Billing support for the Trusted Web Activity (TWA) Android app while maintaining existing Razorpay payment flow for web users.

## Changes Made

### 1. Created TWA Detection Utility (`client/src/utils/twa.ts`)
- **`isTWA()`**: Detects if app is running in TWA by checking `document.referrer` for "android-app://"
- **`isAndroidBridgeAvailable()`**: Checks if Android bridge is available
- **`getTWAPackageName()`**: Extracts package name from referrer

### 2. Updated PaymentButtons Component (`client/src/components/PaymentButtons.tsx`)

#### Window Interface Extension
Added Android bridge interface:
```typescript
declare global {
  interface Window {
    Razorpay: any;
    Android?: {
      purchase: (productId: string) => void;
    };
  }
}
```

#### Updated `handlePayment()` Function
The payment handler now checks the platform:

**TWA Flow (Android App):**
- Detects TWA environment using `isTWA()`
- Calls `window.Android.purchase(plan)` to trigger Play Billing
- Shows error toast if Android bridge is unavailable

**Web Flow (Browser):**
- Uses existing Razorpay checkout flow
- No changes to Razorpay implementation
- All existing payment logic preserved

### 3. No Changes Required
- **SubscriptionRequiredModal**: Already redirects to `/payment`, works for both TWA and web
- **UI/Routing**: No changes to UI, navigation, or routing logic
- **Other Components**: No other files modified

## How It Works

### For Web Users
1. User clicks subscription button
2. `handlePayment()` detects web environment
3. Razorpay checkout opens as before
4. Payment verified through existing backend API
5. Subscription activated

### For TWA Users (Android App)
1. User clicks subscription button
2. `handlePayment()` detects TWA environment via `document.referrer`
3. Calls `window.Android.purchase(plan)` 
4. Android native layer handles Google Play Billing
5. Purchase token sent to backend for verification (Android-side implementation needed)
6. Subscription activated

## Testing

### Test TWA Detection
```javascript
// In browser console (web):
console.log(document.referrer); // Should NOT contain "android-app://"

// In TWA app:
console.log(document.referrer); // Should be "android-app://com.neetbro"
```

### Test Payment Flow
- **Web**: Should show Razorpay checkout as before
- **TWA**: Should call Android bridge (requires Android-side implementation)

## Android-Side Requirements

The TWA app must inject a JavaScript bridge with the following interface:

```java
@JavascriptInterface
public void purchase(String productId) {
    // Implement Google Play Billing flow
    // After successful purchase, verify on backend
}
```

## Product IDs
- `"basic"` - Basic subscription plan (₹1,500/year)
- `"pro"` - Pro subscription plan (₹2,500/year)

## Backend Integration Notes

The backend will need to:
1. Accept Google Play purchase tokens
2. Verify tokens with Google Play Developer API
3. Grant subscription based on verified purchase
4. Handle subscription renewals and cancellations

Existing Razorpay flow remains unchanged on the backend.

## Summary

✅ **Completed:**
- TWA detection utility created
- Payment handler updated with platform detection
- Android bridge interface defined
- Existing Razorpay flow preserved
- No UI/routing changes

⚠️ **Still Required (Android-side):**
- Implement JavaScript bridge in TWA
- Integrate Google Play Billing Library
- Implement purchase verification flow
- Add backend endpoint for Play purchase verification

## Files Modified
1. `client/src/utils/twa.ts` (new file)
2. `client/src/components/PaymentButtons.tsx` (modified)

## Files NOT Modified
- All routing logic
- All UI components
- SubscriptionRequiredModal
- API configuration
- Backend files

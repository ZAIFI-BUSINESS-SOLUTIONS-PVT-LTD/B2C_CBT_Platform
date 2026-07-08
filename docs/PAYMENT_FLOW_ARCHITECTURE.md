# Payment Flow Architecture

## Decision Flow

```
User clicks "Subscribe to Basic/Pro"
           |
           v
    handlePayment(plan)
           |
           v
     Is TWA Environment?
     (document.referrer contains "android-app://")
           |
    +------+------+
    |             |
   YES           NO
    |             |
    v             v
Android Flow    Web Flow
    |             |
    v             v
window.Android   Razorpay
.purchase(plan)  Checkout
    |             |
    v             v
Google Play      Razorpay
Billing          Payment
    |             |
    v             v
Android verifies Web verifies
with backend     with backend
    |             |
    +------+------+
           |
           v
   Subscription Activated
           |
           v
    Reload Status
```

## Component Architecture

```
┌─────────────────────────────────────────────┐
│         SubscriptionRequiredModal           │
│  (Redirects to /payment for both platforms) │
└─────────────┬───────────────────────────────┘
              |
              v
┌─────────────────────────────────────────────┐
│           PaymentButtons Component           │
│  ┌─────────────────────────────────────┐   │
│  │     Import isTWA() utility          │   │
│  └─────────────────────────────────────┘   │
│  ┌─────────────────────────────────────┐   │
│  │    handlePayment(plan) function     │   │
│  │  ┌──────────────────────────────┐  │   │
│  │  │   if (isTWA())               │  │   │
│  │  │     → Android.purchase()     │  │   │
│  │  │   else                       │  │   │
│  │  │     → Razorpay checkout      │  │   │
│  │  └──────────────────────────────┘  │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  ┌─────────────┐  ┌─────────────────┐     │
│  │  Basic Plan │  │    Pro Plan     │     │
│  │  Button     │  │    Button       │     │
│  └─────────────┘  └─────────────────┘     │
└─────────────────────────────────────────────┘
```

## Platform Detection Logic

```typescript
// utils/twa.ts
export const isTWA = (): boolean => {
  return document.referrer.includes("android-app://");
};

// Web Browser:
// document.referrer = "https://neetbro.com/" or ""
// isTWA() returns false

// TWA Android App:
// document.referrer = "android-app://com.neetbro"
// isTWA() returns true
```

## Payment Handler Logic

```typescript
const handlePayment = async (plan: 'basic' | 'pro') => {
  setLoading(plan);
  
  try {
    // 🔍 Platform Detection
    if (isTWA()) {
      // 📱 Android TWA Path
      if (window.Android?.purchase) {
        console.log(`[TWA] Android billing: ${plan}`);
        window.Android.purchase(plan);
        return; // Exit early - Android handles the rest
      } else {
        // Show error - bridge not available
        toast({ error: "Update app for billing" });
        return;
      }
    }
    
    // 🌐 Web Browser Path (Existing Razorpay Flow)
    const isRazorpayLoaded = await loadRazorpayScript();
    if (!isRazorpayLoaded) {
      toast({ error: "Failed to load payment gateway" });
      return;
    }
    
    const orderData = await createOrder(plan);
    const rzp = new window.Razorpay({
      key: orderData.key,
      amount: orderData.amount,
      // ... rest of Razorpay config
    });
    rzp.open();
    
  } catch (error) {
    toast({ error: "Failed to initiate payment" });
  } finally {
    setLoading(null);
  }
};
```

## Integration Points

### Frontend (Completed ✅)
- TWA detection utility
- Payment handler with platform switching
- Android bridge type definitions
- No changes to UI/UX

### Android Native (Pending ⚠️)
Required in TWA app:

```java
// MainActivity.java or similar
webView.addJavascriptInterface(new BillingBridge(), "Android");

class BillingBridge {
    @JavascriptInterface
    public void purchase(String productId) {
        // 1. Trigger Play Billing flow
        // 2. On success, get purchase token
        // 3. Send to backend for verification
        // 4. Activate subscription
    }
}
```

### Backend (Pending ⚠️)
New endpoint needed:

```
POST /api/verify-play-purchase/
{
  "productId": "basic",
  "purchaseToken": "...",
  "packageName": "com.neetbro"
}

→ Verify with Google Play Developer API
→ Grant subscription if valid
```

## Testing Strategy

### Development Testing
```javascript
// Force TWA mode in browser DevTools
Object.defineProperty(document, 'referrer', {
  get: () => 'android-app://com.neetbro'
});

// Mock Android bridge
window.Android = {
  purchase: (productId) => {
    console.log(`Mock purchase: ${productId}`);
  }
};
```

### Production Testing
1. **Web**: Test on neetbro.com (should use Razorpay)
2. **TWA**: Test in Android app (should call Android bridge)
3. **Edge cases**: Test with missing Android bridge

## Security Considerations

1. **TWA Origin Verification**: Document.referrer can only be "android-app://" if legitimately from TWA
2. **Backend Verification**: Always verify purchases server-side with Google Play API
3. **Fallback Handling**: Graceful error if Android bridge missing
4. **No Sensitive Data**: Product IDs only, no prices sent to Android

## Rollout Plan

**Phase 1: Frontend (Completed ✅)**
- TWA detection
- Payment routing logic
- Type definitions

**Phase 2: Android Development (Next)**
- Implement JavaScript bridge
- Integrate Google Play Billing Library
- Handle purchase flow

**Phase 3: Backend Integration (Next)**
- Create Play purchase verification endpoint
- Integrate with Google Play Developer API
- Update subscription activation logic

**Phase 4: Testing (Next)**
- End-to-end testing in TWA
- Verify web flow still works
- Test edge cases

**Phase 5: Deployment**
- Release updated TWA to Play Store
- Monitor both payment flows
- Track conversion rates

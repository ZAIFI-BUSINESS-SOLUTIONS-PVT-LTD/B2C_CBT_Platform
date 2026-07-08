# Google Play Billing Integration - Setup Guide

## Overview
This guide explains how to set up Google Play Billing for subscription verification in the NEET Ninja backend.

## Implementation Summary

### What Was Changed

1. **Payment Model Extended**
   - `RazorpayOrder` → `PaymentOrder` with `provider` field
   - Supports both `razorpay` and `play` providers
   - Added Play-specific fields: `play_purchase_token`, `play_product_id`, `play_order_id`
   - All Razorpay fields remain intact (backward compatible)
   - Migration: `0031_paymentorder_delete_razorpayorder_and_more`

2. **New Service Created**
   - File: `backend/neet_app/services/play_billing_service.py`
   - Verifies Google Play subscription purchases
   - Uses Google Play Developer API v3

3. **New Endpoint Added**
   - `POST /api/payments/play/verify-subscription/`
   - Verifies purchase token with Google
   - Activates subscription (30 days)
   - Stores payment record in unified table

4. **Admin Panel Updated**
   - `PaymentOrder` admin shows both Razorpay and Play orders
   - Collapsible sections for provider-specific fields
   - Smart payment ID display based on provider

## Setup Instructions

### Step 1: Install Dependencies

```bash
cd backend
pip install google-api-python-client google-auth
```

### Step 2: Create Google Play Service Account

1. Go to [Google Play Console](https://play.google.com/console)
2. Select your app (com.neetbro)
3. Navigate to **Setup → API access**
4. Click **Create new service account**
5. Click **Google Cloud Console** link
6. In Google Cloud Console:
   - Click **Create Service Account**
   - Name: `play-billing-verifier`
   - Click **Create and Continue**
   - Grant role: **Service Account User**
   - Click **Done**
7. Click on the service account email
8. Go to **Keys** tab
9. Click **Add Key → Create new key**
10. Choose **JSON** format
11. Download the JSON file

### Step 3: Configure Service Account Permissions

Back in Google Play Console:
1. Go to **Setup → API access**
2. Find your service account in the list
3. Click **Grant Access**
4. Under **App permissions**, select your app
5. Under **Account permissions**, enable:
   - **View app information and download bulk reports**
   - **View financial data, orders, and cancellation survey responses**
   - **Manage orders and subscriptions**
6. Click **Invite user** → **Send invite**

### Step 4: Configure Backend

#### Option A: Environment Variable (Recommended for Production)

```bash
# Add to .env file
PLAY_SERVICE_ACCOUNT_JSON=/path/to/your/play-service-account.json
PLAY_PACKAGE_NAME=com.neetbro
```

#### Option B: Place File in Backend Directory (Development)

```bash
# Copy the JSON file to backend directory
cp ~/Downloads/play-service-account-xxxxx.json backend/play-service-account.json

# Update .env (optional - defaults to backend/play-service-account.json)
PLAY_PACKAGE_NAME=com.neetbro
```

### Step 5: Test the Integration

#### Test with cURL:

```bash
# Get auth token first
TOKEN="your_jwt_token_here"

# Verify Play subscription
curl -X POST http://localhost:8000/api/payments/play/verify-subscription/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "purchaseToken": "test_purchase_token_from_android",
    "productId": "basic"
  }'
```

#### Expected Response (Success):

```json
{
  "status": "verified",
  "provider": "play",
  "plan": "basic",
  "expires_at": "2024-03-15T12:00:00Z",
  "message": "Successfully subscribed to basic plan via Google Play"
}
```

#### Expected Response (Already Processed):

```json
{
  "status": "already_verified",
  "provider": "play",
  "plan": "basic",
  "message": "This purchase has already been processed"
}
```

#### Expected Response (Invalid):

```json
{
  "error": "Purchase verification failed",
  "details": "Purchase not found or invalid token"
}
```

## API Endpoints

### Verify Play Subscription

**Endpoint:** `POST /api/payments/play/verify-subscription/`

**Headers:**
```
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json
```

**Request Body:**
```json
{
  "purchaseToken": "string (required)",
  "productId": "basic" | "pro" (required)
}
```

**Response (200 OK):**
```json
{
  "status": "verified",
  "provider": "play",
  "plan": "basic",
  "expires_at": "2024-03-15T12:00:00Z",
  "message": "Successfully subscribed to basic plan via Google Play"
}
```

**Error Responses:**
- `400` - Invalid request (missing fields, invalid productId, verification failed)
- `401` - Unauthorized (invalid/missing JWT token)
- `500` - Internal server error

## Database Schema

### PaymentOrder Model

| Field | Type | Description |
|-------|------|-------------|
| `id` | BigAutoField | Primary key |
| `student` | ForeignKey | Student who made purchase |
| `provider` | CharField | 'razorpay' or 'play' |
| `plan` | CharField | 'basic' or 'pro' |
| `amount` | Integer | Amount in rupees |
| `currency` | CharField | 'INR' |
| `status` | CharField | Order status |
| `razorpay_order_id` | CharField | Razorpay order ID (nullable) |
| `razorpay_payment_id` | CharField | Razorpay payment ID (nullable) |
| `razorpay_signature` | CharField | Razorpay signature (nullable) |
| `play_purchase_token` | TextField | Google Play purchase token (nullable) |
| `play_product_id` | CharField | Google Play product ID (nullable) |
| `play_order_id` | CharField | Google Play order ID (nullable) |
| `created_at` | DateTimeField | Order creation time |
| `updated_at` | DateTimeField | Last update time |

## Frontend Integration

The frontend already has TWA detection and calls the Android bridge:

```typescript
// In PaymentButtons.tsx
if (isTWA()) {
  window.Android.purchase(plan);
} else {
  // Razorpay checkout
}
```

### Android-Side Implementation Needed

The TWA app must:

1. Inject JavaScript bridge:
```java
webView.addJavascriptInterface(new BillingBridge(), "Android");
```

2. Implement purchase method:
```java
@JavascriptInterface
public void purchase(String productId) {
    // 1. Initiate Play Billing flow
    // 2. On successful purchase, get purchaseToken
    // 3. Call backend API:
    //    POST /api/payments/play/verify-subscription/
    //    Body: { purchaseToken, productId }
    // 4. On backend success, reload subscription status
}
```

## Testing Checklist

- [ ] Service account JSON file configured
- [ ] Environment variables set (PLAY_SERVICE_ACCOUNT_JSON, PLAY_PACKAGE_NAME)
- [ ] Backend server restarted
- [ ] API endpoint accessible: `/api/payments/play/verify-subscription/`
- [ ] Test with valid purchase token from Play Console
- [ ] Verify subscription activated in database
- [ ] Check Django admin shows Play orders
- [ ] Confirm Razorpay flow still works (existing subscriptions)

## Troubleshooting

### Error: "Play billing service not initialized"

**Cause:** Service account JSON file not found or invalid path

**Solution:**
```bash
# Check file exists
ls -la backend/play-service-account.json

# Or check environment variable
echo $PLAY_SERVICE_ACCOUNT_JSON

# Set correct path
export PLAY_SERVICE_ACCOUNT_JSON=/full/path/to/play-service-account.json
```

### Error: "Authentication failed. Check service account credentials."

**Cause:** Service account doesn't have proper permissions

**Solution:**
1. Go to Google Play Console → API access
2. Find service account
3. Grant access with proper permissions (see Step 3 above)
4. Wait 5-10 minutes for permissions to propagate

### Error: "Purchase not found or invalid token"

**Cause:** Invalid purchase token or purchase doesn't exist

**Solution:**
- Verify purchase token is correct
- Ensure purchase was made for the correct package (com.neetbro)
- Check if purchase is in test mode (use test accounts)

### Error: "Access denied. Check API permissions."

**Cause:** API not enabled in Google Cloud Console

**Solution:**
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Select your project
3. Navigate to **APIs & Services → Library**
4. Search for "Google Play Android Developer API"
5. Click **Enable**

## Security Notes

1. **Never commit service account JSON to git**
   ```bash
   # Add to .gitignore
   echo "play-service-account.json" >> backend/.gitignore
   ```

2. **Use environment variables in production**
   ```bash
   # Production .env
   PLAY_SERVICE_ACCOUNT_JSON=/secure/path/play-service-account.json
   ```

3. **Rotate service account keys periodically**
   - Create new key in Google Cloud Console
   - Update backend configuration
   - Delete old key

4. **Monitor API usage**
   - Check Google Cloud Console for quota usage
   - Set up alerts for unusual activity

## Support

For issues or questions:
- Check Django logs: `backend/logs/`
- Check Google Play Console for purchase status
- Verify service account permissions
- Test with Play Console test accounts first

## Next Steps

1. **Android TWA Implementation:**
   - Implement JavaScript bridge
   - Integrate Play Billing Library
   - Handle purchase flow
   - Call backend verification endpoint

2. **Testing:**
   - Set up test accounts in Play Console
   - Test with test purchase tokens
   - Verify end-to-end flow

3. **Production Deployment:**
   - Upload TWA to Play Store (internal testing first)
   - Configure production service account
   - Monitor subscriptions in Django admin
   - Track conversion rates

## References

- [Google Play Billing Library](https://developer.android.com/google/play/billing)
- [Google Play Developer API](https://developers.google.com/android-publisher)
- [TWA Documentation](https://developer.chrome.com/docs/android/trusted-web-activity/)

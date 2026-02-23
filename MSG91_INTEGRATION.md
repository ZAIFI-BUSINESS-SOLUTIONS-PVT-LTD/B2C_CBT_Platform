# MSG91 SMS Integration for OTP Authentication

This document explains the MSG91 integration for sending OTP SMS messages, which replaces the previous AWS SNS implementation.

## Overview

The OTP authentication system now uses **MSG91** for SMS delivery instead of AWS SNS. MSG91 is a popular SMS service provider in India with better pricing and reliability for Indian mobile numbers.

## What Changed

### Files Modified

1. **`backend/neet_app/utils/sms.py`**
   - Removed AWS SNS (boto3) dependencies
   - Added MSG91 API integration using Python's built-in `http.client`
   - Kept the same function signatures so no other code needs to change
   
2. **`backend/neet_backend/settings.py`**
   - Added MSG91 configuration variables
   - Removed AWS configuration (kept for reference but not used)

3. **`requirements.txt`**
   - Commented out `boto3` and `botocore` dependencies
   - No new dependencies needed (uses built-in `http.client`)

### Key Functions

- **`send_otp_sms(mobile_number, otp)`** - Main function called by OTP views
- **`send_sms_via_msg91(mobile_number, otp, max_retries=3)`** - Handles MSG91 API calls
- **`normalize_mobile_for_msg91(mobile_number)`** - Converts E.164 format to MSG91 format

## Configuration

### Environment Variables

Add these to your `.env` file:

```bash
# MSG91 Configuration
MSG91_AUTH_KEY=470822AZqEX38U6999f1c6P1
MSG91_TEMPLATE_ID=6999eead965c7eb3fa0f75e3
MSG91_OTP_EXPIRY=5
APP_NAME=NeetNinja
```

### Getting MSG91 Credentials

1. Sign up at [MSG91 Dashboard](https://control.msg91.com/)
2. Get your **Auth Key** from Settings > API Keys
3. Create an OTP template and get the **Template ID**
4. Configure your template with OTP variables

### Template Setup

Your MSG91 OTP template should include:
- OTP code variable: `##OTP##` or similar
- App name reference
- Validity duration
- DND-compliant format for India

## How It Works

### Flow

1. User enters phone number in frontend
2. Frontend calls `/auth/send-otp/` with phone number
3. Backend:
   - Normalizes phone number (E.164 → MSG91 format)
   - Generates 6-digit OTP
   - Stores OTP hash in Redis (5-minute TTL)
   - Calls MSG91 API with OTP
4. MSG91 sends SMS using configured template
5. User enters OTP from SMS
6. Frontend calls `/auth/verify-otp/`
7. Backend verifies OTP and creates JWT session

### Phone Number Format

- **Input (E.164)**: `+919876543210`
- **MSG91 Format**: `919876543210` (no + prefix)
- Conversion handled automatically by `normalize_mobile_for_msg91()`

### MSG91 API Request

```python
POST https://control.msg91.com/api/v5/otp
Query Parameters:
  - mobile: 919876543210
  - authkey: {MSG91_AUTH_KEY}
  - otp: 123456
  - otp_expiry: 5
  - template_id: {MSG91_TEMPLATE_ID}
  - realTimeResponse: 1
```

### Response Format

Success:
```json
{
  "type": "success",
  "request_id": "abc123xyz789"
}
```

Error:
```json
{
  "type": "error",
  "message": "Invalid authentication key"
}
```

## Error Handling

The implementation includes:
- **Retry logic**: Up to 3 attempts with exponential backoff
- **Timeout**: 10-second connection timeout
- **Rate limit detection**: Retries on rate limit errors
- **Credential validation**: Checks if MSG91 credentials are configured
- **Response parsing**: Handles malformed JSON responses

## Testing

### Manual Testing

1. Set MSG91 credentials in `.env`
2. Start backend server
3. Make OTP request:

```bash
curl -X POST http://localhost:8000/auth/send-otp/ \
  -H "Content-Type: application/json" \
  -d '{"mobile_number": "+919876543210"}'
```

4. Check logs for MSG91 response
5. Verify SMS received on phone

### Unit Tests

Run existing OTP tests (they mock the SMS layer):

```bash
cd backend
python -m pytest neet_app/tests/test_mobile_otp.py -v
```

## Monitoring

Check logs for:
- `"OTP sent successfully to ... via MSG91"` - Success
- `"MSG91 Error"` - API errors
- `"Failed to send SMS to ..."` - Complete failures

## Production Checklist

- [ ] Add real MSG91 credentials to production `.env`
- [ ] Test SMS delivery to multiple Indian carriers
- [ ] Verify template is DND-compliant
- [ ] Set up MSG91 webhook for delivery reports (optional)
- [ ] Monitor SMS credits in MSG91 dashboard
- [ ] Set up alerts for low credit balance

## Rollback

If you need to switch back to AWS SNS:

1. Uncomment `boto3` and `botocore` in `requirements.txt`
2. Restore `backend/neet_app/utils/sms.py` from git history
3. Add AWS credentials to settings
4. Run `pip install -r requirements.txt`

## Cost Comparison

| Provider | Cost per SMS (India) | Notes |
|----------|---------------------|-------|
| AWS SNS  | ~₹0.60-1.00        | Higher cost, global coverage |
| MSG91    | ~₹0.10-0.30        | Lower cost, India-focused |

## Support

For MSG91 issues:
- Documentation: https://docs.msg91.com/
- Support: https://control.msg91.com/support/
- Status: https://status.msg91.com/

For code issues:
- Check logs in `backend/logs/`
- Review `neet_app/tests/test_mobile_otp.py`
- Contact backend team

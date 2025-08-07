# API Key Configuration Guide for NEET Ninja Chatbot

This guide explains how to configure multiple Gemini API keys for automatic rotation to avoid rate limits.

## Where to Add Your 10 API Keys

### Method 1: Environment Variables (Recommended)

Create or update your `.env` file in the project root with your 10 API keys:

```env
# Gemini API Keys for rotation (add all 10 keys)
GEMINI_API_KEY_1=your_first_api_key_here
GEMINI_API_KEY_2=your_second_api_key_here
GEMINI_API_KEY_3=your_third_api_key_here
GEMINI_API_KEY_4=your_fourth_api_key_here
GEMINI_API_KEY_5=your_fifth_api_key_here
GEMINI_API_KEY_6=your_sixth_api_key_here
GEMINI_API_KEY_7=your_seventh_api_key_here
GEMINI_API_KEY_8=your_eighth_api_key_here
GEMINI_API_KEY_9=your_ninth_api_key_here
GEMINI_API_KEY_10=your_tenth_api_key_here

# Fallback single key (optional)
GEMINI_API_KEY=your_primary_api_key_here
```

### Method 2: Direct in Settings (Not Recommended for Production)

If you prefer to add keys directly in settings.py:

```python
# In backend/neet_backend/settings.py
GEMINI_API_KEYS = [
    'your_first_api_key_here',
    'your_second_api_key_here',
    'your_third_api_key_here',
    'your_fourth_api_key_here',
    'your_fifth_api_key_here',
    'your_sixth_api_key_here',
    'your_seventh_api_key_here',
    'your_eighth_api_key_here',
    'your_ninth_api_key_here',
    'your_tenth_api_key_here',
]
```

## How the API Key Rotation Works

1. **Automatic Rotation**: When a rate limit is hit, the system automatically switches to the next API key
2. **Round-Robin**: Keys are used in a round-robin fashion (1 → 2 → 3 → ... → 10 → 1)
3. **Rate Limiting**: Built-in delays between requests to prevent hitting limits
4. **Error Handling**: Handles various error types (rate limits, authentication, quotas)

## Testing Your API Keys

### 1. Check API Key Status
```bash
GET /api/test/api-keys/status/
```

### 2. Test All Keys
```bash
GET /api/test/api-keys/
```

### 3. Test Rotation
```bash
POST /api/test/api-keys/rotation/
```

## Rate Limit Management

- **Default Delay**: 1 second between requests
- **Rotation Trigger**: Automatic on rate limit errors (429, quota exceeded)
- **Retry Logic**: Up to 3 retries with different keys
- **Fallback**: Graceful degradation when all keys are rate-limited

## Error Types Handled

1. **Rate Limits**: `429`, `quota exceeded`, `resource exhausted`
2. **Authentication**: `401`, `403`, `invalid api key`
3. **General Errors**: Network issues, temporary failures

## Best Practices

1. **Use Environment Variables**: Keep API keys secure and out of version control
2. **Monitor Usage**: Check API key status regularly
3. **Distribute Load**: Use all 10 keys to maximize request capacity
4. **Test Regularly**: Use the test endpoints to verify key functionality

## Configuration Verification

After adding your keys, verify the configuration:

1. Start the Django server
2. Check the console output for key count: `"GeminiClient initialized with X API keys"`
3. Use the test endpoints to verify functionality
4. Monitor logs for rotation events

## Troubleshooting

### No API Keys Found
```
Warning: No Gemini API keys found!
Add your API keys to settings.py as GEMINI_API_KEYS list or
set environment variables GEMINI_API_KEY_1, GEMINI_API_KEY_2, etc.
```
**Solution**: Add keys using Method 1 or 2 above.

### Keys Not Rotating
- Check that multiple keys are configured
- Verify keys are valid using the test endpoint
- Monitor logs for rotation messages

### Rate Limits Still Hit
- Ensure all 10 keys are different and valid
- Check if keys have different quota limits
- Consider adding delays between operations

## Security Notes

- **Never commit API keys to version control**
- **Use environment variables in production**
- **Regularly rotate your API keys**
- **Monitor API key usage through Google Cloud Console**

## Example Usage in Code

The rotation is handled automatically, but you can check status:

```python
from neet_app.services.chatbot_service import NeetChatbotService

chatbot = NeetChatbotService()

# Check status
status = chatbot.gemini_client.get_api_key_status()
print(f"Using key {status['current_key_index'] + 1} of {status['total_keys']}")

# Generate response (rotation happens automatically if needed)
response = chatbot.generate_response("How should I study for NEET?", student_id, session_id)
```

## Support

If you encounter issues:
1. Check the console logs for error messages
2. Use the test endpoints to diagnose problems
3. Verify your API keys in Google Cloud Console
4. Check the rate limits and quotas for your keys

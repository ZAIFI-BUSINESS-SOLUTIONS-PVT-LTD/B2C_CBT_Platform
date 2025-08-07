# Chatbot Frontend-Backend Connection Troubleshooting Guide

## The Issue
Frontend is getting 404 errors when trying to access chatbot endpoints, and receiving HTML instead of JSON responses.

## Root Cause Analysis
The error `"Unexpected token '<', "<!DOCTYPE "... is not valid JSON"` indicates that:
1. The frontend is receiving an HTML page instead of JSON API response
2. This usually means the request is not reaching the Django backend properly
3. The 404 error suggests the endpoint doesn't exist or routing is incorrect

## Fixed Issues ✅

### 1. API Configuration
- ✅ Added chatbot endpoints to `client/src/config/api.ts`
- ✅ Updated frontend to use `API_CONFIG.BASE_URL` and proper endpoints
- ✅ Fixed all API calls to use full URLs instead of relative paths

### 2. Frontend API Calls
- ✅ Fixed `loadChatSessions()` to use correct URL
- ✅ Fixed `loadSessionMessages()` to use correct URL  
- ✅ Fixed `createNewSession()` to use correct URL
- ✅ Fixed `sendMessage()` to use correct URL
- ✅ Added debug logging to identify issues

### 3. Backend Endpoints
- ✅ Verified `ChatSessionViewSet` exists and is properly registered
- ✅ Confirmed all required actions exist: `list`, `create`, `send_message`, `get_messages`

## Steps to Test the Fix

### 1. Verify Backend is Running
```bash
cd backend
python manage.py runserver 8000
```

### 2. Test Backend Connectivity
```bash
cd backend
python test_backend_connectivity.py
```

### 3. Check Frontend Configuration
Open browser dev tools and look for console logs:
- 🔑 Auth token: Present/Missing
- 🌐 API Base URL: http://localhost:8000
- 📡 Loading chat sessions from: http://localhost:8000/api/chat-sessions/

### 4. Test API Endpoints Manually
```bash
# Test if backend is accessible
curl http://localhost:8000/api/

# Test chat sessions endpoint (should return 401 Unauthorized)
curl http://localhost:8000/api/chat-sessions/
```

## Expected Behavior After Fix

### Frontend Console Output:
```
🔑 Auth token: Present
🌐 API Base URL: http://localhost:8000
📡 Loading chat sessions from: http://localhost:8000/api/chat-sessions/
📨 Response status: 200
📊 Chat sessions data: {results: [...]}
```

### Successful Flow:
1. User clicks "Start Conversation"
2. Frontend calls `http://localhost:8000/api/chat-sessions/` with auth token
3. Backend creates new chat session
4. Frontend receives JSON response with session data
5. Welcome message loads automatically

## Common Issues to Check

### 1. Backend Not Running
**Symptoms:** Connection refused errors
**Solution:** Start Django with `python manage.py runserver 8000`

### 2. Wrong Port
**Symptoms:** 404 errors, HTML responses
**Solution:** Ensure backend is on port 8000, frontend on 5173

### 3. Authentication Issues
**Symptoms:** 401 Unauthorized
**Solution:** Check that user is logged in and token is valid

### 4. CORS Issues
**Symptoms:** CORS policy errors in browser
**Solution:** Already fixed - CORS_ALLOW_ALL_ORIGINS = True

### 5. URL Mismatch
**Symptoms:** 404 on specific endpoints
**Solution:** Check that endpoint URLs match between frontend and backend

## Debug Commands

### Check if Django is running:
```bash
netstat -an | grep 8000
```

### Check if frontend can reach backend:
```bash
curl -H "Accept: application/json" http://localhost:8000/api/chat-sessions/
```

### Check Django URL routing:
```bash
cd backend
python manage.py show_urls | grep chat
```

## Next Steps if Still Failing

1. **Check Authentication**: Ensure user is logged in and JWT token is valid
2. **Verify Database**: Ensure PostgreSQL is running and migrations are applied
3. **Check Logs**: Look at Django console for any error messages
4. **Test Without Auth**: Try accessing public endpoints first
5. **Browser Network Tab**: Check actual HTTP requests being made

## Files Modified
- ✅ `client/src/config/api.ts` - Added chatbot endpoints
- ✅ `client/src/pages/chatbot.tsx` - Fixed API calls and added debugging
- ✅ `backend/test_backend_connectivity.py` - Created connectivity test

The chatbot should now work properly with these fixes! 🚀

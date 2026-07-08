# TTS Audio Dictation for Demo Tests - Implementation Summary

## Overview

Successfully implemented server-side TTS audio dictation for demo tests from Neet Bro Institute. When students complete a demo test, the system now:

1. Generates checkpoint insights (existing flow)
2. Generates MP3 audio from the first checkpoint of each subject
3. Plays audio with animated penguin overlay after loading video ends
4. Redirects to dashboard when audio completes

## Architecture

### Backend (Django)
- **TTS Helper**: `backend/neet_app/utils/tts_helper.py`
  - `is_demo_test_for_neet_bro()` - Detects demo tests
  - `extract_checkpoint_text_for_audio()` - Formats checkpoint text
  - `generate_insight_audio()` - Calls Node TTS service

- **Zone Insights API**: Modified `backend/neet_app/views/zone_insights_views.py`
  - `/api/zone-insights/status/<test_id>/` now returns `audio_url` for demo tests
  - Extracts first checkpoint from each subject
  - Generates audio: "Hi, you have completed your first test successfully. Here are the feedback of your performance from our end. For Physics: [checkpoint]. For Chemistry: [checkpoint]..."

### TTS Microservice (Node.js)
- **Location**: `tts-service/`
- **Stack**: Express + edge-tts (Microsoft Edge TTS)
- **Voice**: `en-IN-NeerjaNeural` (Indian English Female)
- **Endpoints**:
  - `POST /api/generate-insight-audio` - Generate MP3 from text
  - `GET /audio/:filename.mp3` - Serve generated audio
  - `GET /health` - Health check

### Frontend (React)
- **TTS Helper**: `client/src/utils/tts.ts`
  - `unlockAudio()` - Unlock audio during user gesture
  - `playAudioWithElement()` - Play audio with unlocked element

- **Penguin Overlay**: `client/src/components/PenguinOverlay.tsx`
  - Animated penguin SVG with sound waves
  - Blur backdrop effect
  - Audio indicator animation

- **Loading Results**: `client/src/pages/LoadingResultsPage.tsx`
  - Unlocks audio on mount (user gesture from test submit)
  - Polls for insights + audio URL
  - Waits for loading video to end
  - Plays audio with penguin overlay
  - Redirects when audio completes

## Flow Diagram

```
Student completes test (demo test from Neet Bro Institute)
    ↓
Test submission → Backend generates metrics
    ↓
Loading video plays (frontend)
    ↓
Backend generates checkpoint insights (async)
    ↓
Backend detects demo test → generates TTS audio
    ↓
Frontend polls /api/zone-insights/status/ → receives audio_url
    ↓
Video ends → frontend plays audio with penguin overlay
    ↓
Audio completes → redirect to dashboard
```

## Files Created/Modified

### Created
1. `tts-service/` - Node microservice
   - `package.json` - Dependencies
   - `index.js` - Express API server
   - `services/tts.js` - TTS generation logic
   - `scripts/cleanup-audio.js` - Cleanup old files
   - `public/audio/` - Generated MP3 storage
   - `README.md` - Service documentation

2. `backend/neet_app/utils/tts_helper.py` - TTS helper functions

3. `client/src/utils/tts.ts` - Frontend TTS helper

4. `client/src/components/PenguinOverlay.tsx` - Penguin overlay component

5. `TTS_IMPLEMENTATION.md` - This file

### Modified
1. `backend/neet_app/views/zone_insights_views.py`
   - Added audio URL generation to `get_zone_insights_status()`

2. `backend/neet_backend/settings.py`
   - Added `TTS_SERVICE_URL` configuration

3. `client/src/pages/LoadingResultsPage.tsx`
   - Added audio unlock, playback, and penguin overlay logic

4. `client/src/components/LoadingVideo.tsx`
   - Added `onVideoEnd` callback prop

## Setup & Deployment

### Local Development

#### 1. Start TTS Service

```bash
cd tts-service
npm install
npm start
```

Service runs on `http://localhost:3001`

#### 2. Configure Django

Add to `.env`:
```bash
TTS_SERVICE_URL=http://localhost:3001
```

#### 3. Start Django Backend

```bash
cd backend
python manage.py runserver
```

#### 4. Start React Frontend

```bash
cd client
npm run dev
```

### Production Deployment

#### Option A: Same Server (Reverse Proxy)

**Nginx Configuration:**

```nginx
# TTS Service
upstream tts_service {
    server localhost:3001;
}

# Proxy TTS API
location /api/generate-insight-audio {
    proxy_pass http://tts_service/api/generate-insight-audio;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_connect_timeout 10s;
    proxy_read_timeout 10s;
}

# Serve audio files with caching
location /audio/ {
    proxy_pass http://tts_service/audio/;
    proxy_cache public_cache;
    proxy_cache_valid 200 1h;
    add_header Cache-Control "public, max-age=3600";
    add_header Access-Control-Allow-Origin "*";
}
```

**Environment Variables:**

```bash
# Django .env
TTS_SERVICE_URL=http://localhost:3001

# TTS Service .env
PORT=3001
NODE_ENV=production
MAX_AGE_HOURS=24
```

#### Option B: Separate Server

**TTS Service Server:**
```bash
# Deploy to separate server (e.g., tts.inzighted.com)
cd tts-service
npm install --production
pm2 start index.js --name tts-service
pm2 save
```

**Django Configuration:**
```bash
# .env
TTS_SERVICE_URL=https://tts.inzighted.com
```

**CORS**: Enable in `tts-service/index.js`:
```javascript
app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', 'https://neet.inzighted.com');
  res.header('Access-Control-Allow-Methods', 'GET, POST');
  next();
});
```

### Audio File Cleanup

**Automated Cleanup (Cron):**

```bash
# Run daily at 3 AM
crontab -e

# Add:
0 3 * * * cd /path/to/tts-service && node scripts/cleanup-audio.js
```

**Manual Cleanup:**

```bash
cd tts-service
npm run cleanup
```

## Testing

### Test TTS Service

```bash
# Health check
curl http://localhost:3001/health

# Generate audio
curl -X POST http://localhost:3001/api/generate-insight-audio \
  -H "Content-Type: application/json" \
  -d '{"text": "Hi, you have completed your first test successfully", "testId": "123"}'

# Response:
# {"audioUrl": "/audio/insight-123-1234567890.mp3"}

# Download audio
curl http://localhost:3001/audio/insight-123-1234567890.mp3 -o test.mp3
```

### Test End-to-End

1. Create a demo test in Neet Bro Institute
2. Complete the test as a student
3. Verify:
   - Loading video plays
   - Checkpoint insights generate
   - Audio URL appears in `/api/zone-insights/status/<id>/` response
   - Penguin overlay shows after video
   - Audio plays automatically
   - Dashboard redirect after audio ends

### Test Matrix

- ✅ Chrome Android (installed PWA)
- ✅ Safari iOS (installed PWA)
- ✅ Chrome Desktop
- ✅ TWA (Trusted Web Activity)

## Security

### Rate Limiting

TTS service applies 10 requests/minute per IP to prevent abuse.

To adjust:
```javascript
// tts-service/index.js
const limiter = rateLimit({
  windowMs: 60 * 1000,
  max: 20, // Increase limit
});
```

### Text Validation

- Maximum 800 characters (enforced by TTS service)
- No HTML/script tags
- Frontend sanitizes before sending

### Authentication

Currently no auth on TTS service (relying on Django auth). To add JWT:

```javascript
// tts-service/middleware/auth.js
import jwt from 'jsonwebtoken';

export function requireAuth(req, res, next) {
  const token = req.headers.authorization?.replace('Bearer ', '');
  if (!token) {
    return res.status(401).json({ error: 'Unauthorized' });
  }
  
  try {
    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    req.user = decoded;
    next();
  } catch {
    res.status(401).json({ error: 'Invalid token' });
  }
}
```

## Monitoring

### Metrics to Track

1. **TTS Service**
   - Generation time (avg, p95, p99)
   - Error rate
   - Rate limit hits
   - Disk usage

2. **Backend**
   - TTS call success rate
   - Demo test detection accuracy
   - Audio URL inclusion rate

3. **Frontend**
   - Audio playback success rate
   - Autoplay failures
   - Penguin overlay render time

### Logging

**TTS Service:**
```javascript
console.log('📨 TTS request received:', { testId, textLength });
console.log('✅ Audio generated:', audioUrl);
console.error('❌ TTS generation failed:', error);
```

**Backend:**
```python
logger.info(f"✅ Generated TTS audio for demo test {test_id}: {audio_url}")
logger.error(f"Error generating TTS audio for test {test_id}: {str(e)}")
```

**Frontend:**
```typescript
console.log('🎙️ Demo test detected - playing audio with penguin overlay');
console.log('✅ Audio playback started');
console.error('❌ Audio playback failed:', error);
```

## Troubleshooting

### Audio not generating

1. Check TTS service is running: `curl http://localhost:3001/health`
2. Check Django can reach TTS service: Test from Django shell
3. Check logs in TTS service terminal
4. Verify text length < 800 chars

### Audio not playing

1. Check browser console for errors
2. Verify audio URL in network tab
3. Test audio URL directly in browser
4. Check autoplay policy (ensure user gesture flow)

### Penguin overlay not showing

1. Check `is_demo_test` flag in API response
2. Verify video `onEnded` callback fires
3. Check React dev tools for state updates

### Rate limit errors

1. Check TTS service logs
2. Increase rate limit in `index.js`
3. Add IP whitelisting if needed

## Future Enhancements

1. **Voice Selection**: Allow institution to choose voice (male/female, language)
2. **Audio Caching**: Cache audio for repeated checkpoint text
3. **Streaming**: Stream audio as it generates (reduce latency)
4. **Metrics Dashboard**: Real-time TTS usage statistics
5. **A/B Testing**: Compare audio vs no-audio engagement
6. **Multilingual**: Support Hindi, Tamil, Telugu voices

## Support

For issues or questions:
- Check logs in TTS service and Django backend
- Review TTS service README: `tts-service/README.md`
- Test endpoints manually with curl commands above
- Contact: support@inzighted.com

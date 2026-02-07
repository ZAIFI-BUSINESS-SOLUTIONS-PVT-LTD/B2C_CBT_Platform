# TTS Microservice

Server-side Text-to-Speech service for NeetNinja PWA using edge-tts.

## Overview

This microservice generates MP3 audio files from checkpoint insights text using Microsoft Edge's TTS engine with the Indian English voice "en-IN-NeerjaNeural".

## Features

- ✅ Server-side speech generation (no browser TTS)
- ✅ Indian English voice (Neerja Neural)
- ✅ MP3 output for universal compatibility
- ✅ Rate limiting (10 req/min per IP)
- ✅ Automatic file cleanup
- ✅ CORS-enabled for PWA/TWA

## Quick Start

### 1. Install Dependencies

```bash
cd tts-service
npm install
```

### 2. Start Service

```bash
npm start
```

Service runs on port 3001 by default.

### 3. Test Endpoint

```bash
curl -X POST http://localhost:3001/api/generate-insight-audio \
  -H "Content-Type: application/json" \
  -d '{"text": "Hi, you have completed your first test successfully"}'
```

Response:
```json
{
  "audioUrl": "/audio/insight-<uuid>.mp3",
  "filename": "insight-<uuid>",
  "generationTime": 234
}
```

### 4. Access Audio

```
http://localhost:3001/audio/insight-<uuid>.mp3
```

## API Endpoints

### POST /api/generate-insight-audio

Generate TTS audio from text.

**Request Body:**
```json
{
  "text": "Insight text to convert to speech",
  "testId": "123",  // Optional: for filename tagging
  "institution": "neet bro institute"  // Optional: for gating
}
```

**Response:**
```json
{
  "audioUrl": "/audio/<filename>.mp3",
  "filename": "<filename>",
  "generationTime": 234
}
```

**Errors:**
- 400: Invalid request (missing text, too long)
- 429: Rate limit exceeded
- 500: TTS generation failed

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "service": "tts-service",
  "timestamp": "2026-02-07T10:30:00.000Z"
}
```

### GET /audio/:filename

Serve generated audio files (static).

## Configuration

### Environment Variables

```bash
PORT=3001                  # Service port (default: 3001)
NODE_ENV=production        # Environment mode
MAX_AGE_HOURS=24          # Audio file max age for cleanup (default: 24)
```

### Voice Settings

Voice: `en-IN-NeerjaNeural` (Indian English Female)

To change voice, edit `services/tts.js`:
```javascript
const VOICE = 'en-IN-NeerjaNeural';
```

Available Indian English voices:
- `en-IN-NeerjaNeural` (Female)
- `en-IN-PrabhatNeural` (Male)

## File Cleanup

Audio files are stored in `public/audio/` and should be cleaned periodically.

### Manual Cleanup

```bash
npm run cleanup
```

### Automated Cleanup (Cron)

Add to crontab (runs daily at 3 AM):
```cron
0 3 * * * cd /path/to/tts-service && node scripts/cleanup-audio.js
```

### Windows Task Scheduler

Create a scheduled task:
- Program: `node`
- Arguments: `F:\ZAIFI\NeetNinja\tts-service\scripts\cleanup-audio.js`
- Schedule: Daily at 3:00 AM

## Deployment

### Development

```bash
npm run dev  # Auto-restart on file changes
```

### Production

```bash
npm start
```

### Reverse Proxy (Nginx)

Add to your Nginx config to proxy TTS service to same origin:

```nginx
# TTS service proxy
location /api/generate-insight-audio {
    proxy_pass http://localhost:3001/api/generate-insight-audio;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection 'upgrade';
    proxy_set_header Host $host;
    proxy_cache_bypass $http_upgrade;
}

location /audio/ {
    proxy_pass http://localhost:3001/audio/;
    proxy_cache public_cache;
    proxy_cache_valid 200 1h;
    add_header Cache-Control "public, max-age=3600";
}
```

### Docker (Optional)

```dockerfile
FROM node:18-alpine

WORKDIR /app
COPY package*.json ./
RUN npm install --production
COPY . .

EXPOSE 3001
CMD ["npm", "start"]
```

Build and run:
```bash
docker build -t tts-service .
docker run -p 3001:3001 tts-service
```

## Security

- ✅ Rate limiting: 10 requests/minute per IP
- ✅ Text length limit: 800 characters max
- ✅ Helmet security headers
- ✅ Request body size limit: 10KB
- ⚠️ No authentication (add JWT if needed)

### Adding Authentication

To require auth tokens, add middleware:

```javascript
// middleware/auth.js
export function requireAuth(req, res, next) {
  const token = req.headers.authorization?.replace('Bearer ', '');
  if (!token || !verifyToken(token)) {
    return res.status(401).json({ error: 'Unauthorized' });
  }
  next();
}

// In index.js
import { requireAuth } from './middleware/auth.js';
app.post('/api/generate-insight-audio', requireAuth, async (req, res) => {
  // ...
});
```

## Monitoring

### Logs

Service logs include:
- 📨 Request received
- 🎙️ Audio generation started
- ✅ Generation completed
- ❌ Errors

### Metrics to Track

- Generation time (avg, p95, p99)
- Error rate
- Rate limit hits
- Disk usage (audio files)

Example with Prometheus:
```javascript
import promClient from 'prom-client';

const generationTime = new promClient.Histogram({
  name: 'tts_generation_duration_seconds',
  help: 'TTS generation duration'
});

generationTime.observe((Date.now() - startTime) / 1000);
```

## Troubleshooting

### Audio not generating

1. Check logs for errors
2. Ensure `public/audio/` is writable
3. Test edge-tts directly:
   ```bash
   npx edge-tts -v "en-IN-NeerjaNeural" -t "Test audio" -o test.mp3
   ```

### CORS errors

Add to Nginx/Apache or enable in service:
```javascript
app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', '*');
  res.header('Access-Control-Allow-Methods', 'GET, POST');
  next();
});
```

### Rate limit too strict

Adjust in `index.js`:
```javascript
const limiter = rateLimit({
  windowMs: 60 * 1000,
  max: 20, // Increase limit
});
```

## Development

### Project Structure

```
tts-service/
├── index.js              # Express API server
├── services/
│   └── tts.js           # TTS generation logic
├── scripts/
│   └── cleanup-audio.js # Cleanup script
├── public/
│   └── audio/           # Generated MP3 files
├── package.json
└── README.md
```

### Testing

```bash
# Start service
npm start

# Test generation
curl -X POST http://localhost:3001/api/generate-insight-audio \
  -H "Content-Type: application/json" \
  -d '{"text": "Test audio generation", "testId": "test-123"}'

# Download audio
curl http://localhost:3001/audio/<filename>.mp3 -o test.mp3

# Play audio (Linux)
mpv test.mp3

# Play audio (Windows)
start test.mp3
```

## License

MIT

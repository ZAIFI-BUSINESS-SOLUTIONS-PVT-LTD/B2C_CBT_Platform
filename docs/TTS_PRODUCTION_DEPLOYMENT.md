# TTS Service - Production Deployment Summary

## ✅ Completed Setup

### 1. Service Installation
- **Location**: `/var/www/tts-service/`
- **User**: `www-data:www-data`
- **Node Version**: v20.19.5
- **Dependencies**: Installed successfully (express, uuid, fs-extra, helmet, express-rate-limit)
- **Python CLI**: edge-tts v7.2.7 (installed in Django venv: `/home/ubuntu/B2C_CBT_Platform/.venv`)

### 2. Systemd Service
- **Service File**: `/etc/systemd/system/tts-service.service`
- **Status**: ✅ Active and running on port 3001
- **Auto-start**: Enabled (will start on boot)
- **Logs**: 
  - `/var/log/tts-service.log` (stdout)
  - `/var/log/tts-service-error.log` (stderr)

**Service Commands**:
```bash
sudo systemctl status tts-service
sudo systemctl restart tts-service
sudo systemctl stop tts-service
sudo systemctl start tts-service
sudo journalctl -u tts-service -f  # Follow logs
```

### 3. Nginx Configuration
- **Config File**: `/etc/nginx/sites-enabled/api.conf`
- **Backup**: `/etc/nginx/sites-enabled/api.conf.backup`

**New Routes Added**:
```nginx
# TTS API endpoint (proxied to Node service)
location = /api/generate-insight-audio {
    proxy_pass http://127.0.0.1:3001/api/generate-insight-audio;
    # Timeout: 120s for audio generation
    # Forwards Authorization header for future auth
}

# Static audio files (served directly by Nginx for performance)
location /audio/ {
    alias /var/www/tts-service/public/audio/;
    # Cached for 1 hour
    # CORS enabled
}
```

### 4. Audio Cleanup Cron Job
- **Schedule**: Daily at 3:00 AM
- **User**: www-data
- **Log**: `/var/log/tts-cleanup.log`
- **Retention**: Deletes audio files older than 24 hours

**View/Edit Cron**:
```bash
sudo crontab -u www-data -l
sudo crontab -u www-data -e
```

## 🔗 API Usage

### Health Check
```bash
curl https://testapi.inzighted.com/health  # Goes to Django (default route)
curl http://127.0.0.1:3001/health          # TTS service health (direct)
```

### Generate Audio (from backend or frontend)
```bash
curl -X POST https://testapi.inzighted.com/api/generate-insight-audio \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"text": "Your checkpoint insight text here", "testId": "123"}'
```

**Response**:
```json
{
  "audioUrl": "/audio/insight-<uuid>.mp3",
  "filename": "insight-<uuid>",
  "generationTime": 800
}
```

### Access Audio
```bash
# Audio file URL (served by Nginx)
https://testapi.inzighted.com/audio/insight-<uuid>.mp3
```

## 📋 Django/Backend Integration

### Option 1: Direct API Call from Frontend
Frontend calls TTS API directly (recommended for async/non-blocking):
```javascript
const response = await fetch('https://testapi.inzighted.com/api/generate-insight-audio', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify({
    text: insightText,
    testId: testId,
    institution: institutionName
  })
});
const { audioUrl } = await response.json();
// Play audio: https://testapi.inzighted.com + audioUrl
```

### Option 2: Backend Proxies TTS Request
If Django needs to call TTS internally:

```python
import requests
from django.conf import settings

def generate_tts_audio(text, test_id=None):
    """Call TTS microservice to generate audio"""
    tts_url = 'http://127.0.0.1:3001/api/generate-insight-audio'
    
    payload = {
        'text': text,
        'testId': test_id
    }
    
    try:
        response = requests.post(
            tts_url,
            json=payload,
            timeout=90  # Match Nginx timeout
        )
        response.raise_for_status()
        data = response.json()
        
        # Return full URL
        return f"https://{settings.DOMAIN}{data['audioUrl']}"
    except requests.RequestException as e:
        logger.error(f"TTS generation failed: {e}")
        return None
```

### Gunicorn Settings (Already Configured)
Your current Gunicorn setup is fine:
- **Workers**: 3
- **Timeout**: 1200s (sufficient for TTS calls)
- **Binding**: 127.0.0.1:8000

No changes needed unless you want to reduce timeout for non-TTS endpoints.

## 🔒 Security Considerations

### Current Setup
- ✅ Rate limiting: 10 requests/min per IP (built into TTS service)
- ✅ Text length limit: 800 characters max
- ✅ Helmet security headers
- ✅ Request body size limit: 10KB
- ⚠️ No authentication (TTS endpoint is publicly accessible)

### Adding Authentication (Optional)
If you want to restrict TTS to authenticated users:

1. **Update Django to forward auth token**:
```python
# In your Django view that calls TTS
headers = {
    'Authorization': request.headers.get('Authorization', '')
}
response = requests.post(tts_url, json=payload, headers=headers, timeout=90)
```

2. **Add auth middleware to TTS service** (`/var/www/tts-service/middleware/auth.js`):
```javascript
export function requireAuth(req, res, next) {
  const token = req.headers.authorization?.replace('Bearer ', '');
  
  if (!token) {
    return res.status(401).json({ error: 'Unauthorized' });
  }
  
  // Verify JWT or shared secret
  // For now, just check if token exists
  next();
}
```

3. **Apply middleware** (edit `/var/www/tts-service/index.js`):
```javascript
import { requireAuth } from './middleware/auth.js';
app.post('/api/generate-insight-audio', requireAuth, async (req, res) => {
  // ... existing code
});
```

4. **Restart service**:
```bash
sudo systemctl restart tts-service
```

## 📊 Monitoring

### Check Service Status
```bash
# Service health
sudo systemctl status tts-service

# Recent logs
sudo tail -f /var/log/tts-service.log

# Error logs
sudo tail -f /var/log/tts-service-error.log

# Cleanup logs
sudo tail -f /var/log/tts-cleanup.log
```

### Check Audio Storage
```bash
# List generated audio files
ls -lh /var/www/tts-service/public/audio/

# Check disk usage
du -sh /var/www/tts-service/public/audio/
```

### Performance Metrics to Track
- Audio generation time (target: < 3s for 800 chars)
- Error rate (should be < 1%)
- Rate limit hits (adjust if legitimate traffic is blocked)
- Disk usage (audio files should auto-cleanup daily)

## 🧪 Testing Checklist

### ✅ Basic Functionality
```bash
# 1. Service is running
curl http://127.0.0.1:3001/health

# 2. Generate audio locally
curl -X POST http://127.0.0.1:3001/api/generate-insight-audio \
  -H "Content-Type: application/json" \
  -d '{"text":"Test audio"}'

# 3. Access audio file directly
curl -I http://127.0.0.1:3001/audio/insight-<uuid>.mp3

# 4. Access through Nginx
curl -I https://testapi.inzighted.com/audio/insight-<uuid>.mp3

# 5. Generate via Nginx proxy
curl -X POST https://testapi.inzighted.com/api/generate-insight-audio \
  -H "Content-Type: application/json" \
  -d '{"text":"Nginx proxy test"}'
```

### ✅ Edge Cases
```bash
# Long text (should succeed, < 800 chars)
curl -X POST http://127.0.0.1:3001/api/generate-insight-audio \
  -H "Content-Type: application/json" \
  -d '{"text":"'"$(python3 -c 'print("A" * 790)')"'"}'

# Too long (should fail with 400)
curl -X POST http://127.0.0.1:3001/api/generate-insight-audio \
  -H "Content-Type: application/json" \
  -d '{"text":"'"$(python3 -c 'print("A" * 850)')"'"}'

# Rate limiting (10+ rapid requests should get 429)
for i in {1..12}; do curl -X POST http://127.0.0.1:3001/api/generate-insight-audio -H "Content-Type: application/json" -d '{"text":"Rate limit test"}'; done
```

## 🔧 Troubleshooting

### Service Won't Start
```bash
# Check logs
sudo journalctl -u tts-service -n 50

# Verify Node path
ls -la /home/ubuntu/.nvm/versions/node/v20.19.5/bin/node

# Verify edge-tts
source /home/ubuntu/B2C_CBT_Platform/.venv/bin/activate
which edge-tts
edge-tts --version
```

### Audio Not Generating
```bash
# Test edge-tts directly
source /home/ubuntu/B2C_CBT_Platform/.venv/bin/activate
edge-tts --voice "en-IN-NeerjaNeural" --text "Test" --write-media /tmp/test.mp3
ls -lh /tmp/test.mp3

# Check permissions
ls -ld /var/www/tts-service/public/audio/
# Should be: drwxr-xr-x www-data www-data
```

### Nginx 502/504 Errors
```bash
# Check if TTS service is running
sudo systemctl status tts-service

# Check Nginx error log
sudo tail -f /var/nginx/error.log | grep tts

# Test direct connection
curl http://127.0.0.1:3001/health
```

### Audio Files Not Cleaning Up
```bash
# Test cleanup script manually
cd /var/www/tts-service
/home/ubuntu/.nvm/versions/node/v20.19.5/bin/node scripts/cleanup-audio.js

# Check cron logs
sudo tail -f /var/log/tts-cleanup.log

# Verify cron is set
sudo crontab -u www-data -l | grep cleanup
```

## 🚀 Future Enhancements

### Recommended Improvements
1. **Add JWT authentication** to restrict TTS access
2. **Implement audio caching** (check if same text was recently generated)
3. **Use Redis queue** for async TTS processing (avoid blocking requests)
4. **Add Prometheus metrics** for monitoring
5. **Configure CDN** for audio delivery (if high traffic)
6. **Voice selection** endpoint (allow users to pick voice)
7. **Background queue** integration with Celery (for heavy load)

### Scaling Considerations
- Current setup handles ~10 requests/min per IP
- For high traffic, consider:
  - Multiple TTS service instances with load balancer
  - S3/Cloud storage for audio files
  - CDN for audio delivery
  - Redis caching for duplicate text requests

## 📝 Maintenance Tasks

### Weekly
- Check audio storage size: `du -sh /var/www/tts-service/public/audio/`
- Review error logs: `sudo grep -i error /var/log/tts-service-error.log`

### Monthly
- Update dependencies: `cd /var/www/tts-service && sudo -u www-data npm update`
- Review rate limit settings (adjust if needed)
- Check disk space on server

### As Needed
- Rotate logs if they grow too large
- Update edge-tts: `source .venv/bin/activate && pip install --upgrade edge-tts`
- Update Node if security patches released

## 📞 Quick Reference

**Service**: `sudo systemctl restart tts-service`  
**Logs**: `tail -f /var/log/tts-service.log`  
**Audio Path**: `/var/www/tts-service/public/audio/`  
**Config**: `/etc/nginx/sites-enabled/api.conf`  
**Port**: 3001 (internal), 443 (public via Nginx)  
**Cron**: `sudo crontab -u www-data -e`

---

**Deployment Date**: 2026-02-07  
**Deployed By**: System Administrator  
**Environment**: Production (testapi.inzighted.com)

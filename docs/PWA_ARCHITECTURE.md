# InzightEd PWA Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER'S ANDROID DEVICE                     │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  Home Screen                                            │    │
│  │  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────────────┐       │    │
│  │  │ App1 │  │ App2 │  │ App3 │  │  InzightEd   │       │    │
│  │  └──────┘  └──────┘  └──────┘  │  (YOUR PWA)  │       │    │
│  │                                  └──────────────┘       │    │
│  └────────────────────────────────────────────────────────┘    │
│                            ▼ Tap to open                        │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  InzightEd App (Fullscreen - No Browser UI)           │    │
│  │  ┌──────────────────────────────────────────────────┐ │    │
│  │  │                                                   │ │    │
│  │  │         React Frontend (Vite)                    │ │    │
│  │  │         - Dashboard                              │ │    │
│  │  │         - Tests                                  │ │    │
│  │  │         - Results                                │ │    │
│  │  │         - Chatbot                                │ │    │
│  │  │                                                   │ │    │
│  │  └──────────────────────────────────────────────────┘ │    │
│  │                            ▲                            │    │
│  │                            │                            │    │
│  │  ┌─────────────────────────┴─────────────────────┐    │    │
│  │  │      Service Worker (Caching Layer)           │    │    │
│  │  │  ┌──────────────┐  ┌───────────────────────┐ │    │    │
│  │  │  │ Cache Store  │  │  Network Requests     │ │    │    │
│  │  │  │  - HTML      │  │   /api/* → Django     │ │    │    │
│  │  │  │  - CSS       │  │   (Always Fresh)      │ │    │    │
│  │  │  │  - JS        │  │                       │ │    │    │
│  │  │  │  - Images    │  │  Offline: Serve cache │ │    │    │
│  │  │  └──────────────┘  └───────────────────────┘ │    │    │
│  │  └───────────────────────────────────────────────┘    │    │
│  └────────────────────────────────────────────────────────┘    │
│                            │                                    │
│                            │ HTTPS                              │
│                            ▼                                    │
└─────────────────────────────────────────────────────────────────┘
                             │
                             │ Internet
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      YOUR SERVER (HTTPS)                         │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Static Files (dist/public/)                             │  │
│  │  ├── index.html                                           │  │
│  │  ├── manifest.json                                        │  │
│  │  ├── service-worker.js                                    │  │
│  │  ├── assets/                                              │  │
│  │  │   ├── main-abc123.js                                   │  │
│  │  │   └── main-xyz789.css                                  │  │
│  │  └── icons/                                               │  │
│  │      ├── icon-72.png                                      │  │
│  │      ├── icon-192.png                                     │  │
│  │      └── icon-512.png                                     │  │
│  └──────────────────────────────────────────────────────────┘  │
│                            │                                    │
│                            │ API Proxy                          │
│                            ▼                                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Django Backend (Port 8000)                              │  │
│  │  ├── /api/auth/*                                         │  │
│  │  ├── /api/tests/*                                        │  │
│  │  ├── /api/dashboard/*                                    │  │
│  │  ├── /api/chatbot/*                                      │  │
│  │  └── /api/payments/*                                     │  │
│  └──────────────────────────────────────────────────────────┘  │
│                            │                                    │
│                            ▼                                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  PostgreSQL Database                                     │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. Initial Install
```
User visits HTTPS URL
  ↓
Manifest.json loaded → Install prompt appears
  ↓
User clicks "Install"
  ↓
App added to home screen with icon
  ↓
Service worker registered & activated
```

### 2. App Launch (Online)
```
User taps home screen icon
  ↓
App opens fullscreen (no browser UI)
  ↓
Service worker intercepts requests
  ↓
Static assets: Cache first → Fast load
  ↓
API requests: Network first → Fresh data from Django
```

### 3. App Launch (Offline)
```
User taps home screen icon (no internet)
  ↓
App opens fullscreen
  ↓
Service worker intercepts requests
  ↓
Static assets: Served from cache → App works!
  ↓
API requests: Fail gracefully → Show offline message
```

## Request Flow Examples

### Static Asset (e.g., main.js)
```
Browser → Service Worker → Check Cache
           ↓                    ↓
        Found in cache     Not in cache
           ↓                    ↓
      Return cached         Fetch from network
                                ↓
                           Add to cache
                                ↓
                           Return to browser
```

### API Request (e.g., /api/dashboard/)
```
Browser → Service Worker → BYPASS CACHE
                              ↓
                         Network fetch
                              ↓
                        Django backend
                              ↓
                      Return fresh data
```

## File Structure

```
client/
├── index.html              # Entry point (PWA meta tags added)
├── src/
│   ├── main.tsx           # Service worker registration
│   ├── App.tsx            # React app (unchanged)
│   └── components/
│       └── PWAInstallButton.tsx  # Optional install UI
└── public/
    ├── manifest.json      # PWA configuration ✨ NEW
    ├── service-worker.js  # Caching logic ✨ NEW
    └── icons/             # App icons ✨ NEW
        ├── icon-72.png
        ├── icon-192.png
        ├── icon-512.png
        └── ... (all sizes)
```

## Caching Rules

| Path Pattern | Strategy | Reason |
|--------------|----------|--------|
| `/api/*` | Network Only | Always fresh data from Django |
| `/admin/*` | Network Only | Admin panel needs auth |
| `/auth/*` | Network Only | Authentication must be real-time |
| `/static/*` | Cache First | Static assets rarely change |
| `/assets/*` | Cache First | Build assets have hash in filename |
| `/icons/*` | Cache First | App icons never change |
| Navigation | Network First | Try online, fallback to cache |

## Installation Requirements

✅ Served over HTTPS  
✅ Valid manifest.json  
✅ Icons (192x192 and 512x512 minimum)  
✅ Service worker registered  
✅ Service worker has fetch handler  
✅ User engages with site (30 seconds)  

## Key Features

### 1. Installability
- Add to home screen
- Custom app icon
- App name
- Splash screen

### 2. Standalone Mode
- Fullscreen app
- No browser UI
- Native app feel

### 3. Offline Support
- Cached static assets
- Works without internet (pages)
- Graceful API failures

### 4. Performance
- Cache-first for static assets
- Instant load times
- Reduced bandwidth usage

### 5. Automatic Updates
- Checks every 60 seconds
- Downloads in background
- Activates on next visit

## Testing Workflow

```
1. Generate Icons
   ↓
2. npm run build
   ↓
3. Deploy dist/public/ to HTTPS server
   ↓
4. Open in Chrome on Android
   ↓
5. Wait 30 seconds
   ↓
6. Install prompt appears
   ↓
7. Tap "Install"
   ↓
8. App on home screen ✅
```

## Deployment Checklist

- [ ] Icons generated (8 files)
- [ ] Production build successful
- [ ] dist/public/ uploaded to server
- [ ] HTTPS enabled
- [ ] Django backend accessible
- [ ] CORS configured for domain
- [ ] Tested on Android Chrome
- [ ] Install successful
- [ ] App opens fullscreen
- [ ] API calls work
- [ ] Offline pages load

## Maintenance

### Updating the App
1. Make code changes
2. `npm run build`
3. Deploy new `dist/public/`
4. Service worker auto-updates users

### Changing Icons
1. Replace `source-icon.png`
2. `npm run generate-icons`
3. `npm run build`
4. Deploy

### Changing Manifest
1. Edit `client/public/manifest.json`
2. `npm run build`
3. Deploy
4. Users see changes on next install

---

**This architecture ensures**:
- ✅ Fast loading (cached assets)
- ✅ Works offline (static pages)
- ✅ Always fresh data (API calls)
- ✅ Native app experience
- ✅ Automatic updates
- ✅ No backend changes needed

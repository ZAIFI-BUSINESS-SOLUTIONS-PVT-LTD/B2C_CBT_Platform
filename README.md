# NEET Bro (NeetNinja)

A B2C Computer-Based Test (CBT) platform for NEET exam preparation. Students take adaptive mock tests, previous-year question papers, and a daily Question of the Day; the platform analyzes performance (zone insights, focus zones, misconceptions) and offers an AI chatbot tutor. Institutions can onboard their own students, upload offline results/answer keys, and view cohort analytics. The web app is a installable PWA with an Android TWA wrapper and supports both Razorpay (web) and Google Play Billing (in-app) subscriptions.

## Architecture

The project is a monorepo with three runtime services and a native app wrapper:

| Component | Path | Stack | Purpose |
|---|---|---|---|
| Frontend (PWA) | [client/](client/) | React 18, TypeScript, Vite, Tailwind, Radix UI, TanStack Query | Student, institution admin, and platform admin web UI |
| Backend API | [backend/](backend/) | Django 5.2, Django REST Framework, Celery, PostgreSQL, Redis | Auth, tests, payments, analytics, chatbot, institutions |
| TTS microservice | [tts-service/](tts-service/) | Node.js, Express, edge-tts | Generates Indian-English voice audio for insight text |
| Android wrapper | [twa/](twa/) | Gradle / Trusted Web Activity (Bubblewrap) | Packages the PWA as a Play Store app with Play Billing |
| Build output | [dist/](dist/) | — | Production build artifact of the frontend, deployed to S3/CloudFront |

The frontend calls the Django REST API (JSON keys in camelCase via `djangorestframework-camel-case`), calls the TTS microservice directly for audio playback, and is packaged into the `twa/` Android project for Play Store distribution.

## Key features

- **Adaptive testing** — rule-based question selection engine (14 rules covering difficulty ratios, weak/strong topics, numeric-answer tolerance, exclusion windows) for platform tests
- **Previous Year Question papers (PYQs)** and daily **Question of the Day**
- **Zone Insights / Focus Zone** — async (Celery) analytics that surface weak topics and recurring misconceptions after each test
- **AI chatbot tutor** — Gemini + LangChain, with chat memory/sessions and API key rotation (up to 10 keys)
- **Authentication** — JWT (student), Google OAuth, mobile OTP via MSG91, plus separate institution-admin and platform-admin logins
- **Payments** — Razorpay (web) and Google Play Billing (Android in-app subscriptions), with webhook-based reconciliation
- **Institutions** — self-registration, student linking, offline result & answer-key upload (Excel), institution-level analytics
- **PWA** — offline support, install prompts, background sync via Workbox (`vite-plugin-pwa`)
- **Platform admin panel** — Django-template based test/question management and live session metrics

## Repository layout

```
backend/            Django project (neet_backend settings, neet_app domain logic)
  neet_app/
    models.py       23 models: tests, sessions, institutions, payments, chat, notifications...
    views/          30+ view modules grouped by domain
    services/       Razorpay, Play Billing, selection engine, zone insights, chatbot, AI clients
    tasks.py        Celery tasks (results computation, insights, misconceptions)
    management/commands/  Ops scripts (data population, expiry cleanup, payment reconciliation)
  external_db/      Secondary app for syncing questions/topics from a source DB
  tests/            pytest test suite
client/             React frontend (Vite)
  src/pages/        mobile/, desktop/, responsive/ variants + shared pages (test, results, payment...)
  src/components/   UI primitives (shadcn/Radix), test interface, chatbot, payments, institution UI
  src/hooks/, src/contexts/, src/lib/, src/config/
tts-service/        Express microservice wrapping edge-tts
twa/                Android TWA (Trusted Web Activity) Gradle project
docs/               Feature/architecture write-ups (PWA, TWA, payments, TTS, zone insights, etc.)
dist/               Production frontend build output (generated, deployed via CI)
```

See [docs/](docs/) for deep-dive write-ups on specific features (PWA architecture, Play Billing setup, Razorpay checklist, MSG91 integration, zone insights, misconceptions, delete-account flow, testing guide, etc).

## Prerequisites

- Node.js 20+ and npm (frontend + TTS service)
- Python 3.11+ and pip (backend)
- PostgreSQL 16
- Redis (Celery broker/result backend, OTP + rate-limit caching)
- Optional: Neo4j (only if graph-based features via `neomodel` are enabled)

## Getting started

### 1. Backend (Django API)

```bash
cd backend
pip install -r ../requirements.txt
```

Configure environment variables (see [Environment variables](#environment-variables) below), then:

```bash
python manage.py migrate
python manage.py runserver
```

Run the Celery worker separately for async tasks (results computation, zone insights, notifications):

```bash
celery -A neet_backend worker --loglevel=INFO --concurrency=2
```

### 2. Frontend (PWA)

```bash
cp client/.env.example client/.env
npm install
npm run dev
```

Vite dev server runs on port 5000 by default (see `.replit` port mapping). Set `VITE_API_BASE_URL` to point at your local backend (default `http://localhost:8000/api`).

### 3. TTS microservice (optional, for voice insights)

```bash
cd tts-service
npm install
npm start
```

Runs on port 3001 by default; the backend calls it via `TTS_SERVICE_URL`.

### 4. Android TWA (optional, for Play Store builds)

See [docs/TWA_PLAY_BILLING_IMPLEMENTATION.md](docs/TWA_PLAY_BILLING_IMPLEMENTATION.md) and the Gradle project in [twa/](twa/).

## Environment variables

Backend (Django) reads these from the process environment — create a `.env` in `backend/` or export them before running:

| Variable | Purpose |
|---|---|
| `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS` | Django core settings |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | Primary PostgreSQL database |
| `SRC_DB_*` | Optional secondary/source database (question sync) |
| `NEO4J_BOLT_URL` | Neo4j connection (if graph features used) |
| `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB` or `REDIS_URL` | Redis (Celery + caching) |
| `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` | Celery (defaults to Redis) |
| `JWT_*` | JWT lifetime/rotation overrides (`djangorestframework-simplejwt`) |
| `EMAIL_*`, `DEFAULT_FROM_EMAIL`, `EMAIL_PROVIDER` | Transactional email (password reset, etc.) |
| `MSG91_AUTH_KEY`, `MSG91_TEMPLATE_ID`, `MSG91_OTP_EXPIRY` | SMS OTP delivery |
| `GEMINI_API_KEY_1`..`GEMINI_API_KEY_10` (or `GEMINI_API_KEY`) | Chatbot LLM, with rotation across up to 10 keys |
| `LANGCHAIN_API_KEY`, `LANGCHAIN_TRACING_V2` | LangChain tracing (optional) |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | Google OAuth login |
| `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET` | Web payments |
| `PLAY_PACKAGE_NAME`, `PLAY_SERVICE_ACCOUNT_JSON` | Google Play Billing verification |
| `TTS_SERVICE_URL` | URL of the TTS microservice |
| `SENTRY_DSN` | Error tracking (optional) |
| `FEATURE_INSTITUTION_TESTS` | Feature flag for institution test flows |

Frontend (`client/.env`, see [client/.env.example](client/.env.example)):

| Variable | Purpose |
|---|---|
| `VITE_GOOGLE_CLIENT_ID` | Google OAuth client ID |
| `VITE_API_BASE_URL` | Base URL of the Django API |

TTS service:

| Variable | Purpose |
|---|---|
| `PORT` | Service port (default 3001) |
| `MAX_AGE_HOURS` | Max age before generated audio files are cleaned up |

## Testing

Backend uses pytest:

```bash
cd backend
pytest                      # runs suite in backend/tests
pytest -m "not slow"        # skip slow/stress tests
```

Markers available: `unit`, `integration`, `stress`, `slow`, `auth`, `chat`, `question_selection`, `export`. See [docs/TESTING_GUIDE.md](docs/TESTING_GUIDE.md).

Frontend type-checking:

```bash
npm run check
```

## Deployment

- **Frontend**: [.github/workflows/frontend-deploy.yml](.github/workflows/frontend-deploy.yml) builds on push to `main` and syncs `dist/` to S3 + invalidates CloudFront.
- **Backend**: `Procfile` defines `web` (gunicorn) and `worker` (Celery) processes for platform-as-a-service deployment.
- **Android**: build and sign via the `twa/` Gradle project for Play Store submission.

## Documentation

Detailed, feature-specific documentation lives in [docs/](docs/), including PWA architecture and offline behavior, Play Billing and Razorpay setup/checklists, MSG91 SMS integration, TTS deployment, zone insights/misconception engine internals, and the account-deletion flow.

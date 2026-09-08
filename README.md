# Hunger Birds

Campus food ordering for BIT Mesra. Students browse the food stalls on campus,
place cash-on-delivery orders, and watch the status update live; stall owners
manage their menu and work through incoming orders from a separate app.

- **Customer app** (Flutter) — browse stalls, order, track live
- **Merchant app** (Flutter) — stall dashboard, live order queue, menu management
- **Backend** (FastAPI + Postgres + Redis) — API, auth, realtime

Sign-up is restricted to `@bitmesra.ac.in` email addresses. Payment is cash
only — there is no payment gateway.

## Repository layout

```
backend/               FastAPI service (API, auth, WebSockets)
apps/customer_app/     Flutter app for students
apps/merchant_app/     Flutter app for stall owners
packages/hb_shared/    Shared Dart: models, API client, login flow, theme
```

## How it works

**Auth.** A student enters their institute email; the backend generates a
6-digit code, stores it in Redis with a 5-minute TTL, and emails it through
Resend. Verifying the code issues a JWT access/refresh pair. Only
`@bitmesra.ac.in` addresses are accepted, and `+tag` addressing is normalised
away (`me+1@…` and `me@…` are the same account) so one person can't spin up
unlimited accounts.

**Vendors.** Anyone can apply to run a stall, but the stall stays invisible to
students until an admin approves it. Approved stalls also carry an
open/closed switch the owner controls from their app.

**Orders.** A cart holds items from one stall. Placing an order snapshots each
item's name and price, so later menu edits never rewrite order history. Status
moves through an explicit state machine — `placed → accepted → preparing →
ready → completed`, with `rejected`/`cancelled` as terminal branches — and
invalid jumps are rejected by the API.

**Realtime.** Every status change publishes to Redis pub/sub. The customer's
tracking screen subscribes to `order:{id}` and the merchant's queue to
`vendor:{id}`, so both sides update within a second without polling. Clients
re-fetch on reconnect, so nothing is lost if a socket drops.

## Running the backend locally

Requires Python 3.11+, Postgres and Redis.

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env          # then edit DATABASE_URL / JWT_SECRET
alembic upgrade head
PYTHONPATH=. python scripts/seed.py    # optional: demo stalls + admin user

uvicorn app.main:app --reload
```

With `OTP_DEBUG_ECHO=true` (the default in `.env.example`) the login endpoint
returns the OTP in its response, so you can sign in locally without a Resend
key. **Keep it `false` in production** — it would otherwise let anyone log in
as any address.

To make a user an admin, have them log in once, then:

```bash
PYTHONPATH=. python scripts/promote_admin.py you@bitmesra.ac.in
```

## Running the apps

```bash
cd apps/customer_app     # or apps/merchant_app
flutter pub get
flutter run --dart-define=API_BASE_URL=http://localhost:8000
```

Point `API_BASE_URL` at the deployed URL to run against production. On an
Android emulator, localhost on the host machine is `http://10.0.2.2:8000`.

Tests: `flutter test` in either app, `flutter analyze` for lints.

## Deployment (Railway)

The backend deploys from this repo with no Dockerfile — Railway's builder
detects Python from `requirements.txt`. The service is configured with:

- **Root directory** `/backend` (the repo also holds the Flutter apps)
- **Start command** `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Healthcheck** `/health`

Alongside it run a Postgres and a Redis service. Required variables on the API
service:

| Variable | Notes |
| --- | --- |
| `DATABASE_URL` | Postgres URL; a plain `postgres://` URL is upgraded to the asyncpg driver automatically |
| `REDIS_URL` | Redis URL |
| `JWT_SECRET` | Long random string |
| `ALLOWED_EMAIL_DOMAIN` | `bitmesra.ac.in` |
| `OTP_DEBUG_ECHO` | `false` in production |
| `RESEND_API_KEY` | Required for OTP emails to actually send |
| `RESEND_FROM_EMAIL` | Must use a domain verified in Resend |
| `CLOUDINARY_*` | Cloud name, API key, API secret for menu/cover photos |

Images are uploaded straight from the phone to Cloudinary's free tier using a
short-lived signature minted by `GET /media/signature`, so image bytes never
pass through the backend.

## Things to know before going live

- **Resend needs a verified domain** before it will deliver to real
  `@bitmesra.ac.in` inboxes. Until then OTP emails won't arrive.
- **Distributing the apps** is not covered here. Android can be sideloaded as
  an APK; iOS requires an Apple Developer account ($99/yr) even for TestFlight.
- **No ratings or reviews** — deliberately out of scope for the first version.

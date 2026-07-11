# Smart Truck Parking Management System

A production-ready, full-stack truck yard management platform.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI 0.111 + SQLAlchemy 2 (async) |
| Database | PostgreSQL 16 |
| Frontend | Next.js 14 (App Router) + TypeScript + Tailwind CSS |
| Messaging | MSG91 WhatsApp Business API |
| Auth | JWT (access + refresh tokens) with bcrypt |
| Migrations | Alembic |
| Container | Docker Compose + Nginx reverse proxy |
| PWA | next-pwa (offline shell, installable on mobile) |

---

## Architecture

```
Browser / Mobile PWA
        │
        ▼
   Nginx :80
   ┌─────┴──────────────┐
   │                    │
   ▼                    ▼
Next.js :3000     FastAPI :8000
   (App Router)         │
                   PostgreSQL :5432
```

**Roles:**
- **Admin** — full dashboard, billing config, user management, report export
- **Gatekeeper** — entry form, exit/billing flow, personal session history

---

## Quick Start (Docker)

```bash
python ../main.py
```

Or start the stack manually:

```bash
docker compose up --build
```

Configuration is already in `backend/.env` and `frontend/.env`. Edit those files if you need to change credentials, CORS origins, database settings, or MSG91 keys.

The first boot automatically:
1. Runs Alembic migrations
2. Seeds the root admin account
3. Seeds the default gatekeeper account
4. Seeds default billing rules

Open `http://localhost` and log in with:

| Role | Mobile | Password |
|---|---|---|
| Admin | `7200775876` | `0000` |
| Gatekeeper | `8888888888` | `0000` |

---

## Local Development

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# edit .env if you need a different DATABASE_URL

alembic upgrade head
python -m app.db.seed

uvicorn app.main:app --reload
# → http://localhost:8000
# → http://localhost:8000/docs  (Swagger UI)
```

### Frontend

```bash
cd frontend
npm install
# edit .env if you need a different NEXT_PUBLIC_API_URL

npm run dev
# → http://localhost:3000
```

### Tests

```bash
cd backend
pytest tests/
```

---

## API Reference

Interactive docs: `http://localhost:8000/docs`

### Core Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/auth/login` | Public | Login → JWT tokens |
| POST | `/api/v1/auth/refresh` | Public | Refresh access token |
| GET | `/api/v1/auth/me` | Any | Current user |
| POST | `/api/v1/sessions/entry` | GK/Admin | Log truck entry |
| GET | `/api/v1/sessions/search?q=` | GK/Admin | Search by truck # or mobile |
| GET | `/api/v1/sessions/history` | GK/Admin | Paginated history |
| POST | `/api/v1/sessions/{id}/exit` | GK/Admin | Log exit + calculate bill |
| POST | `/api/v1/payments/{id}/mark-paid` | GK/Admin | Collect payment |
| GET | `/api/v1/dashboard/summary` | Admin | KPI summary |
| GET | `/api/v1/dashboard/live` | GK/Admin | Live trucks inside |
| GET/POST/PUT/DELETE | `/api/v1/billing/rules` | Admin | Billing rule CRUD |
| GET/PUT | `/api/v1/settings` | Admin | System / MSG91 settings |
| GET/POST/PATCH | `/api/v1/users` | Admin | User management |
| GET | `/api/v1/reports/export` | Admin | Download Excel/PDF |
| POST | `/api/v1/uploads/photo` | GK/Admin | Upload truck photo |

---

## Billing Engine

Rules are admin-configurable from the UI — no code changes needed.

**Example (default seed):**

| Rule | Range | Charge |
|---|---|---|
| First 12 Hours | 0–12h | ₹100 |
| 12–24 Hours | 12–24h | ₹150 |
| Additional Day | >24h (open-ended) | ₹100/day (ceil-rounded) |

Open-ended rules (no "To Hours") charge `amount × ceil(extra_hours / 24)` per additional day beyond their "From Hours" threshold.

---

## MSG91 WhatsApp Notifications

Configure via **Admin Panel → Settings**:

- `MSG91 AuthKey` — from the MSG91 dashboard
- `WhatsApp Number` — your registered business number
- `Entry Template Name` — the WhatsApp template to use on entry
- `Exit Template Name` — the WhatsApp template to use on exit/payment

Notifications are fire-and-forget (background task) — a failed notification never blocks entry/exit. Every attempt is recorded in the `notifications` table for audit.

---

## Project Structure

```
truckpark/
├── backend/
│   ├── app/
│   │   ├── core/          # config, security, dependencies
│   │   ├── db/            # session, base, migrations, seed
│   │   ├── models/        # SQLAlchemy ORM models
│   │   ├── schemas/       # Pydantic schemas
│   │   ├── routers/       # FastAPI route handlers
│   │   ├── services/      # billing engine, MSG91, exports
│   │   └── utils/         # time helpers, logging
│   ├── tests/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── alembic.ini
│
├── frontend/
│   ├── app/
│   │   ├── (auth)/login/
│   │   ├── (gatekeeper)/  # entry, exit, history
│   │   └── (admin)/       # dashboard, sessions, billing, users, reports
│   ├── components/        # shared UI components
│   ├── lib/               # api client, auth, utils
│   ├── Dockerfile
│   └── package.json
│
├── nginx/nginx.conf
├── docker-compose.yml
└── README.md
```

---

## Production Checklist

- [ ] Set a strong `SECRET_KEY` (32+ random bytes)
- [ ] Change `ROOT_ADMIN_PASSWORD` immediately after first login
- [ ] Configure MSG91 credentials in Admin → Settings
- [ ] Set `CORS_ORIGINS` to your actual domain(s)
- [ ] Point `DATABASE_URL` to a managed PostgreSQL instance
- [ ] Add SSL termination in Nginx (Let's Encrypt / Certbot)
- [ ] Set up automated DB backups (pg_dump or managed DB snapshots)
- [ ] Replace local `uploads/` with cloud object storage (AWS S3 / Cloudflare R2) for photo storage in production

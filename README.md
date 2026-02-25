# HRMS Lite

A lightweight, production-ready Human Resource Management System with FastAPI + PostgreSQL backend and React + Tailwind frontend.

## Project Overview

HRMS Lite provides:
- Employee management (add, list, delete)
- Attendance management (mark and view per employee)
- Optional analytics in UI (total present days, quick dashboard count)
- Clean layered architecture with repository + service separation
- Superadmin shared-key entrance and protected REST API access

## Tech Stack

### Backend
- FastAPI
- SQLAlchemy 2.0 ORM
- PostgreSQL
- Alembic migrations
- Gunicorn + Uvicorn worker for production serving

### Frontend
- React (Vite)
- Tailwind CSS
- Axios
- React Router
- React Hot Toast

## Repository Structure

```text
backend/
  app/
    main.py
    core/
    db/
    models/
    schemas/
    repositories/
    services/
    api/
    utils/
  alembic/
  alembic.ini
  requirements.txt

frontend/
  src/
    api/
    components/
    pages/
    hooks/
    layouts/
    utils/
    App.jsx
    main.jsx

scripts/
   hrmsctl.py
```

## Unified Service Runner (SSH-safe)

Use the controller script to start/stop/status both services together with platform selection via `-p`.

```bash
python3 scripts/hrmsctl.py <start|stop|status> -p <docker|venv> [--build] [--wait]
```

Examples:

```bash
python3 scripts/hrmsctl.py start -p docker --build --wait
python3 scripts/hrmsctl.py status -p docker
python3 scripts/hrmsctl.py stop -p docker

python3 scripts/hrmsctl.py start -p venv --wait
python3 scripts/hrmsctl.py status -p venv
python3 scripts/hrmsctl.py stop -p venv
```

Notes:
- `-p docker` uses `docker compose up -d` (optional `--build`) / `docker compose down`.
- `-p venv` performs setup (venv, dependencies, migrations, frontend build), then starts backend/frontend detached.
- `--wait` blocks until health checks pass for backend/frontend.
- venv mode writes logs to `.runtime/logs/` and PID files to `.runtime/pids/`.
- Processes are launched detached and continue running after SSH disconnect.
- Docker mode URLs: frontend `http://localhost:5173`, backend `http://localhost:8001`.
- venv mode URLs: frontend `http://localhost:5173`, backend `http://localhost:8000`.

Environment overrides (optional):
- `HRMS_HOST` (default: `127.0.0.1`)
- `HRMS_DOCKER_BACKEND_PORT` (default: `8001`)
- `HRMS_DOCKER_FRONTEND_PORT` (default: `5173`)
- `HRMS_VENV_BACKEND_PORT` (default: `8000`)
- `HRMS_VENV_FRONTEND_PORT` (default: `5173`)
- `HRMS_DOCKER_BACKEND_HEALTH_URL`, `HRMS_DOCKER_FRONTEND_URL`
- `HRMS_VENV_BACKEND_HEALTH_URL`, `HRMS_VENV_FRONTEND_URL`

## Backend API Endpoints

All protected endpoints require header:
- `X-Superadmin-Key: <shared_key>`

### Employee
- `POST /api/employees` - Create employee
- `GET /api/employees` - List employees
- `DELETE /api/employees/{employee_id}` - Delete employee

### Attendance
- `POST /api/attendance` - Mark attendance
- `GET /api/attendance/{employee_id}` - Get attendance (optional query: `?date=YYYY-MM-DD`)

### Auth
- `POST /api/auth/enter` - Validate shared superadmin key

### Health
- `GET /health`

## Local Setup

## 1) Prerequisites
- Python 3.12+ (recommended)
- Node 18+
- PostgreSQL 14+

## 2) Backend Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Update `DATABASE_URL` in `backend/.env` if needed.
Set `SUPERADMIN_KEY` in `backend/.env`.

Run migrations:

```bash
alembic upgrade head
```

Start backend:

```bash
uvicorn app.main:app --reload --port 8000
```

## 3) Frontend Setup

```bash
cd frontend
npm install
cp .env.example .env
```

Update `VITE_API_BASE_URL` in `frontend/.env` if needed.

Start frontend:

```bash
npm run dev
```

Frontend runs at `http://localhost:5173`.
When opening the UI, enter the shared superadmin key on the sign-in screen.

## Testing

The project includes:
- Backend unit tests (service-layer behavior)
- Backend integration tests (API endpoints with isolated test DB)
- Frontend feature/integration tests (page behavior with mocked API layer)

### Backend tests

```bash
cd backend
/opt/homebrew/bin/python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest
```

### Frontend tests

```bash
cd frontend
npm install
npm run test:run
```

Optional coverage:

```bash
cd frontend
npm run test:coverage
```

## Docker Setup (Optional)

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
docker compose up --build
```

## Deployment

### Backend (Render / Railway)

1. Create a PostgreSQL instance.
2. Set backend env vars:
   - `DATABASE_URL`
   - `APP_ENV=production`
   - `APP_DEBUG=false`
   - `CORS_ALLOWED_ORIGINS=["https://<your-frontend-domain>"]`
3. Build command:
   - `pip install -r requirements.txt`
4. Start command:
   - `gunicorn -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:$PORT`
5. Run DB migrations on deploy:
   - `alembic upgrade head`

### Frontend (Vercel / Netlify)

1. Set `VITE_API_BASE_URL=https://<your-backend-domain>`
2. Build command: `npm run build`
3. Publish directory: `dist`

## Design Notes

- Service layer contains business rules.
- Repository layer isolates DB access.
- API routers stay thin and delegate to services.
- Global exception handler standardizes error responses.
- Validation is implemented on both backend (Pydantic) and frontend.

## Assumptions / Limitations

- Authentication/authorization is not included in Lite scope.
- Attendance is unique per employee per date.
- Employee `employee_id` and `email` are globally unique.
- Dashboard is intentionally minimal.

## Production Hardening (Recommended Next)

- Add auth (JWT + RBAC for admin role)
- Add test suites (unit + integration + e2e)
- Add CI pipeline for lint/test/migrations
- Add structured logging and monitoring
- Add rate limiting and audit logs

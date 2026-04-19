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
- RabbitMQ (topic exchange event broker)
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
   hrmsctl-k8s.py

kubernetes/
  *.yaml
  README.md
```

## Unified Service Runner (SSH-safe)

Use the controller script to start/stop/status/scale both services together with platform selection via `-p`.

```bash
python3 scripts/hrmsctl.py <start|stop|status|scale> -p <docker|venv> [--build] [--wait] [--backend-instances N] [--frontend-instances N]
```

Examples:

```bash
python3 scripts/hrmsctl.py start -p docker --build --wait
python3 scripts/hrmsctl.py start -p docker --build --wait --backend-instances 2 --frontend-instances 2
python3 scripts/hrmsctl.py scale -p docker --backend-instances 3 --frontend-instances 4 --wait
python3 scripts/hrmsctl.py status -p docker
python3 scripts/hrmsctl.py stop -p docker

python3 scripts/hrmsctl.py start -p venv --wait
python3 scripts/hrmsctl.py status -p venv
python3 scripts/hrmsctl.py stop -p venv
```

Notes:
- `-p docker` uses `docker compose up -d` (optional `--build`) / `docker compose down`.
- Docker `start` and `scale` clamp frontend/backend replicas within configured min/max bounds.
- `-p venv` performs setup (venv, dependencies, migrations, frontend build), then starts backend/frontend detached.
- `--wait` blocks until health checks pass for backend/frontend.
- venv mode writes logs to `.runtime/logs/` and PID files to `.runtime/pids/`.
- Processes are launched detached and continue running after SSH disconnect.
- Docker mode URLs (through Nginx reverse proxy): frontend `http://<server-ip>:5173`, backend `http://<server-ip>:8001`.
- venv mode URLs: frontend `http://<server-ip>:5173`, backend `http://<server-ip>:8000`.

Environment overrides (optional):
- Root controller defaults can be placed in `.env` using `.env.example` as the template.
- `HRMS_HOST` (default: `127.0.0.1`)
- `HRMS_DOCKER_BACKEND_PORT` (default: `8001`)
- `HRMS_DOCKER_FRONTEND_PORT` (default: `5173`)
- `HRMS_VENV_BACKEND_PORT` (default: `8000`)
- `HRMS_VENV_FRONTEND_PORT` (default: `5173`)
- `HRMS_DOCKER_BACKEND_HEALTH_URL`, `HRMS_DOCKER_FRONTEND_URL`
- `HRMS_VENV_BACKEND_HEALTH_URL`, `HRMS_VENV_FRONTEND_URL`
- `HRMS_DOCKER_BACKEND_MIN_INSTANCES` (default: `1`)
- `HRMS_DOCKER_BACKEND_MAX_INSTANCES` (default: `4`)
- `HRMS_DOCKER_FRONTEND_MIN_INSTANCES` (default: `1`)
- `HRMS_DOCKER_FRONTEND_MAX_INSTANCES` (default: `4`)
- `HRMS_K8S_NAMESPACE` (default: `hrms-lite`)
- `HRMS_K8S_BACKEND_MIN_INSTANCES` (default: `2`)
- `HRMS_K8S_BACKEND_MAX_INSTANCES` (default: `6`)
- `HRMS_K8S_FRONTEND_MIN_INSTANCES` (default: `2`)
- `HRMS_K8S_FRONTEND_MAX_INSTANCES` (default: `6`)
- `HRMS_K8S_BACKEND_CPU_TARGET` (default: `70`)
- `HRMS_K8S_FRONTEND_CPU_TARGET` (default: `70`)
- `HRMS_K8S_BACKEND_CPU_THRESHOLD_MILLICORES` (default: `300`)
- `HRMS_K8S_FRONTEND_CPU_THRESHOLD_MILLICORES` (default: `200`)
- `HRMS_K8S_AUTOSCALE_MODE` (default: `cpu`)
- `HRMS_K8S_AUTOSCALE_INTERVAL_SECONDS` (default: `30`)
- `HRMS_K8S_RESPONSE_TIME_THRESHOLD_MS` (default: `700`)
- `HRMS_K8S_SCALE_STEP` (default: `1`)
- `HRMS_K8S_BACKEND_HEALTH_URL`, `HRMS_K8S_FRONTEND_URL`

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

### Swagger / OpenAPI

FastAPI auto-generates interactive API documentation. No extra setup required.

| Interface | Path | Description |
|-----------|------|-------------|
| Swagger UI | `/docs` | Interactive browser UI — try requests directly |
| ReDoc | `/redoc` | Clean read-only reference docs |
| OpenAPI JSON | `/openapi.json` | Raw schema for code generators / Postman import |

Access URLs by deployment mode:

| Mode | Swagger UI | ReDoc |
|------|------------|-------|
| venv (local) | `http://127.0.0.1:8000/docs` | `http://127.0.0.1:8000/redoc` |
| Docker (Nginx) | `http://127.0.0.1:8001/docs` | `http://127.0.0.1:8001/redoc` |
| Kubernetes (port-forward) | `http://127.0.0.1:8001/docs` | `http://127.0.0.1:8001/redoc` |

Start port-forward first when using Kubernetes:

```bash
python3 scripts/hrmsctl-k8s.py port-forward-start
```

Then open `http://127.0.0.1:8001/docs` in your browser.

> **Tip:** All protected endpoints in Swagger UI require the `X-Superadmin-Key` header.
> Click **Authorize** (lock icon) at the top of `/docs` and enter your key to authenticate all requests in the session.

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

Frontend runs at `http://<server-ip>:5173`.
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

### Selenium scalability smoke

For browser-level concurrency and UI scalability observation, use the Selenium runner:

```bash
/Users/vinaykumar/Desktop/interview-asignments/.venv/bin/pip install -r scripts/requirements-selenium.txt
/Users/vinaykumar/Desktop/interview-asignments/.venv/bin/python scripts/selenium_scalability_test.py \
   --base-url http://127.0.0.1:5173 \
   --superadmin-key <shared-key> \
   --users 10 \
   --loops 3 \
   --ramp-seconds 15 \
   --report-file .runtime/reports/selenium-scalability.json
```

To observe Kubernetes replica changes during the run:

```bash
/Users/vinaykumar/Desktop/interview-asignments/.venv/bin/python scripts/selenium_scalability_test.py \
   --base-url http://127.0.0.1:5173 \
   --superadmin-key <shared-key> \
   --users 10 \
   --loops 3 \
   --ramp-seconds 15 \
   --observe-k8s \
   --namespace hrms-lite \
   --report-file .runtime/reports/selenium-scalability.json
```

Notes:
- This is a browser-concurrency test, not a true high-throughput backend load test.
- For serious protocol-level load testing, use JMeter, Locust, or k6.
- Selenium requires a local Chrome or Chromium installation available to Selenium Manager.

## Docker Setup (Optional)

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
docker compose up --build
```

### Nginx Reverse Proxy + Load Balancing

`docker-compose.yml` includes an `nginx` service that acts as the public entrypoint and reverse proxy:

- `http://<server-ip>:5173` -> Nginx -> frontend service replicas
- `http://<server-ip>:8001` -> Nginx -> backend service replicas

The app containers are internal-only (`expose`) so Nginx is the only service publishing host ports.

RabbitMQ is also included for event-driven flows:

- AMQP: `localhost:5672`
- RabbitMQ Management UI: `http://localhost:15672` (default credentials: `guest` / `guest`)

### Scale Containers For Load Balancing

The controller supports bounded scaling for Docker services. Requested replica counts are clamped to the configured minimum and maximum instance values.

Example bounds:

```bash
export HRMS_DOCKER_BACKEND_MIN_INSTANCES=2
export HRMS_DOCKER_BACKEND_MAX_INSTANCES=6
export HRMS_DOCKER_FRONTEND_MIN_INSTANCES=2
export HRMS_DOCKER_FRONTEND_MAX_INSTANCES=8
```

Start at the minimum instance counts:

```bash
python3 scripts/hrmsctl.py start -p docker --build --wait
```

Request higher replica counts during traffic increases:

```bash
python3 scripts/hrmsctl.py scale -p docker --backend-instances 5 --frontend-instances 6 --wait
```

If a requested count falls outside the configured range, `hrmsctl` automatically clamps it to the nearest valid value.

Start with explicit replica counts:

```bash
docker compose up -d --build --scale frontend=3 --scale backend=3
```

Scale up/down at any time:

```bash
docker compose up -d --scale frontend=4 --scale backend=2
```

Check running replicas:

```bash
docker compose ps
```

Notes:
- Do not set `container_name` for services you plan to scale (already removed for frontend/backend).
- Database is stateful and normally kept as a single container unless you add a dedicated PostgreSQL replication setup.

## Kubernetes Deployment Model

The repository now includes a Kubernetes deployment model under [kubernetes/README.md](kubernetes/README.md) with:

- PostgreSQL, backend, frontend, and Nginx manifests
- CPU-based HorizontalPodAutoscaler resources for backend and frontend
- A dedicated controller script: `python3 scripts/hrmsctl-k8s.py <deploy|delete|status|scale|autoscale|port-forward-start|port-forward-stop|port-forward-status>`

Examples:

```bash
python3 scripts/hrmsctl-k8s.py deploy --wait
python3 scripts/hrmsctl-k8s.py port-forward-start
python3 scripts/hrmsctl-k8s.py port-forward-status
python3 scripts/hrmsctl-k8s.py autoscale --mode cpu
python3 scripts/hrmsctl-k8s.py autoscale --mode response-time
python3 scripts/hrmsctl-k8s.py port-forward-stop
```

Notes:
- Kubernetes is the implementation provided here for real autoscaling support.
- CPU-based autoscaling requires Metrics Server in the cluster.
- Response-time autoscaling requires the Nginx service to be reachable from the machine running `hrmsctl-k8s.py`, typically through `python3 scripts/hrmsctl-k8s.py port-forward-start`.

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

## Environment Variables

### Backend (Super Admin Key)

- `SUPERADMIN_KEY`  
  **Required.** The shared secret key for superadmin access.  
  Set this in `backend/.env`:
  ```dotenv
  SUPERADMIN_KEY=kjgdfhkgjhd-fjgkehslgjg
  ```

### Backend (RabbitMQ Event Broker)

- `RABBITMQ_URL` (default: `amqp://guest:guest@localhost:5672/`)
- `RABBITMQ_EXCHANGE` (default: `hrms.events`)
- `RABBITMQ_LISTENER_QUEUE` (default: `hrms.activity.listener`)
- `RABBITMQ_INTERNAL_TOPIC` (default: `internal.#`)
- `RABBITMQ_ACTIVITY_TOPIC` (default: `activity.#`)
- `RABBITMQ_RECONNECT_SECONDS` (default: `3`)
- `EVENT_PUBLISH_ENABLED` (default: `true`)
- `EVENT_LISTENER_ENABLED` (default: `true`)

Published topics follow a domain pattern:

- `internal.employee.created`
- `internal.employee.deleted`
- `internal.attendance.marked`
- `internal.attendance.updated`
- `activity.employee.created`
- `activity.employee.deleted`
- `activity.attendance.marked`
- `activity.attendance.updated`
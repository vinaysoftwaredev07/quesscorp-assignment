# Docker Operations Guide

This guide lists day-to-day Docker commands for HRMS Lite.

## 1. Prerequisites

```bash
cd /Users/vinaykumar/Desktop/interview-asignments
```

## 2. Preferred Control Commands (via hrmsctl)

Start stack (build + wait for health):

```bash
python3 scripts/hrmsctl.py start -p docker --build --wait
```

Start with explicit replicas:

```bash
python3 scripts/hrmsctl.py start -p docker --build --wait --backend-instances 2 --frontend-instances 2
```

Check status:

```bash
python3 scripts/hrmsctl.py status -p docker
```

Scale services:

```bash
python3 scripts/hrmsctl.py scale -p docker --backend-instances 3 --frontend-instances 4 --wait
```

Stop stack:

```bash
python3 scripts/hrmsctl.py stop -p docker
```

## 3. Direct Docker Compose Commands

Build images:

```bash
docker compose build
```

Start detached:

```bash
docker compose up -d
```

Start detached with build:

```bash
docker compose up -d --build
```

Scale during startup:

```bash
docker compose up -d --scale backend=3 --scale frontend=3
```

Scale running services:

```bash
docker compose up -d --scale backend=4 --scale frontend=2
```

List container status:

```bash
docker compose ps
docker ps
```

View logs:

```bash
docker compose logs -f
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f nginx
docker compose logs -f db
```

Restart one service:

```bash
docker compose restart backend
```

Stop and remove stack resources:

```bash
docker compose down
```

Stop and remove stack + volumes:

```bash
docker compose down -v
```

## 4. Health and Access Checks

Frontend via Nginx:

```bash
curl -i http://127.0.0.1:5173
```

Backend health via Nginx:

```bash
curl -i http://127.0.0.1:8001/health
```

Backend Swagger:

```bash
open http://127.0.0.1:8001/docs
```

## 5. Container Debugging

Enter backend container shell:

```bash
docker compose exec backend sh
```

Enter db container shell:

```bash
docker compose exec db sh
```

Check resource usage:

```bash
docker stats
```

Inspect one container:

```bash
docker inspect hrms_lite_db
```

## 6. Cleanup Commands

Remove stopped containers:

```bash
docker container prune -f
```

Remove dangling images:

```bash
docker image prune -f
```

Deep cleanup (unused images/networks/volumes):

```bash
docker system prune -a --volumes -f
```

## 7. Common Daily Workflow

```bash
cd /Users/vinaykumar/Desktop/interview-asignments
python3 scripts/hrmsctl.py start -p docker --build --wait
python3 scripts/hrmsctl.py status -p docker
python3 scripts/hrmsctl.py scale -p docker --backend-instances 3 --frontend-instances 3 --wait
python3 scripts/hrmsctl.py stop -p docker
```

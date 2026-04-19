# Kubernetes Deployment

This folder contains a Kubernetes-style deployment model for HRMS Lite with:

- PostgreSQL deployment and persistent volume claim
- RabbitMQ deployment and service for event-driven messaging
- Backend and frontend deployments and services
- Nginx reverse proxy service for ports 5173 and 8001
- HorizontalPodAutoscaler resources for backend and frontend

## Prerequisites

- A Kubernetes cluster
- `kubectl` configured for that cluster
- Metrics Server installed for CPU-based HPA and `kubectl top`
- Backend and frontend images available to the cluster:
  - `interview-asignments-backend:latest`
  - `interview-asignments-frontend:latest`

For local clusters, load the images after building them:

```bash
docker compose build backend frontend
```

Examples:

```bash
kind load docker-image interview-asignments-backend:latest interview-asignments-frontend:latest
```

```bash
minikube image load interview-asignments-backend:latest interview-asignments-frontend:latest
```

## Secrets

Update `secrets.template.yaml` before deploying, especially:

- `POSTGRES_PASSWORD`
- `SUPERADMIN_KEY`

## Deploy

```bash
python3 scripts/hrmsctl-k8s.py deploy --wait
```

## Access

Port-forward the Nginx service:

```bash
kubectl port-forward -n hrms-lite service/hrms-nginx 5173:5173 8001:8001
```

Then open:

- Frontend: `http://127.0.0.1:5173`
- Backend: `http://127.0.0.1:8001`

## Scale

```bash
python3 scripts/hrmsctl-k8s.py scale --backend-instances 3 --frontend-instances 4 --wait
```

## Autoscale Loop

CPU-based loop:

```bash
python3 scripts/hrmsctl-k8s.py autoscale --mode cpu
```

Response-time loop:

```bash
python3 scripts/hrmsctl-k8s.py autoscale --mode response-time
```

The loop respects the min/max replica bounds defined in the root `.env` file.

## Remove

```bash
python3 scripts/hrmsctl-k8s.py delete
```

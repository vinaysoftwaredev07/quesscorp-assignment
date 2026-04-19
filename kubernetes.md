# Kubernetes Operations Guide

This guide lists day-to-day Kubernetes commands for HRMS Lite.

## 1. Prerequisites

```bash
cd /Users/vinaykumar/Desktop/interview-asignments
kubectl config current-context
kubectl get nodes
```

Build/load images for local clusters when needed:

```bash
docker compose build backend frontend
minikube image load interview-asignments-backend:latest interview-asignments-frontend:latest
```

## 2. Preferred Control Commands (via hrmsctl-k8s)

Deploy all resources:

```bash
python3 scripts/hrmsctl-k8s.py deploy --wait
```

Status check:

```bash
python3 scripts/hrmsctl-k8s.py status
```

Scale backend/frontend:

```bash
python3 scripts/hrmsctl-k8s.py scale --backend-instances 3 --frontend-instances 4 --wait
```

Run autoscaling loop (CPU mode):

```bash
python3 scripts/hrmsctl-k8s.py autoscale --mode cpu
```

Run autoscaling loop (response-time mode):

```bash
python3 scripts/hrmsctl-k8s.py autoscale --mode response-time
```

Stop workloads (scale deployments to 0, keep resources):

```bash
python3 scripts/hrmsctl-k8s.py stop
```

Delete all resources:

```bash
python3 scripts/hrmsctl-k8s.py delete
```

## 3. Access Commands

Managed port-forward (recommended):

```bash
python3 scripts/hrmsctl-k8s.py port-forward-start
python3 scripts/hrmsctl-k8s.py port-forward-status
python3 scripts/hrmsctl-k8s.py port-forward-stop
```

Manual port-forward:

```bash
kubectl port-forward -n hrms-lite service/hrms-nginx 5173:5173 8001:8001
```

Access URLs:

```text
Frontend: http://127.0.0.1:5173
Backend:  http://127.0.0.1:8001
Swagger:  http://127.0.0.1:8001/docs
```

## 4. Namespace and Resource Checks

```bash
kubectl get ns
kubectl get all -n hrms-lite
kubectl get deployments,hpa,services,pods -n hrms-lite
kubectl get events -n hrms-lite --sort-by=.metadata.creationTimestamp
```

RabbitMQ service checks:

```bash
kubectl get svc hrms-rabbitmq -n hrms-lite
kubectl port-forward -n hrms-lite service/hrms-rabbitmq 15672:15672 5672:5672
```

Describe resources:

```bash
kubectl describe deployment hrms-backend -n hrms-lite
kubectl describe deployment hrms-frontend -n hrms-lite
kubectl describe pod <pod-name> -n hrms-lite
```

## 5. Logs and Debugging

Tail deployment logs:

```bash
kubectl logs -n hrms-lite deployment/hrms-backend -f
kubectl logs -n hrms-lite deployment/hrms-frontend -f
kubectl logs -n hrms-lite deployment/hrms-nginx -f
```

Logs for a specific pod:

```bash
kubectl logs -n hrms-lite <pod-name> -f
```

Shell into pod container:

```bash
kubectl exec -it -n hrms-lite deploy/hrms-backend -- sh
kubectl exec -it -n hrms-lite deploy/hrms-frontend -- sh
```

Restart a deployment:

```bash
kubectl rollout restart deployment/hrms-backend -n hrms-lite
kubectl rollout restart deployment/hrms-frontend -n hrms-lite
```

Watch rollout status:

```bash
kubectl rollout status deployment/hrms-backend -n hrms-lite
kubectl rollout status deployment/hrms-frontend -n hrms-lite
```

## 6. Metrics and Autoscaling Visibility

```bash
kubectl top pods -n hrms-lite
kubectl top nodes
kubectl get hpa -n hrms-lite
kubectl describe hpa hrms-backend-hpa -n hrms-lite
kubectl describe hpa hrms-frontend-hpa -n hrms-lite
```

## 7. Cleanup and Recovery

Delete one deployment only:

```bash
kubectl delete deployment hrms-backend -n hrms-lite
```

Delete full namespace:

```bash
kubectl delete namespace hrms-lite
```

If namespace is stuck terminating:

```bash
kubectl get namespace hrms-lite -o json > /tmp/hrms-lite-ns.json
# Edit /tmp/hrms-lite-ns.json and set: "spec": {"finalizers": []}
kubectl replace --raw /api/v1/namespaces/hrms-lite/finalize -f /tmp/hrms-lite-ns.json
```

## 8. Common Daily Workflow

```bash
cd /Users/vinaykumar/Desktop/interview-asignments
python3 scripts/hrmsctl-k8s.py deploy --wait
python3 scripts/hrmsctl-k8s.py port-forward-start
python3 scripts/hrmsctl-k8s.py status
python3 scripts/hrmsctl-k8s.py scale --backend-instances 3 --frontend-instances 3 --wait
python3 scripts/hrmsctl-k8s.py port-forward-stop
python3 scripts/hrmsctl-k8s.py stop
```

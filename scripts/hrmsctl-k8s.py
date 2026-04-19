#!/usr/bin/env python3
"""HRMS Lite Kubernetes controller.

Deploys the application to Kubernetes, updates HPA bounds, and can run a simple
control loop that scales backend/frontend deployments based on pod CPU usage or
HTTP response time.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen

ROOT_DIR = Path(__file__).resolve().parents[1]
K8S_DIR = ROOT_DIR / "kubernetes"
RUNTIME_DIR = ROOT_DIR / ".runtime"
K8S_RUNTIME_DIR = RUNTIME_DIR / "k8s"
K8S_PORT_FORWARD_PID_FILE = K8S_RUNTIME_DIR / "port-forward.pid"
K8S_PORT_FORWARD_LOG_FILE = K8S_RUNTIME_DIR / "port-forward.log"


def load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env_file(ROOT_DIR / ".env")


def env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


K8S_NAMESPACE = os.getenv("HRMS_K8S_NAMESPACE", "hrms-lite")
K8S_BACKEND_MIN_INSTANCES = env_int("HRMS_K8S_BACKEND_MIN_INSTANCES", 1)
K8S_BACKEND_MAX_INSTANCES = env_int("HRMS_K8S_BACKEND_MAX_INSTANCES", 10)
K8S_FRONTEND_MIN_INSTANCES = env_int("HRMS_K8S_FRONTEND_MIN_INSTANCES", 1)
K8S_FRONTEND_MAX_INSTANCES = env_int("HRMS_K8S_FRONTEND_MAX_INSTANCES", 10)
K8S_BACKEND_CPU_TARGET = env_int("HRMS_K8S_BACKEND_CPU_TARGET", 75)
K8S_FRONTEND_CPU_TARGET = env_int("HRMS_K8S_FRONTEND_CPU_TARGET", 75)
K8S_AUTOSCALE_MODE = os.getenv("HRMS_K8S_AUTOSCALE_MODE", "cpu")
K8S_AUTOSCALE_INTERVAL_SECONDS = env_int("HRMS_K8S_AUTOSCALE_INTERVAL_SECONDS", 30)
K8S_RESPONSE_TIME_THRESHOLD_MS = env_int("HRMS_K8S_RESPONSE_TIME_THRESHOLD_MS", 700)
K8S_SCALE_STEP = env_int("HRMS_K8S_SCALE_STEP", 1)
K8S_BACKEND_HEALTH_URL = os.getenv("HRMS_K8S_BACKEND_HEALTH_URL", "http://127.0.0.1:8001/health")
K8S_FRONTEND_URL = os.getenv("HRMS_K8S_FRONTEND_URL", "http://127.0.0.1:5173")
K8S_LOCAL_FRONTEND_PORT = env_int("HRMS_K8S_LOCAL_FRONTEND_PORT", 5173)
K8S_LOCAL_BACKEND_PORT = env_int("HRMS_K8S_LOCAL_BACKEND_PORT", 8001)
K8S_LOCAL_FRONTEND_URL = f"http://127.0.0.1:{K8S_LOCAL_FRONTEND_PORT}"
K8S_LOCAL_BACKEND_HEALTH_URL = f"http://127.0.0.1:{K8S_LOCAL_BACKEND_PORT}/health"

BACKEND_DEPLOYMENT = "hrms-backend"
FRONTEND_DEPLOYMENT = "hrms-frontend"
NGINX_DEPLOYMENT = "hrms-nginx"
POSTGRES_DEPLOYMENT = "hrms-postgres"
BACKEND_HPA = "hrms-backend-hpa"
FRONTEND_HPA = "hrms-frontend-hpa"


def run_command(
    command: list[str],
    *,
    cwd: Path | None = None,
    capture_output: bool = False,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        text=True,
        check=check,
        capture_output=capture_output,
    )


def ensure_runtime_dirs() -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    K8S_RUNTIME_DIR.mkdir(parents=True, exist_ok=True)


def read_pid(path: Path) -> int | None:
    if not path.exists():
        return None
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except ValueError:
        return None


def write_pid(path: Path, pid: int) -> None:
    path.write_text(str(pid), encoding="utf-8")


def remove_pid(path: Path) -> None:
    if path.exists():
        path.unlink()


def is_process_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


_CLUSTER_CONNECT_ERRORS = (
    "connection refused",
    "no such host",
    "was refused",
    "no server found",
    "unable to connect",
    "dial tcp",
)

_CLUSTER_SETUP_HINT = """
[hrmsctl-k8s] No Kubernetes cluster is reachable.

Quick-start options (choose one):
  1) Docker Desktop  – Settings -> Kubernetes -> Enable Kubernetes -> Apply
     Then: kubectl config use-context docker-desktop

  2) minikube        – brew install minikube
     minikube start --driver=docker

  3) kind            – brew install kind
     kind create cluster --name hrms

After the cluster is up, re-run:
  kubectl get nodes
  python3 scripts/hrmsctl-k8s.py deploy --wait
"""


def assert_cluster_reachable() -> None:
    result = run_command(
        ["kubectl", "cluster-info"],
        capture_output=True,
        check=False,
    )
    combined = (result.stdout + result.stderr).lower()
    if result.returncode != 0 or any(err in combined for err in _CLUSTER_CONNECT_ERRORS):
        print(_CLUSTER_SETUP_HINT, file=sys.stderr)
        raise SystemExit(1)


def kubectl(args: list[str], *, capture_output: bool = False, check: bool = True) -> subprocess.CompletedProcess[str]:
    return run_command(["kubectl", *args], capture_output=capture_output, check=check)


def kubectl_json(args: list[str]) -> dict:
    result = kubectl([*args, "-o", "json"], capture_output=True)
    return json.loads(result.stdout)


def validate_instance_bounds(service: str, minimum: int, maximum: int) -> None:
    if minimum < 1:
        raise ValueError(f"{service} minimum instances must be at least 1")
    if maximum < minimum:
        raise ValueError(f"{service} maximum instances must be greater than or equal to minimum instances")


def clamp_instance_count(service: str, requested: int, minimum: int, maximum: int) -> int:
    validate_instance_bounds(service, minimum, maximum)
    if requested < minimum:
        print(f"[hrmsctl-k8s] Requested {service} instances {requested} is below minimum {minimum}; using {minimum}.")
        return minimum
    if requested > maximum:
        print(f"[hrmsctl-k8s] Requested {service} instances {requested} exceeds maximum {maximum}; using {maximum}.")
        return maximum
    return requested


def current_replicas(deployment_name: str) -> int:
    deployment = kubectl_json(["get", "deployment", deployment_name, "-n", K8S_NAMESPACE])
    return int(deployment["spec"].get("replicas", 1))


def patch_hpa(name: str, minimum: int, maximum: int, cpu_target: int) -> None:
    payload = {
        "spec": {
            "minReplicas": minimum,
            "maxReplicas": maximum,
            "metrics": [
                {
                    "type": "Resource",
                    "resource": {
                        "name": "cpu",
                        "target": {
                            "type": "Utilization",
                            "averageUtilization": cpu_target,
                        },
                    },
                }
            ],
        }
    }
    kubectl(
        [
            "patch",
            "hpa",
            name,
            "-n",
            K8S_NAMESPACE,
            "--type",
            "merge",
            "-p",
            json.dumps(payload),
        ]
    )


def scale_deployment(name: str, replicas: int) -> None:
    kubectl(["scale", "deployment", name, "-n", K8S_NAMESPACE, f"--replicas={replicas}"])


def wait_for_rollout(name: str, timeout_seconds: int = 180) -> None:
    kubectl(
        [
            "rollout",
            "status",
            "deployment",
            name,
            "-n",
            K8S_NAMESPACE,
            f"--timeout={timeout_seconds}s",
        ]
    )


def wait_for_http(url: str, timeout_seconds: int = 120) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with urlopen(Request(url, method="GET"), timeout=5) as response:
                if 200 <= response.status < 500:
                    return True
        except Exception:
            time.sleep(1)
    return False


def measure_response_time_ms(url: str) -> float:
    start = time.perf_counter()
    try:
        with urlopen(Request(url, method="GET"), timeout=5) as response:
            if response.status >= 500:
                raise RuntimeError(f"Request to {url} returned HTTP {response.status}")
    except Exception as exc:
        raise RuntimeError(
            "Response-time autoscaling requires reachable local endpoints. "
            "Run: kubectl port-forward -n hrms-lite service/hrms-nginx 5173:5173 8001:8001"
        ) from exc
    return (time.perf_counter() - start) * 1000


def parse_cpu_value(raw_value: str) -> int:
    value = raw_value.strip()
    if value.endswith("m"):
        return int(value[:-1])
    return int(float(value) * 1000)


def requested_cpu_millicores(deployment_name: str) -> int:
    deployment = kubectl_json(["get", "deployment", deployment_name, "-n", K8S_NAMESPACE])
    containers = deployment["spec"]["template"]["spec"].get("containers", [])
    total_requested_cpu = 0

    for container in containers:
        requests = container.get("resources", {}).get("requests", {})
        cpu_request = requests.get("cpu")
        if cpu_request:
            total_requested_cpu += parse_cpu_value(cpu_request)

    if total_requested_cpu <= 0:
        raise RuntimeError(f"Deployment {deployment_name} does not define CPU requests")

    return total_requested_cpu


def average_cpu_millicores(component: str) -> int:
    result = kubectl(
        [
            "top",
            "pods",
            "-n",
            K8S_NAMESPACE,
            f"--selector=app.kubernetes.io/component={component}",
            "--no-headers",
        ],
        capture_output=True,
    )
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    if not lines:
        raise RuntimeError(
            f"No CPU metrics returned for {component}. Ensure metrics-server is installed and pods are running."
        )

    cpu_values = []
    for line in lines:
        parts = line.split()
        if len(parts) < 2:
            continue
        cpu_values.append(parse_cpu_value(parts[1]))

    if not cpu_values:
        raise RuntimeError(f"Unable to parse CPU metrics for {component}")
    return sum(cpu_values) // len(cpu_values)


def average_cpu_utilization_percent(component: str, deployment_name: str) -> float:
    average_cpu = average_cpu_millicores(component)
    requested_cpu = requested_cpu_millicores(deployment_name)
    return (average_cpu / requested_cpu) * 100


def print_access_instructions() -> None:
    print(
        "[hrmsctl-k8s] Access services with: "
        f"python3 scripts/hrmsctl-k8s.py port-forward-start "
        f"(local ports {K8S_LOCAL_FRONTEND_PORT}/{K8S_LOCAL_BACKEND_PORT})"
    )


def port_forward_status() -> bool:
    pid = read_pid(K8S_PORT_FORWARD_PID_FILE)
    if not pid:
        if wait_for_http(K8S_LOCAL_FRONTEND_URL, timeout_seconds=1) and wait_for_http(
            K8S_LOCAL_BACKEND_HEALTH_URL,
            timeout_seconds=1,
        ):
            print(
                "[hrmsctl-k8s] Port-forward: active (externally managed process, "
                "no hrmsctl-k8s PID file)."
            )
            return True
        print("[hrmsctl-k8s] Port-forward: stopped (no PID file).")
        return False

    if not is_process_running(pid):
        if wait_for_http(K8S_LOCAL_FRONTEND_URL, timeout_seconds=1) and wait_for_http(
            K8S_LOCAL_BACKEND_HEALTH_URL,
            timeout_seconds=1,
        ):
            print(
                "[hrmsctl-k8s] Port-forward: active (externally managed process, "
                f"stale hrmsctl-k8s PID {pid} cleaned)."
            )
            remove_pid(K8S_PORT_FORWARD_PID_FILE)
            return True
        print(f"[hrmsctl-k8s] Port-forward: stopped (stale PID {pid}).")
        remove_pid(K8S_PORT_FORWARD_PID_FILE)
        return False

    print(
        f"[hrmsctl-k8s] Port-forward: running (PID {pid}) | "
        f"ports {K8S_LOCAL_FRONTEND_PORT}->{K8S_LOCAL_FRONTEND_PORT}, "
        f"{K8S_LOCAL_BACKEND_PORT}->{K8S_LOCAL_BACKEND_PORT} | "
        f"logs: {K8S_PORT_FORWARD_LOG_FILE}"
    )
    return True


def start_port_forward(wait: bool = True) -> None:
    assert_cluster_reachable()
    ensure_runtime_dirs()

    if port_forward_status():
        return

    if wait_for_http(K8S_LOCAL_FRONTEND_URL, timeout_seconds=1) and wait_for_http(
        K8S_LOCAL_BACKEND_HEALTH_URL,
        timeout_seconds=1,
    ):
        print(
            "[hrmsctl-k8s] Port-forward appears active from another process; "
            "reusing current localhost endpoints."
        )
        return

    command = [
        "kubectl",
        "port-forward",
        "-n",
        K8S_NAMESPACE,
        "service/hrms-nginx",
        f"{K8S_LOCAL_FRONTEND_PORT}:{K8S_LOCAL_FRONTEND_PORT}",
        f"{K8S_LOCAL_BACKEND_PORT}:{K8S_LOCAL_BACKEND_PORT}",
    ]

    with K8S_PORT_FORWARD_LOG_FILE.open("ab") as log_handle:
        process = subprocess.Popen(
            command,
            stdout=log_handle,
            stderr=log_handle,
            stdin=subprocess.DEVNULL,
            preexec_fn=os.setsid,
        )

    write_pid(K8S_PORT_FORWARD_PID_FILE, process.pid)
    print(f"[hrmsctl-k8s] Port-forward started (PID {process.pid}).")

    # Detect immediate failures (for example, local port already in use).
    time.sleep(1)
    if not is_process_running(process.pid):
        remove_pid(K8S_PORT_FORWARD_PID_FILE)
        tail = ""
        if K8S_PORT_FORWARD_LOG_FILE.exists():
            lines = K8S_PORT_FORWARD_LOG_FILE.read_text(encoding="utf-8", errors="ignore").splitlines()
            tail = "\n".join(lines[-8:])
        raise RuntimeError(
            "Port-forward process exited immediately. "
            f"Check ports {K8S_LOCAL_FRONTEND_PORT}/{K8S_LOCAL_BACKEND_PORT} availability. "
            f"Recent logs:\n{tail}"
        )

    if wait:
        frontend_ready = wait_for_http(K8S_LOCAL_FRONTEND_URL, timeout_seconds=15)
        backend_ready = wait_for_http(K8S_LOCAL_BACKEND_HEALTH_URL, timeout_seconds=15)
        if not (frontend_ready and backend_ready):
            raise RuntimeError(
                "Port-forward started but local endpoints are not reachable. "
                f"Check logs: {K8S_PORT_FORWARD_LOG_FILE}"
            )


def stop_port_forward() -> None:
    pid = read_pid(K8S_PORT_FORWARD_PID_FILE)
    if not pid:
        print("[hrmsctl-k8s] Port-forward already stopped.")
        return

    if not is_process_running(pid):
        print(f"[hrmsctl-k8s] Port-forward PID {pid} is not running; cleaning PID file.")
        remove_pid(K8S_PORT_FORWARD_PID_FILE)
        return

    print(f"[hrmsctl-k8s] Stopping port-forward (PID {pid})...")
    os.killpg(os.getpgid(pid), signal.SIGTERM)
    remove_pid(K8S_PORT_FORWARD_PID_FILE)
    print("[hrmsctl-k8s] Port-forward stopped.")


def deploy(wait: bool) -> None:
    assert_cluster_reachable()
    print("[hrmsctl-k8s] Applying Kubernetes manifests...")
    kubectl(["apply", "-k", str(K8S_DIR)])
    patch_hpa(BACKEND_HPA, K8S_BACKEND_MIN_INSTANCES, K8S_BACKEND_MAX_INSTANCES, K8S_BACKEND_CPU_TARGET)
    patch_hpa(FRONTEND_HPA, K8S_FRONTEND_MIN_INSTANCES, K8S_FRONTEND_MAX_INSTANCES, K8S_FRONTEND_CPU_TARGET)
    scale_deployment(BACKEND_DEPLOYMENT, K8S_BACKEND_MIN_INSTANCES)
    scale_deployment(FRONTEND_DEPLOYMENT, K8S_FRONTEND_MIN_INSTANCES)

    if wait:
        wait_for_rollout(POSTGRES_DEPLOYMENT)
        wait_for_rollout(BACKEND_DEPLOYMENT)
        wait_for_rollout(FRONTEND_DEPLOYMENT)
        wait_for_rollout(NGINX_DEPLOYMENT)

    print("[hrmsctl-k8s] Kubernetes resources applied.")
    print_scaling_bounds()
    print_access_instructions()


def _scale_to_zero() -> None:
    """Gracefully scale all deployments to 0 so pods start terminating immediately."""
    for name in ("hrms-backend", "hrms-frontend"):
        result = subprocess.run(
            ["kubectl", "scale", "deployment", name, "-n", K8S_NAMESPACE, "--replicas=0"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print(f"[hrmsctl-k8s] Scaled {name} to 0.")


def _wait_for_pods_gone(timeout: int = 60) -> bool:
    """Wait up to *timeout* seconds for all pods in the namespace to terminate."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = subprocess.run(
            ["kubectl", "get", "pods", "-n", K8S_NAMESPACE, "--no-headers"],
            capture_output=True,
            text=True,
        )
        # namespace gone or no pods remaining
        if result.returncode != 0 or result.stdout.strip() == "":
            return True
        print("[hrmsctl-k8s] Waiting for pods to terminate...", flush=True)
        time.sleep(3)
    return False


def _force_clean_docker_containers() -> None:
    """Force-remove any lingering Docker containers that were managed by this K8s namespace."""
    try:
        result = subprocess.run(
            ["docker", "ps", "-a", "--filter", f"name=k8s_", "--format", "{{.ID}}\t{{.Names}}"],
            capture_output=True,
            text=True,
        )
        containers = [
            line.split("\t")[0]
            for line in result.stdout.splitlines()
            if K8S_NAMESPACE in line
        ]
        if not containers:
            return
        print(f"[hrmsctl-k8s] Force-removing {len(containers)} lingering container(s)...")
        subprocess.run(["docker", "rm", "-f", *containers], capture_output=True)
        print("[hrmsctl-k8s] Lingering containers removed.")
    except FileNotFoundError:
        pass  # docker not available


def stop() -> None:
    """Scale all deployments to 0 (pause) without deleting the Kubernetes resources."""
    assert_cluster_reachable()
    print("[hrmsctl-k8s] Scaling all deployments to 0 (stop without delete)...")
    _scale_to_zero()
    gone = _wait_for_pods_gone(timeout=60)
    if gone:
        print("[hrmsctl-k8s] All pods terminated. Resources still exist — run 'deploy' to bring back up.")
    else:
        print("[hrmsctl-k8s] Pods still terminating. They will complete on their own.")
        print("[hrmsctl-k8s] NOTE: Do not use 'docker rm/stop' on k8s_ containers — the kubelet will restart them.")
        print("[hrmsctl-k8s] Run 'delete' to fully remove all resources and force-clean containers.")


def delete() -> None:
    assert_cluster_reachable()
    # Step 1: scale to 0 so pods get a graceful SIGTERM before namespace deletion
    print("[hrmsctl-k8s] Scaling deployments to 0 for graceful shutdown...")
    _scale_to_zero()
    time.sleep(2)
    # Step 2: delete all K8s manifests (including namespace)
    print("[hrmsctl-k8s] Deleting Kubernetes manifests...")
    kubectl(["delete", "-k", str(K8S_DIR), "--ignore-not-found=true"])
    print("[hrmsctl-k8s] Kubernetes resources deleted.")
    # Step 3: wait for pods to terminate naturally
    gone = _wait_for_pods_gone(timeout=45)
    # Step 4: force-clean any Docker containers that are still running
    if not gone:
        print("[hrmsctl-k8s] Timeout waiting for pods — force-cleaning Docker containers...")
    _force_clean_docker_containers()
    print("[hrmsctl-k8s] All resources removed.")


def status() -> None:
    assert_cluster_reachable()
    kubectl(["get", "deployments,hpa,services,pods", "-n", K8S_NAMESPACE], check=False)
    print_scaling_bounds()
    print_access_instructions()
    port_forward_status()


def print_scaling_bounds() -> None:
    print(
        "[hrmsctl-k8s] Scaling bounds: "
        f"backend={K8S_BACKEND_MIN_INSTANCES}-{K8S_BACKEND_MAX_INSTANCES}, "
        f"frontend={K8S_FRONTEND_MIN_INSTANCES}-{K8S_FRONTEND_MAX_INSTANCES}"
    )


def resolve_desired_scale(requested: int | None, current: int, minimum: int, maximum: int, service: str) -> int:
    if requested is None:
        return current
    return clamp_instance_count(service, requested, minimum, maximum)


def scale(backend_instances: int | None, frontend_instances: int | None, wait: bool) -> None:
    assert_cluster_reachable()
    backend_target = resolve_desired_scale(
        backend_instances,
        current_replicas(BACKEND_DEPLOYMENT),
        K8S_BACKEND_MIN_INSTANCES,
        K8S_BACKEND_MAX_INSTANCES,
        "backend",
    )
    frontend_target = resolve_desired_scale(
        frontend_instances,
        current_replicas(FRONTEND_DEPLOYMENT),
        K8S_FRONTEND_MIN_INSTANCES,
        K8S_FRONTEND_MAX_INSTANCES,
        "frontend",
    )

    print("[hrmsctl-k8s] Scaling Kubernetes deployments...")
    scale_deployment(BACKEND_DEPLOYMENT, backend_target)
    scale_deployment(FRONTEND_DEPLOYMENT, frontend_target)

    if wait:
        wait_for_rollout(BACKEND_DEPLOYMENT)
        wait_for_rollout(FRONTEND_DEPLOYMENT)

    print("[hrmsctl-k8s] Deployments scaled.")
    print_scaling_bounds()
    print_access_instructions()


def autoscale_target(current: int, metric: float, threshold: float, minimum: int, maximum: int) -> int:
    if metric >= threshold:
        return min(maximum, current + K8S_SCALE_STEP)
    if metric <= threshold * 0.5:
        return max(minimum, current - K8S_SCALE_STEP)
    return current


def autoscale_by_cpu(wait: bool) -> tuple[int, int]:
    backend_current = current_replicas(BACKEND_DEPLOYMENT)
    frontend_current = current_replicas(FRONTEND_DEPLOYMENT)

    backend_cpu_utilization = average_cpu_utilization_percent("backend", BACKEND_DEPLOYMENT)
    frontend_cpu_utilization = average_cpu_utilization_percent("frontend", FRONTEND_DEPLOYMENT)

    backend_target = autoscale_target(
        backend_current,
        backend_cpu_utilization,
        float(K8S_BACKEND_CPU_TARGET),
        K8S_BACKEND_MIN_INSTANCES,
        K8S_BACKEND_MAX_INSTANCES,
    )
    frontend_target = autoscale_target(
        frontend_current,
        frontend_cpu_utilization,
        float(K8S_FRONTEND_CPU_TARGET),
        K8S_FRONTEND_MIN_INSTANCES,
        K8S_FRONTEND_MAX_INSTANCES,
    )

    print(
        "[hrmsctl-k8s] CPU metrics: "
        f"backend={backend_cpu_utilization:.1f}% target={backend_target}, "
        f"frontend={frontend_cpu_utilization:.1f}% target={frontend_target}"
    )
    apply_autoscale_targets(backend_current, frontend_current, backend_target, frontend_target, wait)
    return backend_target, frontend_target


def autoscale_by_response_time(wait: bool) -> tuple[int, int]:
    backend_current = current_replicas(BACKEND_DEPLOYMENT)
    frontend_current = current_replicas(FRONTEND_DEPLOYMENT)

    backend_response_ms = measure_response_time_ms(K8S_BACKEND_HEALTH_URL)
    frontend_response_ms = measure_response_time_ms(K8S_FRONTEND_URL)

    backend_target = autoscale_target(
        backend_current,
        backend_response_ms,
        float(K8S_RESPONSE_TIME_THRESHOLD_MS),
        K8S_BACKEND_MIN_INSTANCES,
        K8S_BACKEND_MAX_INSTANCES,
    )
    frontend_target = autoscale_target(
        frontend_current,
        frontend_response_ms,
        float(K8S_RESPONSE_TIME_THRESHOLD_MS),
        K8S_FRONTEND_MIN_INSTANCES,
        K8S_FRONTEND_MAX_INSTANCES,
    )

    print(
        "[hrmsctl-k8s] Response times: "
        f"backend={backend_response_ms:.0f}ms target={backend_target}, "
        f"frontend={frontend_response_ms:.0f}ms target={frontend_target}"
    )
    apply_autoscale_targets(backend_current, frontend_current, backend_target, frontend_target, wait)
    return backend_target, frontend_target


def apply_autoscale_targets(
    backend_current: int,
    frontend_current: int,
    backend_target: int,
    frontend_target: int,
    wait: bool,
) -> None:
    if backend_target != backend_current:
        scale_deployment(BACKEND_DEPLOYMENT, backend_target)
        if wait:
            wait_for_rollout(BACKEND_DEPLOYMENT)

    if frontend_target != frontend_current:
        scale_deployment(FRONTEND_DEPLOYMENT, frontend_target)
        if wait:
            wait_for_rollout(FRONTEND_DEPLOYMENT)


def autoscale(mode: str, wait: bool, iterations: int | None) -> None:
    assert_cluster_reachable()
    selected_mode = mode or K8S_AUTOSCALE_MODE
    if selected_mode not in {"cpu", "response-time"}:
        raise ValueError("Autoscale mode must be 'cpu' or 'response-time'")

    print(f"[hrmsctl-k8s] Starting autoscale loop in {selected_mode} mode...")
    print_scaling_bounds()
    print_access_instructions()

    completed = 0
    try:
        while iterations is None or completed < iterations:
            if selected_mode == "cpu":
                try:
                    autoscale_by_cpu(wait)
                except subprocess.CalledProcessError as exc:
                    stderr = (exc.stderr or "").lower()
                    if "metrics api not available" in stderr:
                        print(
                            "[hrmsctl-k8s] Metrics API not available; switching autoscale mode "
                            "to response-time for this run."
                        )
                        print(
                            "[hrmsctl-k8s] To restore CPU mode, install metrics-server and verify with: "
                            "kubectl top pods -n hrms-lite"
                        )
                        selected_mode = "response-time"
                        autoscale_by_response_time(wait)
                    else:
                        raise
            else:
                autoscale_by_response_time(wait)
            completed += 1
            if iterations is None or completed < iterations:
                time.sleep(K8S_AUTOSCALE_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print("\n[hrmsctl-k8s] Autoscale loop stopped.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="HRMS Lite Kubernetes controller")
    parser.add_argument(
        "action",
        choices=[
            "deploy",
            "stop",
            "delete",
            "status",
            "scale",
            "autoscale",
            "port-forward-start",
            "port-forward-stop",
            "port-forward-status",
        ],
        help="Action to perform (stop=scale to 0, delete=remove all resources)",
    )
    parser.add_argument("--wait", action="store_true", help="Wait for rollouts after deploy or scaling")
    parser.add_argument("--backend-instances", type=int, help="Desired backend replica count")
    parser.add_argument("--frontend-instances", type=int, help="Desired frontend replica count")
    parser.add_argument("--mode", choices=["cpu", "response-time"], default=K8S_AUTOSCALE_MODE, help="Autoscale loop mode")
    parser.add_argument("--iterations", type=int, help="Run autoscale loop for a fixed number of iterations")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        if args.action == "deploy":
            deploy(wait=args.wait)
        elif args.action == "stop":
            stop()
        elif args.action == "delete":
            delete()
        elif args.action == "status":
            status()
        elif args.action == "port-forward-start":
            start_port_forward(wait=True)
        elif args.action == "port-forward-stop":
            stop_port_forward()
        elif args.action == "port-forward-status":
            port_forward_status()
        elif args.action == "scale":
            scale(
                backend_instances=args.backend_instances,
                frontend_instances=args.frontend_instances,
                wait=args.wait,
            )
        else:
            autoscale(mode=args.mode, wait=args.wait, iterations=args.iterations)
    except subprocess.CalledProcessError as exc:
        print(f"[hrmsctl-k8s] Command failed with exit code {exc.returncode}: {exc.cmd}", file=sys.stderr)
        if exc.stderr:
            print(exc.stderr, file=sys.stderr)
        return exc.returncode
    except Exception as exc:
        print(f"[hrmsctl-k8s] Unexpected error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

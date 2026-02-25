#!/usr/bin/env python3
"""HRMS Lite service controller.

Supports launching both backend and frontend either with Docker or directly on host
(using Python venv + npm), while ensuring processes keep running after SSH disconnect.
"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
from urllib.request import Request, urlopen
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
RUNTIME_DIR = ROOT_DIR / ".runtime"
LOG_DIR = RUNTIME_DIR / "logs"
PID_DIR = RUNTIME_DIR / "pids"

BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"
BACKEND_VENV_DIRNAME = ".venv"

BACKEND_PID_FILE = PID_DIR / "backend.pid"
FRONTEND_PID_FILE = PID_DIR / "frontend.pid"

BACKEND_LOG_FILE = LOG_DIR / "backend.log"
FRONTEND_LOG_FILE = LOG_DIR / "frontend.log"

def env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


HRMS_HOST = os.getenv("HRMS_HOST", "127.0.0.1")

DOCKER_BACKEND_PORT = env_int("HRMS_DOCKER_BACKEND_PORT", 8001)
DOCKER_FRONTEND_PORT = env_int("HRMS_DOCKER_FRONTEND_PORT", 5173)
VENV_BACKEND_PORT = env_int("HRMS_VENV_BACKEND_PORT", 8000)
VENV_FRONTEND_PORT = env_int("HRMS_VENV_FRONTEND_PORT", 5173)

DOCKER_BACKEND_HEALTH_URL = os.getenv(
    "HRMS_DOCKER_BACKEND_HEALTH_URL",
    f"http://{HRMS_HOST}:{DOCKER_BACKEND_PORT}/health",
)
DOCKER_FRONTEND_URL = os.getenv(
    "HRMS_DOCKER_FRONTEND_URL",
    f"http://{HRMS_HOST}:{DOCKER_FRONTEND_PORT}",
)
VENV_BACKEND_HEALTH_URL = os.getenv(
    "HRMS_VENV_BACKEND_HEALTH_URL",
    f"http://{HRMS_HOST}:{VENV_BACKEND_PORT}/health",
)
VENV_FRONTEND_URL = os.getenv(
    "HRMS_VENV_FRONTEND_URL",
    f"http://{HRMS_HOST}:{VENV_FRONTEND_PORT}",
)


def ensure_runtime_dirs() -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    PID_DIR.mkdir(parents=True, exist_ok=True)


def run_command(command: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=str(cwd) if cwd else None, check=check, text=True)


def is_process_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


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


def spawn_detached(command: str, cwd: Path, log_file: Path) -> int:
    with log_file.open("ab") as log_handle:
        process = subprocess.Popen(
            ["sh", "-c", command],
            cwd=str(cwd),
            stdout=log_handle,
            stderr=log_handle,
            stdin=subprocess.DEVNULL,
            preexec_fn=os.setsid,
        )
        return process.pid


def wait_for_http(url: str, timeout_seconds: int = 120) -> bool:
    deadline = time.time() + timeout_seconds

    while time.time() < deadline:
        try:
            with urlopen(Request(url, method="GET"), timeout=3) as response:
                if 200 <= response.status < 500:
                    return True
        except Exception:  # noqa: BLE001
            time.sleep(1)

    return False


def print_service_urls(backend_url: str, frontend_url: str) -> None:
    print(f"[hrmsctl] Frontend URL: {frontend_url}")
    print(f"[hrmsctl] Backend URL: {backend_url.rsplit('/health', 1)[0]}")


def ensure_env_files() -> None:
    backend_env = BACKEND_DIR / ".env"
    frontend_env = FRONTEND_DIR / ".env"
    backend_example = BACKEND_DIR / ".env.example"
    frontend_example = FRONTEND_DIR / ".env.example"

    if not backend_env.exists() and backend_example.exists():
        backend_env.write_text(backend_example.read_text(encoding="utf-8"), encoding="utf-8")
    if not frontend_env.exists() and frontend_example.exists():
        frontend_env.write_text(frontend_example.read_text(encoding="utf-8"), encoding="utf-8")


def start_docker(build: bool, wait: bool) -> None:
    print("[hrmsctl] Starting services using Docker Compose...")
    command = ["docker", "compose", "up", "-d", "--force-recreate"]
    if build:
        command.append("--build")
    run_command(command, cwd=ROOT_DIR)

    if wait:
        backend_ready = wait_for_http(DOCKER_BACKEND_HEALTH_URL)
        frontend_ready = wait_for_http(DOCKER_FRONTEND_URL)
        if not (backend_ready and frontend_ready):
            raise RuntimeError("Services started but health checks timed out")

    print("[hrmsctl] Docker services started in detached mode.")
    print("[hrmsctl] Check status: docker compose ps")
    print_service_urls(DOCKER_BACKEND_HEALTH_URL, DOCKER_FRONTEND_URL)


def stop_docker() -> None:
    print("[hrmsctl] Stopping Docker services...")
    run_command(["docker", "compose", "down"], cwd=ROOT_DIR)
    print("[hrmsctl] Docker services stopped.")


def status_docker() -> None:
    run_command(["docker", "compose", "ps"], cwd=ROOT_DIR, check=False)
    print(f"[hrmsctl] Backend healthy: {wait_for_http(DOCKER_BACKEND_HEALTH_URL, timeout_seconds=3)}")
    print(f"[hrmsctl] Frontend reachable: {wait_for_http(DOCKER_FRONTEND_URL, timeout_seconds=3)}")


def start_venv(wait: bool) -> None:
    ensure_runtime_dirs()
    ensure_env_files()

    print("[hrmsctl] Preparing backend Python environment...")
    run_command([sys.executable, "-m", "venv", BACKEND_VENV_DIRNAME], cwd=BACKEND_DIR, check=False)

    backend_python = BACKEND_DIR / BACKEND_VENV_DIRNAME / "bin" / "python"
    backend_pip = BACKEND_DIR / BACKEND_VENV_DIRNAME / "bin" / "pip"

    run_command([str(backend_pip), "install", "-r", "requirements.txt"], cwd=BACKEND_DIR)
    run_command([str(backend_python), "-m", "alembic", "upgrade", "head"], cwd=BACKEND_DIR)

    print("[hrmsctl] Preparing frontend Node environment...")
    lock_file = FRONTEND_DIR / "package-lock.json"
    if lock_file.exists():
        run_command(["npm", "ci"], cwd=FRONTEND_DIR)
    else:
        run_command(["npm", "install"], cwd=FRONTEND_DIR)
    run_command(["npm", "run", "build"], cwd=FRONTEND_DIR)

    existing_backend = read_pid(BACKEND_PID_FILE)
    if existing_backend and is_process_running(existing_backend):
        print(f"[hrmsctl] Backend already running with PID {existing_backend}.")
    else:
        backend_cmd = (
            f". {BACKEND_VENV_DIRNAME}/bin/activate && "
            f"gunicorn -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:{VENV_BACKEND_PORT}"
        )
        backend_pid = spawn_detached(backend_cmd, BACKEND_DIR, BACKEND_LOG_FILE)
        write_pid(BACKEND_PID_FILE, backend_pid)
        print(f"[hrmsctl] Backend started (PID {backend_pid}). Logs: {BACKEND_LOG_FILE}")

    existing_frontend = read_pid(FRONTEND_PID_FILE)
    if existing_frontend and is_process_running(existing_frontend):
        print(f"[hrmsctl] Frontend already running with PID {existing_frontend}.")
    else:
        frontend_cmd = f"npm run dev -- --host 0.0.0.0 --port {VENV_FRONTEND_PORT}"
        frontend_pid = spawn_detached(frontend_cmd, FRONTEND_DIR, FRONTEND_LOG_FILE)
        write_pid(FRONTEND_PID_FILE, frontend_pid)
        print(f"[hrmsctl] Frontend started (PID {frontend_pid}). Logs: {FRONTEND_LOG_FILE}")

    if wait:
        backend_ready = wait_for_http(VENV_BACKEND_HEALTH_URL)
        frontend_ready = wait_for_http(VENV_FRONTEND_URL)
        if not (backend_ready and frontend_ready):
            raise RuntimeError("venv services started but health checks timed out")

    print("[hrmsctl] Services launched in detached sessions (survive SSH disconnect).")
    print_service_urls(VENV_BACKEND_HEALTH_URL, VENV_FRONTEND_URL)


def stop_venv() -> None:
    stopped_any = False

    for name, pid_file in (("backend", BACKEND_PID_FILE), ("frontend", FRONTEND_PID_FILE)):
        pid = read_pid(pid_file)
        if not pid:
            print(f"[hrmsctl] {name}: no PID file found.")
            continue

        if not is_process_running(pid):
            print(f"[hrmsctl] {name}: process {pid} is not running; cleaning stale PID.")
            remove_pid(pid_file)
            continue

        print(f"[hrmsctl] Stopping {name} (PID {pid})...")
        os.killpg(os.getpgid(pid), signal.SIGTERM)
        remove_pid(pid_file)
        stopped_any = True

    if not stopped_any:
        print("[hrmsctl] No running venv-mode services were found.")
    else:
        print("[hrmsctl] venv-mode services stopped.")


def status_venv() -> None:
    for name, pid_file, log_file in (
        ("backend", BACKEND_PID_FILE, BACKEND_LOG_FILE),
        ("frontend", FRONTEND_PID_FILE, FRONTEND_LOG_FILE),
    ):
        pid = read_pid(pid_file)
        if not pid:
            print(f"[hrmsctl] {name}: stopped (no PID).")
            continue

        state = "running" if is_process_running(pid) else "stopped"
        print(f"[hrmsctl] {name}: {state} (PID {pid}) | logs: {log_file}")

    print(f"[hrmsctl] Backend healthy: {wait_for_http(VENV_BACKEND_HEALTH_URL, timeout_seconds=3)}")
    print(f"[hrmsctl] Frontend reachable: {wait_for_http(VENV_FRONTEND_URL, timeout_seconds=3)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="HRMS Lite process manager")
    parser.add_argument("action", choices=["start", "stop", "status"], help="Action to perform")
    parser.add_argument(
        "-p",
        "--platform",
        choices=["docker", "venv"],
        required=True,
        help="Run mode: docker compose or direct host processes",
    )
    parser.add_argument("--build", action="store_true", help="Docker mode: build images before start")
    parser.add_argument("--wait", action="store_true", help="Wait for frontend/backend health checks")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    action = args.action
    platform = args.platform

    try:
        if platform == "docker":
            if action == "start":
                start_docker(build=args.build, wait=args.wait)
            elif action == "stop":
                stop_docker()
            else:
                status_docker()
        else:
            if action == "start":
                start_venv(wait=args.wait)
            elif action == "stop":
                stop_venv()
            else:
                status_venv()
    except subprocess.CalledProcessError as exc:
        print(f"[hrmsctl] Command failed with exit code {exc.returncode}: {exc.cmd}", file=sys.stderr)
        return exc.returncode
    except Exception as exc:  # noqa: BLE001
        print(f"[hrmsctl] Unexpected error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

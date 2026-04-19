#!/usr/bin/env python3
"""Concurrent Selenium runner for UI scalability observation.

This is a browser-level stress/smoke harness, not a true protocol-level load test.
It is useful for validating that the UI remains functional under concurrent sessions
and for observing Kubernetes replica changes while traffic increases.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver import ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_BASE_URL = os.getenv("SELENIUM_TEST_BASE_URL", "http://127.0.0.1:5173")
DEFAULT_ADMIN_KEY = os.getenv("SUPERADMIN_KEY", "kjgdfhkgjhd-fjgkehslgjg")
DEFAULT_NAMESPACE = os.getenv("HRMS_K8S_NAMESPACE", "hrms-lite")


@dataclass
class StepMetric:
    name: str
    duration_ms: float


@dataclass
class UserResult:
    user_id: int
    success: bool
    total_duration_ms: float
    steps: list[StepMetric]
    error: str | None = None


class ReplicaObserver:
    def __init__(self, namespace: str, interval_seconds: float) -> None:
        self.namespace = namespace
        self.interval_seconds = interval_seconds
        self.samples: list[dict[str, Any]] = []
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)

    def _run(self) -> None:
        while not self._stop_event.is_set():
            sample = {"timestamp": time.time()}
            try:
                deployments = self._get_deployments()
                sample.update(deployments)
            except Exception as exc:  # noqa: BLE001
                sample["error"] = str(exc)
            self.samples.append(sample)
            self._stop_event.wait(self.interval_seconds)

    def _get_deployments(self) -> dict[str, int]:
        result = subprocess.run(
            [
                "kubectl",
                "get",
                "deployment",
                "hrms-backend",
                "hrms-frontend",
                "-n",
                self.namespace,
                "-o",
                "json",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(result.stdout)
        data: dict[str, int] = {}
        for item in payload.get("items", []):
            name = item["metadata"]["name"]
            data[name] = int(item["status"].get("readyReplicas", 0))
        return data


def build_driver(headless: bool) -> webdriver.Chrome:
    options = ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1440,1200")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-features=Translate")
    options.add_argument("--disable-background-networking")
    service = ChromeService()
    return webdriver.Chrome(service=service, options=options)


def wait_for_ready(driver: webdriver.Chrome, selector: tuple[str, str], timeout: int = 20):
    return WebDriverWait(driver, timeout).until(EC.presence_of_element_located(selector))


def wait_for_text(driver: webdriver.Chrome, selector: tuple[str, str], text: str, timeout: int = 20):
    return WebDriverWait(driver, timeout).until(EC.text_to_be_present_in_element(selector, text))


def timed_step(step_name: str, func):
    started = time.perf_counter()
    func()
    return StepMetric(name=step_name, duration_ms=(time.perf_counter() - started) * 1000)


def run_user_flow(
    user_id: int,
    base_url: str,
    admin_key: str,
    loops: int,
    headless: bool,
) -> UserResult:
    driver = build_driver(headless=headless)
    driver.set_page_load_timeout(30)
    metrics: list[StepMetric] = []
    started = time.perf_counter()

    try:
        def sign_in() -> None:
            driver.get(f"{base_url.rstrip('/')}/signin")
            input_field = wait_for_ready(driver, (By.CSS_SELECTOR, 'input[placeholder="Enter shared key"]'))
            input_field.clear()
            input_field.send_keys(admin_key)
            submit = driver.find_element(By.XPATH, "//button[contains(., 'Enter Platform')]")
            submit.click()
            WebDriverWait(driver, 20).until(EC.url_contains("/dashboard"))

        metrics.append(timed_step("sign_in", sign_in))

        def open_dashboard() -> None:
            driver.get(f"{base_url.rstrip('/')}/dashboard")
            wait_for_ready(driver, (By.TAG_NAME, "body"))

        def open_employees() -> None:
            driver.get(f"{base_url.rstrip('/')}/employees")
            wait_for_ready(driver, (By.XPATH, "//h2[contains(., 'Add Employee') or contains(., 'Employees')]") )

        def open_attendance() -> None:
            driver.get(f"{base_url.rstrip('/')}/attendance")
            wait_for_ready(driver, (By.TAG_NAME, "body"))

        for loop_index in range(loops):
            metrics.append(timed_step(f"dashboard_{loop_index + 1}", open_dashboard))
            metrics.append(timed_step(f"employees_{loop_index + 1}", open_employees))
            metrics.append(timed_step(f"attendance_{loop_index + 1}", open_attendance))

        return UserResult(
            user_id=user_id,
            success=True,
            total_duration_ms=(time.perf_counter() - started) * 1000,
            steps=metrics,
        )
    except (TimeoutException, WebDriverException, Exception) as exc:  # noqa: BLE001
        return UserResult(
            user_id=user_id,
            success=False,
            total_duration_ms=(time.perf_counter() - started) * 1000,
            steps=metrics,
            error=str(exc),
        )
    finally:
        driver.quit()


def summarize(results: list[UserResult], observer: ReplicaObserver | None) -> dict[str, Any]:
    successful = [result for result in results if result.success]
    failed = [result for result in results if not result.success]
    durations = [result.total_duration_ms for result in successful]

    summary: dict[str, Any] = {
        "total_users": len(results),
        "successful_users": len(successful),
        "failed_users": len(failed),
        "avg_duration_ms": round(statistics.mean(durations), 2) if durations else None,
        "p95_duration_ms": round(_percentile(durations, 95), 2) if durations else None,
        "max_duration_ms": round(max(durations), 2) if durations else None,
        "failures": [{"user_id": result.user_id, "error": result.error} for result in failed],
        "results": [
            {
                **asdict(result),
                "steps": [asdict(step) for step in result.steps],
            }
            for result in results
        ],
    }

    if observer:
        summary["replica_samples"] = observer.samples

    return summary


def _percentile(values: list[float], percentile: int) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, round((percentile / 100) * (len(ordered) - 1))))
    return ordered[index]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Selenium-based UI scalability runner")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Frontend base URL")
    parser.add_argument("--superadmin-key", default=DEFAULT_ADMIN_KEY, help="Shared superadmin key")
    parser.add_argument("--users", type=int, default=5, help="Concurrent browser sessions")
    parser.add_argument("--loops", type=int, default=2, help="Dashboard/employees/attendance loops per user")
    parser.add_argument("--ramp-seconds", type=float, default=5.0, help="Seconds to spread user starts across")
    parser.add_argument("--headed", action="store_true", help="Run with visible browser windows")
    parser.add_argument("--observe-k8s", action="store_true", help="Sample backend/frontend replicas during the run")
    parser.add_argument("--namespace", default=DEFAULT_NAMESPACE, help="Kubernetes namespace for replica sampling")
    parser.add_argument("--observe-interval", type=float, default=5.0, help="Replica sample interval in seconds")
    parser.add_argument("--report-file", help="Optional JSON report output path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    headless = not args.headed
    observer = ReplicaObserver(args.namespace, args.observe_interval) if args.observe_k8s else None

    if observer:
        observer.start()

    futures = []
    started = time.perf_counter()
    try:
        with ThreadPoolExecutor(max_workers=args.users) as executor:
            for user_id in range(1, args.users + 1):
                delay = ((user_id - 1) / max(args.users - 1, 1)) * args.ramp_seconds
                if delay:
                    time.sleep(delay if user_id == 1 else args.ramp_seconds / max(args.users - 1, 1))
                futures.append(
                    executor.submit(
                        run_user_flow,
                        user_id,
                        args.base_url,
                        args.superadmin_key,
                        args.loops,
                        headless,
                    )
                )
            results = [future.result() for future in as_completed(futures)]
    except Exception as exc:
        print(f"Error during test execution: {exc}")
    finally:
        if observer:
            observer.stop()

    summary = summarize(sorted(results, key=lambda item: item.user_id), observer)
    summary["wall_clock_duration_ms"] = round((time.perf_counter() - started) * 1000, 2)

    print(json.dumps({
        "summary": {
            key: value
            for key, value in summary.items()
            if key not in {"results", "replica_samples", "failures"}
        },
        "failures": summary.get("failures", []),
    }, indent=2))

    if args.report_file:
        report_path = Path(args.report_file)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"Detailed report written to {report_path}")

    return 0 if summary["failed_users"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
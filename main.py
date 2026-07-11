"""
One-command launcher for the Truck Parking System.

Run from this folder:
    python main.py

What it does:
  1. Starts Docker Desktop if possible.
  2. Builds and starts PostgreSQL, backend, frontend, and Nginx.
  3. Opens the web app in your browser.
  4. Streams all container logs in this terminal.
  5. Stops the stack when you press Ctrl+C.
"""
from __future__ import annotations

import argparse
import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from typing import Sequence


ROOT_DIR = Path(__file__).resolve().parent
APP_DIR = ROOT_DIR / "truckpark"
APP_URL = "http://localhost"
HEALTH_URL = "http://127.0.0.1:8000/health"
LOGIN_URL = "http://127.0.0.1/login"
DOCKER_DESKTOP = Path(r"C:\Program Files\Docker\Docker\Docker Desktop.exe")


def print_step(message: str) -> None:
    print(f"\n==> {message}", flush=True)


def print_note(message: str) -> None:
    print(f"    {message}", flush=True)


def compose_cmd() -> list[str]:
    if shutil.which("docker-compose"):
        return ["docker-compose"]
    if shutil.which("docker"):
        return ["docker", "compose"]
    raise RuntimeError("Docker Compose was not found. Install/open Docker Desktop first.")


def run(command: Sequence[str], *, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(command, cwd=APP_DIR, check=check)


def docker_is_ready() -> bool:
    try:
        result = subprocess.run(
            ["docker", "info"],
            cwd=APP_DIR,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def start_docker_desktop() -> None:
    if docker_is_ready():
        return

    if DOCKER_DESKTOP.exists():
        print_step("Starting Docker Desktop")
        os.startfile(DOCKER_DESKTOP)  # type: ignore[attr-defined]
    else:
        print_step("Waiting for Docker")
        print_note("Docker Desktop was not found at the default install path.")

    deadline = time.time() + 120
    while time.time() < deadline:
        if docker_is_ready():
            print_note("Docker is ready.")
            return
        time.sleep(3)
        print_note("Still waiting for Docker...")

    raise RuntimeError("Docker did not become ready. Open Docker Desktop, then run python main.py again.")


def wait_for_url(url: str, label: str, timeout_seconds: int = 120) -> bool:
    print_step(f"Waiting for {label}")
    deadline = time.time() + timeout_seconds
    last_error = ""

    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                if 200 <= response.status < 500:
                    print_note(f"{label} is responding: {url}")
                    return True
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = str(exc)

        time.sleep(3)
        print_note(f"{label} is not ready yet...")

    print_note(f"{label} did not become ready in time. Last error: {last_error}")
    return False


def stream_logs(compose: Sequence[str]) -> subprocess.Popen:
    print_step("Streaming live system activity")
    print_note("Press Ctrl+C whenever you want to stop the whole system.")
    return subprocess.Popen([*compose, "logs", "-f", "--tail=100"], cwd=APP_DIR)


def stop_stack(compose: Sequence[str]) -> None:
    print_step("Stopping the system")
    subprocess.run([*compose, "down"], cwd=APP_DIR, check=False)
    print_note("Stopped. Database data is kept in the Docker volume.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Start the full Truck Parking System.")
    parser.add_argument("--no-browser", action="store_true", help="Start everything without opening the browser.")
    parser.add_argument("--no-build", action="store_true", help="Skip Docker image builds and only start containers.")
    parser.add_argument("--keep-running", action="store_true", help="Do not stop containers when this launcher exits.")
    args = parser.parse_args()

    if not APP_DIR.exists():
        print(f"Could not find app folder: {APP_DIR}", file=sys.stderr)
        return 1

    compose = compose_cmd()
    logs_process: subprocess.Popen | None = None

    def handle_stop(signum: int, frame: object) -> None:
        raise KeyboardInterrupt

    signal.signal(signal.SIGINT, handle_stop)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, handle_stop)

    try:
        start_docker_desktop()

        print_step("Starting database, backend, frontend, and Nginx")
        up_command = [*compose, "up", "-d"]
        if not args.no_build:
            up_command.append("--build")
        run(up_command)

        backend_ok = wait_for_url(HEALTH_URL, "backend")
        frontend_ok = wait_for_url(LOGIN_URL, "frontend")

        if not args.no_browser and (backend_ok or frontend_ok):
            print_step("Opening the web app")
            webbrowser.open(APP_URL)
            print_note(f"App: {APP_URL}")
            print_note("Admin login: mobile 7200775876, password 0000")
            print_note("Gatekeeper login: mobile 8888888888, password 0000")

        logs_process = stream_logs(compose)
        return logs_process.wait()

    except KeyboardInterrupt:
        print("\nInterrupted by user.", flush=True)
        return 0
    except subprocess.CalledProcessError as exc:
        print(f"\nCommand failed with exit code {exc.returncode}: {' '.join(exc.cmd)}", file=sys.stderr)
        return exc.returncode
    except RuntimeError as exc:
        print(f"\n{exc}", file=sys.stderr)
        return 1
    finally:
        if logs_process and logs_process.poll() is None:
            logs_process.terminate()
        if not args.keep_running:
            stop_stack(compose)


if __name__ == "__main__":
    raise SystemExit(main())

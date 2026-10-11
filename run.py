#!/usr/bin/env python3
"""
ClearSky Intelligence — Unified Local Development Runner

Runs the complete ClearSky Intelligence application locally:
- FastAPI Backend on port 8000 (with auto-reload and SQLite database)
- React Frontend on port 5173 (via Vite dev server)

Usage:
    python run.py                 # Runs both Backend (FastAPI) and Frontend (React)
    python run.py --backend       # Runs only the FastAPI Backend
    python run.py --frontend      # Runs only the React Frontend
    python run.py --port 8000 --frontend-port 5173
"""

import sys
import os
import signal
import socket
import subprocess
import argparse
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"

# Ensure backend and root are in python path
for p in (BACKEND_DIR, ROOT_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

existing_pythonpath = os.environ.get("PYTHONPATH", "")
os.environ["PYTHONPATH"] = f"{BACKEND_DIR}:{ROOT_DIR}:{existing_pythonpath}".strip(":")


def free_port_if_in_use(port: int, host: str = "127.0.0.1"):
    """Check if port is currently occupied by a stale process and free it."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            if s.connect_ex((host, port)) != 0:
                return  # Port is free
    except Exception:
        return

    print(f"  [!] Port {port} is currently in use. Attempting to free stale process...")
    try:
        out = subprocess.check_output(["lsof", "-t", "-i", f":{port}"], text=True)
        pids = [int(p.strip()) for p in out.strip().split() if p.strip()]
        current_pid = os.getpid()
        for pid in pids:
            if pid != current_pid:
                try:
                    os.kill(pid, signal.SIGKILL)
                    print(f"  [✓] Terminated stale process PID {pid} on port {port}")
                except Exception as e:
                    print(f"  [!] Could not kill PID {pid}: {e}")
        time.sleep(0.5)
    except Exception:
        pass


def print_banner(backend_port: int, frontend_port: int, mode: str):
    print("\n" + "=" * 70)
    print("  ClearSky Intelligence — Local Development Environment")
    print("  Team: Quantified Minds (Ishaan Chaturvedi, Ankit Kumar Tiwari)")
    print("=" * 70)
    if mode in ("all", "frontend"):
        print(f"  ► React Web App (Vite)  : http://localhost:{frontend_port}/")
    if mode in ("all", "backend"):
        print(f"  ► FastAPI REST Server   : http://localhost:{backend_port}/")
        print(f"  ► API Swagger Docs      : http://localhost:{backend_port}/docs")
        print(f"  ► API Health Check      : http://localhost:{backend_port}/api/health")
    print("=" * 70)
    print("  Press Ctrl+C to terminate all services.\n")


def start_backend(host: str, port: int, reload: bool):
    """Start uvicorn running the FastAPI app."""
    free_port_if_in_use(port, host)
    # Find python executable (prefer current or .venv)
    venv_python = ROOT_DIR / ".venv" / "bin" / "python"
    py_exec = str(venv_python) if venv_python.exists() else sys.executable

    cmd = [
        py_exec,
        "-m",
        "uvicorn",
        "backend.app.main:app",
        "--host",
        host,
        "--port",
        str(port),
    ]
    if reload:
        cmd.append("--reload")

    return subprocess.Popen(
        cmd,
        cwd=str(ROOT_DIR),
        env=os.environ.copy()
    )


def start_frontend(port: int):
    """Start Vite dev server."""
    free_port_if_in_use(port, "127.0.0.1")
    if not (FRONTEND_DIR / "node_modules").exists():
        print("  [!] frontend/node_modules not found. Running 'npm install'...")
        subprocess.run(["npm", "install"], cwd=str(FRONTEND_DIR), check=True)

    cmd = ["npm", "run", "dev", "--", "--port", str(port), "--host"]
    return subprocess.Popen(
        cmd,
        cwd=str(FRONTEND_DIR),
        env=os.environ.copy()
    )


def main():
    parser = argparse.ArgumentParser(description="ClearSky Intelligence Unified Runner")
    parser.add_argument("--backend", "-b", action="store_true", help="Run only the FastAPI backend")
    parser.add_argument("--frontend", "-f", action="store_true", help="Run only the React frontend")
    parser.add_argument("--host", default="127.0.0.1", help="Backend host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Backend port (default: 8000)")
    parser.add_argument("--frontend-port", type=int, default=5173, help="Frontend port (default: 5173)")
    parser.add_argument("--no-reload", action="store_true", help="Disable backend auto-reload")
    args = parser.parse_args()

    mode = "all"
    if args.backend and not args.frontend:
        mode = "backend"
    elif args.frontend and not args.backend:
        mode = "frontend"

    print_banner(args.port, args.frontend_port, mode)

    processes = []

    try:
        if mode in ("all", "backend"):
            print("  [*] Starting FastAPI backend...")
            backend_proc = start_backend(args.host, args.port, reload=not args.no_reload)
            processes.append(("Backend", backend_proc))

        if mode in ("all", "frontend"):
            # Small delay so backend starts up first
            time.sleep(1)
            print("  [*] Starting React frontend (Vite)...")
            frontend_proc = start_frontend(args.frontend_port)
            processes.append(("Frontend", frontend_proc))

        # Wait for any process to exit or keyboard interrupt
        while True:
            for name, proc in processes:
                ret = proc.poll()
                if ret is not None:
                    print(f"\n  [!] {name} process exited with code {ret}")
                    return
            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\n\n  [*] Stopping services gracefully...")
    finally:
        for name, proc in processes:
            if proc.poll() is None:
                try:
                    proc.terminate()
                    proc.wait(timeout=3)
                except Exception:
                    proc.kill()
        print("  [✓] All services stopped.")


if __name__ == "__main__":
    main()

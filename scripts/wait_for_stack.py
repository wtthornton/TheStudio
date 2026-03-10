#!/usr/bin/env python3
"""Wait for all Docker Compose services to become healthy.

Usage:
    python scripts/wait_for_stack.py [--timeout 120]

Polls health endpoints for PostgreSQL (pg_isready on port 5434),
NATS (TCP on port 4222), Temporal (tctl on port 7233), and the
app (/healthz on port 8000). Exits 0 when all pass, 1 on timeout.
"""

import argparse
import socket
import sys
import time

import httpx

DEFAULT_TIMEOUT = 120
POLL_INTERVAL = 2

SERVICES: dict[str, dict[str, object]] = {
    "postgres": {"host": "localhost", "port": 5434, "check": "tcp"},
    "nats": {"host": "localhost", "port": 4222, "check": "tcp"},
    "temporal": {"host": "localhost", "port": 7233, "check": "tcp"},
    "app": {"url": "http://localhost:8000/healthz", "check": "http"},
}


def check_tcp(host: str, port: int) -> bool:
    """Return True if a TCP connection to host:port succeeds."""
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except (OSError, ConnectionRefusedError):
        return False


def check_http(url: str) -> bool:
    """Return True if url returns HTTP 200."""
    try:
        r = httpx.get(url, timeout=5)
        return r.status_code == 200
    except (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout):
        return False


def check_service(name: str, config: dict[str, object]) -> bool:
    """Check a single service health."""
    if config["check"] == "tcp":
        return check_tcp(str(config["host"]), int(config["port"]))  # type: ignore[arg-type]
    if config["check"] == "http":
        return check_http(str(config["url"]))
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Wait for Docker Compose stack health.")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="Timeout in seconds")
    args = parser.parse_args()

    deadline = time.monotonic() + args.timeout
    healthy: set[str] = set()

    print(f"Waiting for stack (timeout={args.timeout}s)...")

    while time.monotonic() < deadline:
        for name, config in SERVICES.items():
            if name not in healthy and check_service(name, config):
                healthy.add(name)
                print(f"  [OK] {name}")

        if len(healthy) == len(SERVICES):
            print("All services healthy.")
            return 0

        time.sleep(POLL_INTERVAL)

    # Timeout — report status
    print("\nTimeout! Service status:")
    for name in SERVICES:
        status = "healthy" if name in healthy else "NOT READY"
        print(f"  {name}: {status}")

    return 1


if __name__ == "__main__":
    sys.exit(main())

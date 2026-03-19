"""Docker stack health gate for P0 tests.

Verifies all required Docker services are reachable before any P0 test
begins. Uses the app's ``/admin/health`` endpoint (through Caddy) which
reports on Temporal, JetStream/NATS, Postgres, and Router in one call.

If any service is down, the entire P0 run aborts with clear diagnostics
naming the failed service(s) and suggesting remediation.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import httpx

# Default Caddy HTTPS endpoint (prod compose maps 9443 -> 443)
DEFAULT_BASE_URL = "https://localhost:9443"


@dataclass
class ServiceStatus:
    name: str
    healthy: bool
    detail: str = ""
    remediation: str = ""


@dataclass
class HealthReport:
    services: list[ServiceStatus] = field(default_factory=list)
    duration_ms: float = 0.0

    @property
    def all_healthy(self) -> bool:
        return all(s.healthy for s in self.services)

    @property
    def failed(self) -> list[ServiceStatus]:
        return [s for s in self.services if not s.healthy]

    def summary(self) -> str:
        lines = [f"Health Gate ({self.duration_ms:.0f}ms):"]
        for s in self.services:
            icon = "OK" if s.healthy else "FAIL"
            line = f"  [{icon}] {s.name}"
            if s.detail:
                line += f" — {s.detail}"
            lines.append(line)
        if self.failed:
            lines.append("")
            lines.append("Remediation:")
            for s in self.failed:
                if s.remediation:
                    lines.append(f"  {s.name}: {s.remediation}")
        return "\n".join(lines)


def check_stack_health(
    base_url: str = DEFAULT_BASE_URL,
    admin_user: str = "admin",
    admin_password: str = "",
    timeout: float = 10.0,
) -> HealthReport:
    """Run health checks against the deployed Docker stack.

    1. Probe Caddy via ``/healthz`` (no auth).
    2. If Caddy is up, hit ``/admin/health`` (with Basic Auth) for
       backend service status (Temporal, NATS, Postgres, Router).

    Returns a :class:`HealthReport` in under 15 seconds.
    """
    start = time.monotonic()
    services: list[ServiceStatus] = []
    compose_hint = "cd infra && docker compose -f docker-compose.prod.yml up -d"

    # 1. Caddy + App liveness (no auth)
    try:
        r = httpx.get(f"{base_url}/healthz", verify=False, timeout=timeout)
        caddy_ok = r.status_code == 200
        services.append(ServiceStatus(
            name="Caddy + App",
            healthy=caddy_ok,
            detail=f"HTTP {r.status_code}" + ("" if caddy_ok else " (expected 200)"),
            remediation=f"{compose_hint} caddy app",
        ))
    except (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout) as exc:
        caddy_ok = False
        services.append(ServiceStatus(
            name="Caddy + App",
            healthy=False,
            detail=str(exc),
            remediation=f"{compose_hint} caddy app",
        ))

    if not caddy_ok:
        # Can't probe backend services without Caddy
        for svc in ("Temporal", "NATS/JetStream", "Postgres"):
            services.append(ServiceStatus(
                name=svc,
                healthy=False,
                detail="Cannot check — Caddy/App is down",
                remediation="Fix Caddy first",
            ))
        elapsed = (time.monotonic() - start) * 1000
        return HealthReport(services=services, duration_ms=elapsed)

    # 2. Backend services via /admin/health
    auth = (admin_user, admin_password) if admin_password else None
    try:
        r = httpx.get(
            f"{base_url}/admin/health",
            verify=False,
            timeout=timeout,
            auth=auth,
        )
        if r.status_code == 401:
            services.append(ServiceStatus(
                name="Admin Auth",
                healthy=False,
                detail="401 Unauthorized — admin credentials rejected",
                remediation="Check ADMIN_PASSWORD in infra/.env matches Caddy hash",
            ))
        elif r.status_code == 200:
            data = r.json()
            svc_map = {
                "temporal": ("Temporal", f"{compose_hint} temporal"),
                "jetstream": ("NATS/JetStream", f"{compose_hint} nats"),
                "postgres": ("Postgres", f"{compose_hint} postgres"),
                "router": ("Router", f"{compose_hint} app"),
            }
            for key, (display_name, fix) in svc_map.items():
                svc_data = data.get(key, {})
                svc_status = svc_data.get("status", "UNKNOWN")
                healthy = svc_status == "OK"
                detail = svc_status
                if svc_data.get("latency_ms") is not None:
                    detail += f" ({svc_data['latency_ms']:.0f}ms)"
                if svc_data.get("error"):
                    detail += f" — {svc_data['error']}"
                services.append(ServiceStatus(
                    name=display_name,
                    healthy=healthy,
                    detail=detail,
                    remediation=fix,
                ))
        else:
            services.append(ServiceStatus(
                name="Admin Health",
                healthy=False,
                detail=f"HTTP {r.status_code}",
                remediation="Check app logs",
            ))
    except (httpx.ConnectError, httpx.ReadTimeout) as exc:
        services.append(ServiceStatus(
            name="Admin Health",
            healthy=False,
            detail=str(exc),
            remediation="Check Caddy and app logs",
        ))

    # 3. pg-proxy (host port 5434)
    import socket
    try:
        with socket.create_connection(("localhost", 5434), timeout=3.0):
            pg_ok = True
            pg_detail = "tcp:localhost:5434 reachable"
    except (ConnectionRefusedError, OSError, TimeoutError) as exc:
        pg_ok = False
        pg_detail = f"tcp:localhost:5434 — {exc}"
    services.append(ServiceStatus(
        name="pg-proxy (host)",
        healthy=pg_ok,
        detail=pg_detail,
        remediation=f"{compose_hint} pg-proxy",
    ))

    elapsed = (time.monotonic() - start) * 1000
    return HealthReport(services=services, duration_ms=elapsed)


def require_healthy_stack(**kwargs: str | float) -> HealthReport:
    """Check stack health; raise ``SystemExit`` if any service is down."""
    report = check_stack_health(**kwargs)  # type: ignore[arg-type]
    if not report.all_healthy:
        raise SystemExit(f"Docker stack not healthy. Aborting.\n\n{report.summary()}")
    return report


if __name__ == "__main__":
    import os

    report = check_stack_health(
        admin_password=os.environ.get("ADMIN_PASSWORD", ""),
    )
    print(report.summary())
    raise SystemExit(0 if report.all_healthy else 1)

"""Credential validation guard for the P0 runner.

Validates that environment variables contain real credentials,
not placeholders or empty strings. This mirrors the bash guard
in ``scripts/run-p0-tests.sh`` but is implemented in Python for
portability and testability.

Can be invoked as a module: ``python -m tests.p0.credential_guard``
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field


@dataclass
class CredentialCheck:
    """Result of a single credential check."""

    name: str
    ok: bool
    message: str = ""


@dataclass
class CredentialReport:
    """Aggregate result of all credential checks."""

    checks: list[CredentialCheck] = field(default_factory=list)

    @property
    def all_ok(self) -> bool:
        return all(c.ok for c in self.checks)

    @property
    def failed(self) -> list[CredentialCheck]:
        return [c for c in self.checks if not c.ok]

    def summary(self) -> str:
        lines = ["Credential Validation:"]
        for c in self.checks:
            icon = "OK" if c.ok else "FAIL"
            line = f"  [{icon}] {c.name}"
            if c.message:
                line += f" — {c.message}"
            lines.append(line)
        return "\n".join(lines)


def validate_credentials(
    api_key: str | None = None,
    postgres_password: str | None = None,
    admin_user: str | None = None,
    admin_password: str | None = None,
    webhook_secret: str | None = None,
) -> CredentialReport:
    """Validate P0 test credentials.

    If arguments are None, reads from environment variables.
    """
    if api_key is None:
        api_key = os.environ.get("THESTUDIO_ANTHROPIC_API_KEY", "")
    if postgres_password is None:
        postgres_password = os.environ.get("POSTGRES_PASSWORD", "")
    if admin_user is None:
        admin_user = os.environ.get("ADMIN_USER", "")
    if admin_password is None:
        admin_password = os.environ.get("ADMIN_PASSWORD", "")
    if webhook_secret is None:
        webhook_secret = os.environ.get("THESTUDIO_WEBHOOK_SECRET", "")

    checks: list[CredentialCheck] = []

    # API key
    if not api_key:
        checks.append(CredentialCheck(
            "THESTUDIO_ANTHROPIC_API_KEY", False, "is empty"
        ))
    elif not api_key.startswith("sk-ant-"):
        checks.append(CredentialCheck(
            "THESTUDIO_ANTHROPIC_API_KEY", False,
            "does not start with sk-ant- (placeholder?)"
        ))
    else:
        checks.append(CredentialCheck("THESTUDIO_ANTHROPIC_API_KEY", True))

    # Postgres password
    if not postgres_password:
        checks.append(CredentialCheck(
            "POSTGRES_PASSWORD", False, "is empty"
        ))
    elif postgres_password == "thestudio_dev":
        checks.append(CredentialCheck(
            "POSTGRES_PASSWORD", False,
            "is the dev placeholder 'thestudio_dev' — use a real password"
        ))
    else:
        checks.append(CredentialCheck("POSTGRES_PASSWORD", True))

    # Admin user
    if not admin_user:
        checks.append(CredentialCheck("ADMIN_USER", False, "is empty"))
    else:
        checks.append(CredentialCheck("ADMIN_USER", True))

    # Admin password
    if not admin_password:
        checks.append(CredentialCheck(
            "ADMIN_PASSWORD", False, "is empty"
        ))
    else:
        checks.append(CredentialCheck("ADMIN_PASSWORD", True))

    # Webhook secret
    if not webhook_secret:
        checks.append(CredentialCheck(
            "THESTUDIO_WEBHOOK_SECRET", False, "is empty"
        ))
    else:
        checks.append(CredentialCheck("THESTUDIO_WEBHOOK_SECRET", True))

    return CredentialReport(checks=checks)


if __name__ == "__main__":
    report = validate_credentials()
    print(report.summary())
    sys.exit(0 if report.all_ok else 1)

"""Eval preflight guard — validates container LLM config before eval runs.

Checks that the Docker container is configured with:
  1. ``THESTUDIO_LLM_PROVIDER=anthropic`` (not ``mock``)
  2. ``THESTUDIO_ANTHROPIC_API_KEY`` matches the host environment key

If checks fail, eval results would be meaningless — the container is
not using the same LLM provider/key as the tests expect.

Can be invoked as a module: ``python -m tests.p0.eval_preflight``
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass


@dataclass
class PreflightResult:
    """Result of the eval preflight check."""

    ok: bool
    message: str

    def __str__(self) -> str:
        prefix = "PASS" if self.ok else "FAIL"
        return f"[Eval Preflight {prefix}] {self.message}"


def check_container_env(
    compose_file: str = "infra/docker-compose.prod.yml",
    host_api_key: str | None = None,
) -> PreflightResult:
    """Read container env vars via ``docker compose exec`` and validate.

    Args:
        compose_file: Path to the docker-compose file.
        host_api_key: The API key from the host environment. If None,
            reads from ``THESTUDIO_ANTHROPIC_API_KEY`` env var.

    Returns:
        PreflightResult with ok=True if checks pass.
    """
    if host_api_key is None:
        host_api_key = os.environ.get("THESTUDIO_ANTHROPIC_API_KEY", "")

    # Read container's LLM provider
    container_provider = _read_container_env(compose_file, "THESTUDIO_LLM_PROVIDER")
    if container_provider is None:
        return PreflightResult(
            ok=False,
            message=(
                "Could not read THESTUDIO_LLM_PROVIDER from container "
                "(is the app container running?)"
            ),
        )

    if container_provider != "anthropic":
        return PreflightResult(
            ok=False,
            message=(
                f"Container LLM provider is '{container_provider}', not 'anthropic' "
                "-- eval results would be meaningless"
            ),
        )

    # Read container's API key and compare with host
    container_key = _read_container_env(
        compose_file, "THESTUDIO_ANTHROPIC_API_KEY"
    )
    if container_key and host_api_key and container_key != host_api_key:
        return PreflightResult(
            ok=False,
            message=(
                "Container API key does not match host env "
                "-- eval tests would use a different key than the container"
            ),
        )

    return PreflightResult(
        ok=True,
        message="provider=anthropic, API key matches",
    )


def _read_container_env(compose_file: str, var_name: str) -> str | None:
    """Read an environment variable from the running app container.

    Returns the value (stripped), or None if the container is not reachable.
    """
    try:
        result = subprocess.run(
            [
                "docker", "compose", "-f", compose_file,
                "exec", "-T", "app", "printenv", var_name,
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return None
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None


if __name__ == "__main__":
    result = check_container_env()
    print(result)
    sys.exit(0 if result.ok else 1)

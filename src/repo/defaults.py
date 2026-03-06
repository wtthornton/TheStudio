"""Default configurations for Repo Profile."""

# Default required checks for Observe tier
DEFAULT_REQUIRED_CHECKS: list[str] = ["ruff", "pytest"]

# Default tool allowlist for Developer role
DEFAULT_TOOL_ALLOWLIST: list[str] = [
    "read_file",
    "write_file",
    "list_directory",
    "run_command_lint",
    "run_command_test",
]

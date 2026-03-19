"""Root conftest: run unit tests first to avoid event-loop pollution from other suites."""

import pytest


def _order_key(item: pytest.Item) -> tuple[int, str]:
    """Sort: unit (0), integration (1), e2e (2), docker (3), playwright (4), then by path."""
    path = str(item.fspath)
    if "/unit/" in path or "\\unit\\" in path:
        return (0, path)
    if "/integration/" in path or "\\integration\\" in path:
        return (1, path)
    if "/e2e/" in path or "\\e2e\\" in path:
        return (2, path)
    if "/docker/" in path or "\\docker\\" in path:
        return (3, path)
    if "/p0/" in path or "\\p0\\" in path:
        return (4, path)
    if "/playwright/" in path or "\\playwright\\" in path:
        return (5, path)
    return (6, path)


def pytest_collection_modifyitems(session: pytest.Session, config: pytest.Config, items: list[pytest.Item]) -> None:
    """Reorder tests so unit runs first, then integration, docker, playwright."""
    items.sort(key=_order_key)

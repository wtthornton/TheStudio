"""Integration test: full signal consumption path.

Requires NATS server. Marked with pytest.mark.integration.
"""

import pytest

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_signal_emit_consume_roundtrip() -> None:
    """Emit a verification signal, verify it is consumed by the ingestor."""
    pytest.skip("Requires running NATS server")

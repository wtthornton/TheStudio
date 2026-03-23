"""Tests for diff application fallback (Story 40.2)."""

import base64
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.verification.remote.diff_apply import (
    DiffApplyError,
    PathTraversalError,
    apply_changed_files,
)


def _github_contents_response(content: str, status_code: int = 200) -> MagicMock:
    """Create a mock httpx response for GitHub Contents API."""
    resp = MagicMock()
    resp.status_code = status_code
    encoded = base64.b64encode(content.encode()).decode()
    resp.json.return_value = {"content": encoded}
    resp.text = ""
    return resp


def _error_response(status_code: int, text: str = "error") -> MagicMock:
    """Create a mock error response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    return resp


@pytest.mark.asyncio
async def test_apply_changed_files_new_file(tmp_path):
    """Applies a new file to the workspace."""
    workspace = str(tmp_path)
    content = "print('hello')\n"
    response = _github_contents_response(content)

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await apply_changed_files(
            workspace, ["src/hello.py"], "owner", "repo", "branch", "token123"
        )

    assert len(result) == 1
    dest = os.path.join(workspace, "src", "hello.py")
    assert result[0] == dest
    assert os.path.exists(dest)
    with open(dest) as f:
        assert f.read() == content


@pytest.mark.asyncio
async def test_apply_changed_files_creates_parent_dirs(tmp_path):
    """Creates parent directories as needed."""
    workspace = str(tmp_path)
    response = _github_contents_response("data")

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await apply_changed_files(
            workspace, ["deeply/nested/dir/file.py"], "o", "r", "b", "t"
        )

    assert len(result) == 1
    assert os.path.exists(os.path.join(workspace, "deeply", "nested", "dir", "file.py"))


@pytest.mark.asyncio
async def test_apply_changed_files_deleted_file(tmp_path):
    """Skips files that return 404 (deleted)."""
    workspace = str(tmp_path)
    response = _error_response(404)

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await apply_changed_files(
            workspace, ["deleted_file.py"], "o", "r", "b", "t"
        )

    assert result == []


@pytest.mark.asyncio
async def test_path_traversal_dotdot():
    """Rejects paths with .. components."""
    with pytest.raises(PathTraversalError, match="traversal"):
        await apply_changed_files("/tmp/ws", ["../etc/passwd"], "o", "r", "b", "t")


@pytest.mark.asyncio
async def test_path_traversal_absolute():
    """Rejects absolute paths."""
    with pytest.raises(PathTraversalError, match="Absolute path"):
        await apply_changed_files("/tmp/ws", ["/abs/path/file.py"], "o", "r", "b", "t")


@pytest.mark.asyncio
async def test_path_traversal_null_byte():
    """Rejects paths with null bytes."""
    with pytest.raises(PathTraversalError, match="Null byte"):
        await apply_changed_files("/tmp/ws", ["file\x00.py"], "o", "r", "b", "t")


@pytest.mark.asyncio
async def test_path_traversal_deep():
    """Rejects deeply nested traversal."""
    with pytest.raises(PathTraversalError, match="traversal"):
        await apply_changed_files("/tmp/ws", ["foo/../../../bar"], "o", "r", "b", "t")


@pytest.mark.asyncio
async def test_rollback_on_api_failure(tmp_path):
    """Rolls back written files when a subsequent API call fails."""
    workspace = str(tmp_path)
    good_response = _github_contents_response("good content")
    bad_response = _error_response(500, "Internal Server Error")

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=[good_response, bad_response])
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(DiffApplyError):
            await apply_changed_files(
                workspace,
                ["first.py", "second.py"],
                "o", "r", "b", "t",
            )

    # First file should have been rolled back
    assert not os.path.exists(os.path.join(workspace, "first.py"))

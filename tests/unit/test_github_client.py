"""Unit tests for GitHubClient (src/publisher/github_client.py).

Covers all public methods with mocked HTTP transport to avoid real API calls.
Uses httpx.MockTransport for realistic request/response testing.
"""

from typing import Any
from unittest.mock import AsyncMock

import httpx
import pytest

from src.publisher.github_client import GITHUB_API_BASE, GitHubClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_client(
    responses: list[httpx.Response],
) -> tuple[GitHubClient, list[httpx.Request]]:
    """Build a GitHubClient wired to a mock transport that replays *responses*."""
    captured: list[httpx.Request] = []
    call_idx = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_idx
        captured.append(request)
        resp = responses[min(call_idx, len(responses) - 1)]
        call_idx += 1
        return resp

    client = GitHubClient("test-installation-token")
    client._client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url=GITHUB_API_BASE,
        headers=dict(client._client.headers),
    )
    return client, captured


# ---------------------------------------------------------------------------
# Constructor / context manager
# ---------------------------------------------------------------------------


class TestGitHubClientInit:
    def test_auth_header_set(self) -> None:
        client = GitHubClient("tok123")
        assert client._client.headers["authorization"] == "token tok123"

    def test_accept_header_set(self) -> None:
        client = GitHubClient("tok123")
        assert "application/vnd.github+json" in client._client.headers["accept"]

    def test_api_version_header(self) -> None:
        client = GitHubClient("tok123")
        assert client._client.headers["x-github-api-version"] == "2022-11-28"

    def test_timeout_configured(self) -> None:
        client = GitHubClient("tok123")
        assert client._client.timeout.connect == 30.0


class TestAsyncContextManager:
    async def test_aenter_returns_self(self) -> None:
        client = GitHubClient("tok")
        async with client as ctx:
            assert ctx is client

    async def test_aexit_closes_client(self) -> None:
        client = GitHubClient("tok")
        client._client = AsyncMock()
        async with client:
            pass
        client._client.aclose.assert_awaited_once()


class TestClose:
    async def test_close_delegates_to_aclose(self) -> None:
        client = GitHubClient("tok")
        client._client = AsyncMock()
        await client.close()
        client._client.aclose.assert_awaited_once()


# ---------------------------------------------------------------------------
# _request
# ---------------------------------------------------------------------------


class TestRequest:
    async def test_returns_json_on_success(self) -> None:
        client, _ = _make_client([httpx.Response(200, json={"ok": True})])
        result = await client._request("GET", "/test")
        assert result == {"ok": True}

    async def test_raises_on_http_error(self) -> None:
        client, _ = _make_client([httpx.Response(404, json={"message": "Not Found"})])
        with pytest.raises(httpx.HTTPStatusError):
            await client._request("GET", "/missing")

    async def test_passes_kwargs(self) -> None:
        client, captured = _make_client([httpx.Response(200, json={"id": 1})])
        await client._request("POST", "/items", json={"name": "foo"})
        assert len(captured) == 1
        assert b'"name"' in captured[0].content


# ---------------------------------------------------------------------------
# get_default_branch
# ---------------------------------------------------------------------------


class TestGetDefaultBranch:
    async def test_returns_default_branch(self) -> None:
        client, _ = _make_client(
            [httpx.Response(200, json={"default_branch": "main"})]
        )
        branch = await client.get_default_branch("acme", "repo")
        assert branch == "main"

    async def test_request_url(self) -> None:
        client, captured = _make_client(
            [httpx.Response(200, json={"default_branch": "develop"})]
        )
        await client.get_default_branch("org", "proj")
        assert captured[0].url.path == "/repos/org/proj"


# ---------------------------------------------------------------------------
# get_branch_sha
# ---------------------------------------------------------------------------


class TestGetBranchSha:
    async def test_returns_sha(self) -> None:
        client, _ = _make_client(
            [httpx.Response(200, json={"object": {"sha": "abc123"}})]
        )
        sha = await client.get_branch_sha("o", "r", "main")
        assert sha == "abc123"

    async def test_request_url(self) -> None:
        client, captured = _make_client(
            [httpx.Response(200, json={"object": {"sha": "def456"}})]
        )
        await client.get_branch_sha("o", "r", "feature")
        assert captured[0].url.path == "/repos/o/r/git/ref/heads/feature"


# ---------------------------------------------------------------------------
# create_branch
# ---------------------------------------------------------------------------


class TestCreateBranch:
    async def test_sends_correct_payload(self) -> None:
        client, captured = _make_client([httpx.Response(201, json={"ref": "refs/heads/new"})])
        await client.create_branch("o", "r", "new-branch", "sha123")
        body = captured[0].content
        assert b'"ref":"refs/heads/new-branch"' in body or b'"ref": "refs/heads/new-branch"' in body
        assert b"sha123" in body

    async def test_returns_none(self) -> None:
        client, _ = _make_client([httpx.Response(201, json={"ref": "refs/heads/b"})])
        result = await client.create_branch("o", "r", "b", "sha")
        assert result is None


# ---------------------------------------------------------------------------
# find_pr_by_head
# ---------------------------------------------------------------------------


class TestFindPrByHead:
    async def test_returns_first_pr_when_found(self) -> None:
        pr = {"number": 7, "html_url": "https://github.com/o/r/pull/7"}
        client, _ = _make_client([httpx.Response(200, json=[pr])])
        result = await client.find_pr_by_head("o", "r", "feature")
        assert result == pr

    async def test_returns_none_when_empty(self) -> None:
        client, _ = _make_client([httpx.Response(200, json=[])])
        result = await client.find_pr_by_head("o", "r", "no-pr")
        assert result is None

    async def test_sends_correct_params(self) -> None:
        client, captured = _make_client([httpx.Response(200, json=[])])
        await client.find_pr_by_head("acme", "widgets", "fix-bug")
        url = str(captured[0].url)
        assert "head=acme%3Afix-bug" in url or "head=acme:fix-bug" in url
        assert "state=open" in url

    async def test_raises_on_error(self) -> None:
        client, _ = _make_client([httpx.Response(500, json={"message": "err"})])
        with pytest.raises(httpx.HTTPStatusError):
            await client.find_pr_by_head("o", "r", "branch")


# ---------------------------------------------------------------------------
# create_pull_request
# ---------------------------------------------------------------------------


class TestCreatePullRequest:
    async def test_returns_pr_data(self) -> None:
        pr = {"number": 10, "html_url": "https://github.com/o/r/pull/10"}
        client, _ = _make_client([httpx.Response(201, json=pr)])
        result = await client.create_pull_request(
            "o", "r", "Title", "Body", "head", "main"
        )
        assert result["number"] == 10

    async def test_default_draft_true(self) -> None:
        client, captured = _make_client([httpx.Response(201, json={"number": 1})])
        await client.create_pull_request("o", "r", "T", "B", "h", "main")
        assert b'"draft":true' in captured[0].content or b'"draft": true' in captured[0].content

    async def test_draft_false(self) -> None:
        client, captured = _make_client([httpx.Response(201, json={"number": 1})])
        await client.create_pull_request("o", "r", "T", "B", "h", "main", draft=False)
        assert b'"draft":false' in captured[0].content or b'"draft": false' in captured[0].content

    async def test_payload_fields(self) -> None:
        client, captured = _make_client([httpx.Response(201, json={"number": 1})])
        await client.create_pull_request("o", "r", "My Title", "PR body", "feat", "main")
        body = captured[0].content
        assert b"My Title" in body
        assert b"PR body" in body
        assert b"feat" in body


# ---------------------------------------------------------------------------
# add_comment
# ---------------------------------------------------------------------------


class TestAddComment:
    async def test_returns_comment_data(self) -> None:
        client, _ = _make_client([httpx.Response(201, json={"id": 42, "body": "hi"})])
        result = await client.add_comment("o", "r", 5, "hi")
        assert result["id"] == 42

    async def test_request_url(self) -> None:
        client, captured = _make_client([httpx.Response(201, json={"id": 1})])
        await client.add_comment("org", "repo", 99, "comment")
        assert captured[0].url.path == "/repos/org/repo/issues/99/comments"

    async def test_payload(self) -> None:
        client, captured = _make_client([httpx.Response(201, json={"id": 1})])
        await client.add_comment("o", "r", 1, "hello world")
        assert b"hello world" in captured[0].content


# ---------------------------------------------------------------------------
# add_labels
# ---------------------------------------------------------------------------


class TestAddLabels:
    async def test_returns_label_list(self) -> None:
        labels_resp = [{"name": "bug"}, {"name": "urgent"}]
        client, _ = _make_client([httpx.Response(200, json=labels_resp)])
        result = await client.add_labels("o", "r", 3, ["bug", "urgent"])
        assert len(result) == 2

    async def test_request_url(self) -> None:
        client, captured = _make_client([httpx.Response(200, json=[])])
        await client.add_labels("org", "repo", 7, ["label1"])
        assert captured[0].url.path == "/repos/org/repo/issues/7/labels"

    async def test_payload(self) -> None:
        client, captured = _make_client([httpx.Response(200, json=[])])
        await client.add_labels("o", "r", 1, ["a", "b"])
        assert b'"labels"' in captured[0].content


# ---------------------------------------------------------------------------
# remove_label
# ---------------------------------------------------------------------------


class TestRemoveLabel:
    async def test_success(self) -> None:
        client, captured = _make_client([httpx.Response(200)])
        await client.remove_label("o", "r", 5, "stale")
        assert captured[0].url.path == "/repos/o/r/issues/5/labels/stale"
        assert captured[0].method == "DELETE"

    async def test_ignores_404(self) -> None:
        """Removing a label that doesn't exist should not raise."""
        client, _ = _make_client([httpx.Response(404)])
        await client.remove_label("o", "r", 5, "nonexistent")
        # No exception raised

    async def test_raises_on_other_errors(self) -> None:
        client, _ = _make_client([httpx.Response(500)])
        with pytest.raises(httpx.HTTPStatusError):
            await client.remove_label("o", "r", 5, "label")


# ---------------------------------------------------------------------------
# update_comment
# ---------------------------------------------------------------------------


class TestUpdateComment:
    async def test_returns_updated_comment(self) -> None:
        client, _ = _make_client(
            [httpx.Response(200, json={"id": 77, "body": "updated"})]
        )
        result = await client.update_comment("o", "r", 77, "updated")
        assert result["body"] == "updated"

    async def test_request_url_and_method(self) -> None:
        client, captured = _make_client(
            [httpx.Response(200, json={"id": 1, "body": "x"})]
        )
        await client.update_comment("org", "repo", 123, "new body")
        assert captured[0].url.path == "/repos/org/repo/issues/comments/123"
        assert captured[0].method == "PATCH"


# ---------------------------------------------------------------------------
# mark_ready_for_review
# ---------------------------------------------------------------------------


class TestMarkReadyForReview:
    async def test_fetches_pr_then_calls_graphql(self) -> None:
        """Should first GET the PR for node_id, then POST to GraphQL."""
        pr_resp = httpx.Response(
            200, json={"node_id": "PR_node123", "number": 15}
        )
        graphql_resp = httpx.Response(
            200,
            json={
                "data": {
                    "markPullRequestReadyForReview": {
                        "pullRequest": {"number": 15}
                    }
                }
            },
        )
        client, captured = _make_client([pr_resp, graphql_resp])
        await client.mark_ready_for_review("o", "r", 15)

        assert len(captured) == 2
        # First request: REST GET for PR data
        assert captured[0].method == "GET"
        assert "/repos/o/r/pulls/15" in captured[0].url.path
        # Second request: GraphQL POST
        assert captured[1].method == "POST"
        assert b"markPullRequestReadyForReview" in captured[1].content
        assert b"PR_node123" in captured[1].content

    async def test_raises_on_pr_fetch_error(self) -> None:
        client, _ = _make_client([httpx.Response(404, json={"message": "Not Found"})])
        with pytest.raises(httpx.HTTPStatusError):
            await client.mark_ready_for_review("o", "r", 999)

    async def test_raises_on_graphql_error(self) -> None:
        pr_resp = httpx.Response(200, json={"node_id": "N1", "number": 1})
        graphql_resp = httpx.Response(500)
        client, _ = _make_client([pr_resp, graphql_resp])
        with pytest.raises(httpx.HTTPStatusError):
            await client.mark_ready_for_review("o", "r", 1)

    async def test_returns_none(self) -> None:
        pr_resp = httpx.Response(200, json={"node_id": "N1", "number": 1})
        graphql_resp = httpx.Response(
            200,
            json={"data": {"markPullRequestReadyForReview": {"pullRequest": {"number": 1}}}},
        )
        client, _ = _make_client([pr_resp, graphql_resp])
        result = await client.mark_ready_for_review("o", "r", 1)
        assert result is None

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import httpx
import jwt
import structlog

from src.config import settings
from src.domain.exceptions import GitHubAPIError
from src.domain.ports import IGitHubAdapter

logger: structlog.BoundLogger = structlog.get_logger(__name__)

GITHUB_API_BASE = "https://api.github.com"
TOKEN_TTL_SECONDS = 50 * 60  # refresh 10 min before the 60-min GitHub expiry


@dataclass
class _CachedToken:
    token: str
    expires_at: float  # unix timestamp


@dataclass
class GitHubAdapter(IGitHubAdapter):
    """
    GitHub App adapter.

    Auth flow:
      1. Sign a JWT with the App's private key (valid 10 min).
      2. Exchange the JWT for an installation access token (valid 60 min).
      3. Cache the installation token; refresh when within 10 min of expiry.
    """

    _token_cache: dict[int, _CachedToken] = field(default_factory=dict, init=False)

    def _make_app_jwt(self) -> str:
        now = int(time.time())
        payload = {
            "iat": now - 60,  # issued slightly in the past to account for clock skew
            "exp": now + (10 * 60),
            "iss": settings.github_app_id,
        }
        private_key = settings.github_app_private_key.replace("\\n", "\n")
        return jwt.encode(payload, private_key, algorithm="RS256")

    async def _get_installation_token(self, installation_id: int) -> str:
        cached = self._token_cache.get(installation_id)
        if cached and time.time() < cached.expires_at:
            return cached.token

        app_jwt = self._make_app_jwt()
        url = f"{GITHUB_API_BASE}/app/installations/{installation_id}/access_tokens"

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {app_jwt}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )

        if resp.status_code != 201:
            raise GitHubAPIError(
                f"Failed to get installation token: {resp.text}",
                status_code=resp.status_code,
            )

        data = resp.json()
        token: str = data["token"]
        self._token_cache[installation_id] = _CachedToken(
            token=token,
            expires_at=time.time() + TOKEN_TTL_SECONDS,
        )
        return token

    def _auth_headers(self, token: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def _gh(
        self,
        method: str,
        path: str,
        installation_id: int,
        *,
        accept: str | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> httpx.Response:
        token = await self._get_installation_token(installation_id)
        headers = self._auth_headers(token)
        if accept:
            headers["Accept"] = accept

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.request(
                method,
                f"{GITHUB_API_BASE}{path}",
                headers=headers,
                json=json_body,
            )

        if resp.status_code >= 400:
            raise GitHubAPIError(
                f"GitHub API {method} {path} → {resp.status_code}: {resp.text}",
                status_code=resp.status_code,
            )
        return resp

    # ── IGitHubAdapter implementation ─────────────────────────────────────────

    async def get_pr_diff(
        self, repo_full_name: str, pr_number: int, installation_id: int
    ) -> str:
        resp = await self._gh(
            "GET",
            f"/repos/{repo_full_name}/pulls/{pr_number}",
            installation_id,
            accept="application/vnd.github.diff",
        )
        return resp.text

    async def get_pr_files(
        self,
        repo_full_name: str,
        pr_number: int,
        installation_id: int,
        *,
        head_sha: str,
    ) -> list[dict[str, str]]:
        resp = await self._gh(
            "GET",
            f"/repos/{repo_full_name}/pulls/{pr_number}/files",
            installation_id,
        )
        files_meta: list[dict[str, Any]] = resp.json()

        results: list[dict[str, str]] = []
        for f in files_meta:
            path: str = f["filename"]
            try:
                content = await self.get_file_contents(
                    repo_full_name, path, head_sha, installation_id
                )
            except GitHubAPIError:
                content = ""  # deleted or binary file — skip content
            results.append({"path": path, "content": content, "status": f.get("status", "")})

        return results

    async def get_file_contents(
        self, repo_full_name: str, path: str, ref: str, installation_id: int
    ) -> str:
        import base64

        resp = await self._gh(
            "GET",
            f"/repos/{repo_full_name}/contents/{path}?ref={ref}",
            installation_id,
        )
        data = resp.json()
        if data.get("encoding") == "base64":
            return base64.b64decode(data["content"]).decode("utf-8", errors="replace")
        return str(data.get("content", ""))

    async def post_pr_comment(
        self, repo_full_name: str, pr_number: int, body: str, installation_id: int
    ) -> int:
        resp = await self._gh(
            "POST",
            f"/repos/{repo_full_name}/issues/{pr_number}/comments",
            installation_id,
            json_body={"body": body},
        )
        return int(resp.json()["id"])

    async def update_pr_comment(
        self,
        repo_full_name: str,
        comment_id: int,
        body: str,
        installation_id: int,
    ) -> None:
        await self._gh(
            "PATCH",
            f"/repos/{repo_full_name}/issues/comments/{comment_id}",
            installation_id,
            json_body={"body": body},
        )

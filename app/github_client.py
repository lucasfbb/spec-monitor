"""Cliente mínimo da API do GitHub — só leitura de conteúdo e histórico.

O token precisa apenas de escopo de leitura de conteúdo (fine-grained PAT com
"Contents: Read" no repo). Repos públicos funcionam sem token, com rate limit
menor (60 req/h) — suficiente para poucos projetos com polling espaçado.
"""

import base64
from datetime import datetime
from typing import Any

import httpx

API_BASE = "https://api.github.com"


class GitHubError(Exception):
    pass


class GitHubClient:
    def __init__(self, token: str | None = None) -> None:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "spec-monitor",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._client = httpx.AsyncClient(base_url=API_BASE, headers=headers, timeout=30)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _get(self, url: str, params: dict[str, Any] | None = None) -> httpx.Response:
        resp = await self._client.get(url, params=params)
        if resp.status_code == 404:
            return resp
        if resp.status_code >= 400:
            raise GitHubError(f"GitHub {resp.status_code} em {url}: {resp.text[:200]}")
        return resp

    async def list_dir(self, repo: str, path: str, ref: str) -> list[dict] | None:
        """Lista arquivos de um diretório no ref. None se o caminho não existe."""
        resp = await self._get(f"/repos/{repo}/contents/{path}", params={"ref": ref})
        if resp.status_code == 404:
            return None
        data = resp.json()
        return data if isinstance(data, list) else None

    async def get_file(self, repo: str, path: str, ref: str) -> str | None:
        """Conteúdo (texto) de um arquivo no ref. None se não existe nesse ref."""
        resp = await self._get(f"/repos/{repo}/contents/{path}", params={"ref": ref})
        if resp.status_code == 404:
            return None
        data = resp.json()
        if data.get("encoding") == "base64":
            return base64.b64decode(data["content"]).decode("utf-8", errors="replace")
        return data.get("content")

    async def list_commits(
        self, repo: str, path: str, branch: str, per_page: int = 50
    ) -> list[dict]:
        """Commits que tocaram `path`, do mais novo para o mais antigo."""
        resp = await self._get(
            f"/repos/{repo}/commits",
            params={"path": path, "sha": branch, "per_page": per_page},
        )
        if resp.status_code == 404:
            return []
        commits = []
        for item in resp.json():
            commit = item.get("commit", {})
            date_str = (commit.get("committer") or commit.get("author") or {}).get("date")
            commits.append(
                {
                    "sha": item["sha"],
                    "date": datetime.fromisoformat(date_str) if date_str else None,
                    "message": (commit.get("message") or "").split("\n")[0],
                    "author": (commit.get("author") or {}).get("name") or "",
                }
            )
        return commits

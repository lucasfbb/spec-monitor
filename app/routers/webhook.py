"""Webhook do GitHub (opcional): atualização instantânea no push.

Alternativa ao polling quando o homelab é alcançável pelo GitHub (diretamente
ou via túnel, ex.: Cloudflare Tunnel/Tailscale Funnel). Se GITHUB_WEBHOOK_SECRET
estiver vazio, o endpoint responde 404 — o polling continua cobrindo tudo.
"""

import hashlib
import hmac

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from sqlalchemy import select

from app.config import get_settings
from app.db import SessionLocal
from app.models import Project
from app.sync import sync_project

router = APIRouter()


def _valid_signature(secret: str, body: bytes, signature_header: str | None) -> bool:
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature_header.removeprefix("sha256="), expected)


async def _sync_by_repo(repo_full_name: str) -> None:
    with SessionLocal() as db:
        project = db.scalar(select(Project).where(Project.repo == repo_full_name))
        if project is not None:
            await sync_project(db, project)


@router.post("/webhooks/github")
async def github_webhook(request: Request, background: BackgroundTasks):
    secret = get_settings().github_webhook_secret
    if not secret:
        raise HTTPException(status_code=404)
    body = await request.body()
    if not _valid_signature(secret, body, request.headers.get("X-Hub-Signature-256")):
        raise HTTPException(status_code=401, detail="Assinatura inválida")

    payload = await request.json()
    repo_full_name = (payload.get("repository") or {}).get("full_name")
    if not repo_full_name:
        return {"ok": True, "acao": "ignorado"}

    # Só sincroniza se o push tocou specs/STATUS do projeto correspondente.
    with SessionLocal() as db:
        project = db.scalar(select(Project).where(Project.repo == repo_full_name))
    if project is None:
        return {"ok": True, "acao": "repo não monitorado"}

    touched = []
    for commit in payload.get("commits", []):
        touched += commit.get("added", []) + commit.get("modified", []) + commit.get("removed", [])
    relevant = any(
        path == project.status_path or path.startswith(project.specs_dir.rstrip("/") + "/")
        for path in touched
    )
    if not relevant and touched:
        return {"ok": True, "acao": "push sem mudanças em specs/STATUS"}

    background.add_task(_sync_by_repo, repo_full_name)
    return {"ok": True, "acao": "sync agendado"}

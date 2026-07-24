"""Sincronização de um projeto: STATUS.md + specs/ viram snapshots e versões.

Idempotente: versões são identificadas por (arquivo, commit_sha) — rodar de novo
não duplica nada. O custo é de poucas chamadas por arquivo alterado.
"""

import logging
import re
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.github_client import GitHubClient
from app.models import Checkpoint, Project, SpecFile, SpecVersion, StatusSnapshot, SyncLog
from app.notifications import notify_sync_changes

logger = logging.getLogger(__name__)

# Convenção dos projetos monitorados (ver skill padrao-specs): checkpoints em
# docs/checkpoints/AAAA-MM-DD-checkpoint-NN.md. Projeto sem a pasta só não tem
# linha do tempo — o sync segue normal.
CHECKPOINTS_DIR = "docs/checkpoints"

_CHECKPOINT_NAME = re.compile(r"^(?:(\d{4})-(\d{2})-(\d{2})-)?checkpoint-(\d+)", re.IGNORECASE)


def _aware(dt: datetime | None) -> datetime | None:
    """SQLite devolve datetimes sem timezone — normaliza para UTC-aware."""
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def _first_heading(content: str) -> str:
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
    return ""


async def sync_project(db: Session, project: Project, *, notify: bool = False) -> SyncLog:
    """Sincroniza um projeto. Com `notify=True`, envia notificação de mudança se
    algo novo foi detectado (polling e sync manual usam True; a carga inicial na
    criação usa False para não notificar o histórico inteiro)."""
    log = SyncLog(project_id=project.id)
    client = GitHubClient(project.token)
    status_changes: list[dict] = []
    spec_changes: list[dict] = []
    checkpoint_changes: list[dict] = []
    try:
        status_changes = await _sync_status(db, project, client)
        spec_changes = await _sync_specs(db, project, client)
        checkpoint_changes = await _sync_checkpoints(db, project, client)
        log.new_status_snapshots = len(status_changes)
        log.new_spec_versions = len(spec_changes)
        log.message = (
            f"{len(spec_changes)} versão(ões) de spec, "
            f"{len(status_changes)} snapshot(s) de STATUS, "
            f"{len(checkpoint_changes)} checkpoint(s)"
        )
    except Exception as exc:  # registra a falha em vez de derrubar o poller
        logger.exception("Falha ao sincronizar projeto %s", project.repo)
        log.ok = False
        log.message = str(exc)[:1000]
    finally:
        await client.aclose()
    db.add(log)
    db.commit()

    if notify and log.ok and (status_changes or spec_changes or checkpoint_changes):
        # Notificar nunca deve derrubar o sync — falha aqui é só logada.
        try:
            notify_sync_changes(
                db,
                project,
                spec_changes=spec_changes,
                status_changes=status_changes,
                checkpoint_changes=checkpoint_changes,
            )
        except Exception:
            logger.exception("Falha ao notificar mudanças de %s", project.repo)
    return log


async def _sync_status(db: Session, project: Project, client: GitHubClient) -> list[dict]:
    known = set(
        db.scalars(
            select(StatusSnapshot.commit_sha).where(StatusSnapshot.project_id == project.id)
        )
    )
    commits = await client.list_commits(project.repo, project.status_path, project.branch)
    changes: list[dict] = []
    for commit in reversed(commits):  # do mais antigo para o mais novo
        if commit["sha"] in known or commit["date"] is None:
            continue
        content = await client.get_file(project.repo, project.status_path, ref=commit["sha"])
        if content is None:
            continue
        db.add(
            StatusSnapshot(
                project_id=project.id,
                commit_sha=commit["sha"],
                commit_date=commit["date"],
                commit_message=commit["message"],
                content=content,
            )
        )
        changes.append(
            {
                "type": "status",
                "commit_sha": commit["sha"],
                "date": commit["date"],
                "message": commit["message"],
            }
        )
    db.commit()
    return changes


async def _sync_checkpoints(db: Session, project: Project, client: GitHubClient) -> list[dict]:
    """Sincroniza docs/checkpoints/ (linha do tempo). Só a versão mais recente
    de cada arquivo — checkpoint é imutável por convenção. TEMPLATE é ignorado."""
    entries = await client.list_dir(project.repo, CHECKPOINTS_DIR, project.branch)
    if entries is None:  # projeto sem a pasta — sem linha do tempo, sem erro
        return []
    changes: list[dict] = []
    for entry in entries:
        name = entry.get("name", "")
        if entry.get("type") != "file" or not name.endswith(".md"):
            continue
        if name.upper().startswith("TEMPLATE"):
            continue

        commits = await client.list_commits(project.repo, entry["path"], project.branch)
        if not commits:
            continue
        latest = commits[0]  # mais novo primeiro

        row = db.scalar(
            select(Checkpoint).where(
                Checkpoint.project_id == project.id, Checkpoint.path == entry["path"]
            )
        )
        if row is not None and row.commit_sha == latest["sha"]:
            continue  # já temos a versão mais recente

        content = await client.get_file(project.repo, entry["path"], ref=latest["sha"])
        if content is None:
            continue

        match = _CHECKPOINT_NAME.match(name)
        number = int(match.group(4)) if match else 0
        checkpoint_date = None
        if match and match.group(1):
            checkpoint_date = datetime(
                int(match.group(1)), int(match.group(2)), int(match.group(3)), tzinfo=UTC
            )

        if row is None:
            row = Checkpoint(project_id=project.id, path=entry["path"])
            db.add(row)
        row.number = number
        row.title = _first_heading(content) or name
        row.checkpoint_date = checkpoint_date
        row.commit_sha = latest["sha"]
        row.commit_date = latest["date"]
        row.content = content
        changes.append(
            {
                "type": "checkpoint",
                "number": row.number,
                "title": row.title,
                "date": latest["date"],
            }
        )
    db.commit()
    return changes


async def _sync_specs(db: Session, project: Project, client: GitHubClient) -> list[dict]:
    entries = await client.list_dir(project.repo, project.specs_dir, project.branch)
    if entries is None:
        return []
    changes: list[dict] = []
    for entry in entries:
        if entry.get("type") != "file" or not entry.get("name", "").endswith(".md"):
            continue
        spec = db.scalar(
            select(SpecFile).where(
                SpecFile.project_id == project.id, SpecFile.path == entry["path"]
            )
        )
        if spec is None:
            spec = SpecFile(project_id=project.id, path=entry["path"])
            db.add(spec)
            db.flush()

        known = set(
            db.scalars(select(SpecVersion.commit_sha).where(SpecVersion.spec_file_id == spec.id))
        )
        commits = await client.list_commits(project.repo, entry["path"], project.branch)
        for commit in reversed(commits):
            if commit["sha"] in known or commit["date"] is None:
                continue
            content = await client.get_file(project.repo, entry["path"], ref=commit["sha"])
            if content is None:
                continue
            db.add(
                SpecVersion(
                    spec_file_id=spec.id,
                    commit_sha=commit["sha"],
                    commit_date=commit["date"],
                    commit_message=commit["message"],
                    author=commit["author"],
                    content=content,
                )
            )
            title = _first_heading(content) or entry["name"]
            changes.append(
                {
                    "type": "spec",
                    "title": title,
                    "path": entry["path"],
                    "commit_sha": commit["sha"],
                    "date": commit["date"],
                    "message": commit["message"],
                    "author": commit["author"],
                }
            )
            if spec.last_updated is None or commit["date"] >= _aware(spec.last_updated):
                spec.last_updated = commit["date"]
                spec.latest_sha = commit["sha"]
                spec.title = title
        db.commit()
    return changes

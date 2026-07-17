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


async def sync_project(db: Session, project: Project) -> SyncLog:
    log = SyncLog(project_id=project.id)
    client = GitHubClient(project.token)
    try:
        log.new_status_snapshots = await _sync_status(db, project, client)
        log.new_spec_versions = await _sync_specs(db, project, client)
        new_checkpoints = await _sync_checkpoints(db, project, client)
        log.message = (
            f"{log.new_spec_versions} versão(ões) de spec, "
            f"{log.new_status_snapshots} snapshot(s) de STATUS, "
            f"{new_checkpoints} checkpoint(s)"
        )
    except Exception as exc:  # registra a falha em vez de derrubar o poller
        logger.exception("Falha ao sincronizar projeto %s", project.repo)
        log.ok = False
        log.message = str(exc)[:1000]
    finally:
        await client.aclose()
    db.add(log)
    db.commit()
    return log


async def _sync_status(db: Session, project: Project, client: GitHubClient) -> int:
    known = set(
        db.scalars(
            select(StatusSnapshot.commit_sha).where(StatusSnapshot.project_id == project.id)
        )
    )
    commits = await client.list_commits(project.repo, project.status_path, project.branch)
    new = 0
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
        new += 1
    db.commit()
    return new


async def _sync_checkpoints(db: Session, project: Project, client: GitHubClient) -> int:
    """Sincroniza docs/checkpoints/ (linha do tempo). Só a versão mais recente
    de cada arquivo — checkpoint é imutável por convenção. TEMPLATE é ignorado."""
    entries = await client.list_dir(project.repo, CHECKPOINTS_DIR, project.branch)
    if entries is None:  # projeto sem a pasta — sem linha do tempo, sem erro
        return 0
    changed = 0
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
        changed += 1
    db.commit()
    return changed


async def _sync_specs(db: Session, project: Project, client: GitHubClient) -> int:
    entries = await client.list_dir(project.repo, project.specs_dir, project.branch)
    if entries is None:
        return 0
    new_total = 0
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
            new_total += 1
            if spec.last_updated is None or commit["date"] >= _aware(spec.last_updated):
                spec.last_updated = commit["date"]
                spec.latest_sha = commit["sha"]
                spec.title = _first_heading(content) or entry["name"]
        db.commit()
    return new_total

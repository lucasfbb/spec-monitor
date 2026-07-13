"""Sincronização de um projeto: STATUS.md + specs/ viram snapshots e versões.

Idempotente: versões são identificadas por (arquivo, commit_sha) — rodar de novo
não duplica nada. O custo é de poucas chamadas por arquivo alterado.
"""

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.github_client import GitHubClient
from app.models import Project, SpecFile, SpecVersion, StatusSnapshot, SyncLog

logger = logging.getLogger(__name__)


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
        log.message = (
            f"{log.new_spec_versions} versão(ões) de spec, "
            f"{log.new_status_snapshots} snapshot(s) de STATUS"
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

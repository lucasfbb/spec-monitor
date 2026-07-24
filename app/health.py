"""Sinais de saúde derivados do corpus — sem estado novo no banco.

Hoje: **STATUS defasado**. O STATUS.md deveria ser a foto sempre atual; se as
specs (ou checkpoints) andaram e o STATUS ficou para trás por muitos dias, é
sinal de que a foto está velha. Tudo calculado na hora a partir das datas de
commit que o sync já guarda — nada é persistido (mesma escolha da spec 00 de
calcular diff on-the-fly em vez de manter estado derivado).
"""

from datetime import UTC, datetime

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models import Checkpoint, Project, SpecFile, SpecVersion, StatusSnapshot


def _aware(dt: datetime | None) -> datetime | None:
    """SQLite devolve datetimes sem timezone — normaliza para UTC-aware."""
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def _latest(db: Session, column, whereclause, *joins) -> datetime | None:
    query = select(column)
    for join in joins:
        query = query.join(join)
    query = query.where(whereclause).order_by(desc(column)).limit(1)
    return _aware(db.scalar(query))


def status_staleness(db: Session, project: Project, threshold_days: int) -> dict:
    """Quão atrás o STATUS.md está da atividade mais recente do projeto.

    Atividade = spec versão ou checkpoint mais novo. Defasado quando essa
    atividade está `threshold_days` ou mais à frente do último commit do STATUS.
    Sem STATUS ou sem atividade, não há como medir → não defasado.
    """
    last_status = _latest(
        db, StatusSnapshot.commit_date, StatusSnapshot.project_id == project.id
    )
    last_spec = _latest(
        db, SpecVersion.commit_date, SpecFile.project_id == project.id, SpecFile
    )
    last_checkpoint = _latest(
        db, Checkpoint.commit_date, Checkpoint.project_id == project.id
    )

    activity = [d for d in (last_spec, last_checkpoint) if d is not None]
    last_activity = max(activity) if activity else None

    days_behind: int | None = None
    stale = False
    if last_status is not None and last_activity is not None and last_activity > last_status:
        days_behind = (last_activity - last_status).days
        stale = days_behind >= threshold_days

    return {
        "stale": stale,
        "days_behind": days_behind,
        "threshold_days": threshold_days,
        "last_status_update": last_status,
        "last_activity_at": last_activity,
    }

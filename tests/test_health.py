"""Detecção de STATUS defasado (app/health.py) — cálculo derivado das datas."""

from datetime import UTC, datetime, timedelta

from app.health import status_staleness
from app.models import Project, SpecFile, SpecVersion, StatusSnapshot


def _project(db, repo: str) -> Project:
    project = Project(name=repo, repo=repo)
    db.add(project)
    db.commit()
    return project


def _add_status(db, project, days_ago: int) -> None:
    db.add(
        StatusSnapshot(
            project_id=project.id,
            commit_sha=f"s{days_ago}",
            commit_date=datetime.now(UTC) - timedelta(days=days_ago),
            content="# STATUS",
        )
    )
    db.commit()


def _add_spec_version(db, project, days_ago: int) -> None:
    spec = db.query(SpecFile).filter_by(project_id=project.id).first()
    if spec is None:
        spec = SpecFile(project_id=project.id, path="specs/00.md", title="00")
        db.add(spec)
        db.flush()
    db.add(
        SpecVersion(
            spec_file_id=spec.id,
            commit_sha=f"v{days_ago}",
            commit_date=datetime.now(UTC) - timedelta(days=days_ago),
            content="conteudo",
        )
    )
    db.commit()


def test_defasado_quando_spec_muito_a_frente_do_status(db):
    project = _project(db, "lucas/defasado")
    _add_status(db, project, days_ago=30)  # STATUS parado há 30 dias
    _add_spec_version(db, project, days_ago=5)  # spec mexida há 5 dias

    result = status_staleness(db, project, threshold_days=14)
    assert result["stale"] is True
    assert result["days_behind"] == 25  # 30 - 5


def test_nao_defasado_quando_status_acompanha(db):
    project = _project(db, "lucas/em-dia")
    _add_status(db, project, days_ago=3)
    _add_spec_version(db, project, days_ago=5)  # STATUS é mais novo que a spec

    result = status_staleness(db, project, threshold_days=14)
    assert result["stale"] is False
    assert result["days_behind"] is None  # atividade não está à frente do STATUS


def test_defasado_respeita_o_limiar(db):
    project = _project(db, "lucas/no-limite")
    _add_status(db, project, days_ago=10)
    _add_spec_version(db, project, days_ago=3)  # 7 dias à frente

    assert status_staleness(db, project, threshold_days=14)["stale"] is False
    assert status_staleness(db, project, threshold_days=7)["stale"] is True


def test_sem_status_nao_mede(db):
    project = _project(db, "lucas/sem-status")
    _add_spec_version(db, project, days_ago=1)

    result = status_staleness(db, project, threshold_days=14)
    assert result["stale"] is False
    assert result["last_status_update"] is None

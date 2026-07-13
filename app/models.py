from datetime import UTC, datetime

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _now() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_admin: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(default=_now)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    repo: Mapped[str] = mapped_column(String(255), unique=True)  # "dono/repo" no GitHub
    branch: Mapped[str] = mapped_column(String(120), default="main")
    specs_dir: Mapped[str] = mapped_column(String(255), default="specs")
    status_path: Mapped[str] = mapped_column(String(255), default="STATUS.md")
    # Token de leitura (repo privado). Fica no banco do homelab — ver spec 01, seção segurança.
    token: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(default=_now)

    specs: Mapped[list["SpecFile"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    status_snapshots: Mapped[list["StatusSnapshot"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    sync_logs: Mapped[list["SyncLog"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


class SpecFile(Base):
    __tablename__ = "spec_files"
    __table_args__ = (UniqueConstraint("project_id", "path"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    path: Mapped[str] = mapped_column(String(500))
    title: Mapped[str] = mapped_column(String(500), default="")
    latest_sha: Mapped[str] = mapped_column(String(64), default="")
    last_updated: Mapped[datetime | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(default=_now)

    project: Mapped[Project] = relationship(back_populates="specs")
    versions: Mapped[list["SpecVersion"]] = relationship(
        back_populates="spec_file", cascade="all, delete-orphan"
    )


class SpecVersion(Base):
    __tablename__ = "spec_versions"
    __table_args__ = (UniqueConstraint("spec_file_id", "commit_sha"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    spec_file_id: Mapped[int] = mapped_column(ForeignKey("spec_files.id"), index=True)
    commit_sha: Mapped[str] = mapped_column(String(64))
    commit_date: Mapped[datetime] = mapped_column(index=True)
    commit_message: Mapped[str] = mapped_column(Text, default="")
    author: Mapped[str] = mapped_column(String(255), default="")
    content: Mapped[str] = mapped_column(Text)

    spec_file: Mapped[SpecFile] = relationship(back_populates="versions")


class StatusSnapshot(Base):
    __tablename__ = "status_snapshots"
    __table_args__ = (UniqueConstraint("project_id", "commit_sha"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    commit_sha: Mapped[str] = mapped_column(String(64))
    commit_date: Mapped[datetime] = mapped_column(index=True)
    commit_message: Mapped[str] = mapped_column(Text, default="")
    content: Mapped[str] = mapped_column(Text)

    project: Mapped[Project] = relationship(back_populates="status_snapshots")


class SyncLog(Base):
    __tablename__ = "sync_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    started_at: Mapped[datetime] = mapped_column(default=_now)
    ok: Mapped[bool] = mapped_column(default=True)
    message: Mapped[str] = mapped_column(Text, default="")
    new_spec_versions: Mapped[int] = mapped_column(default=0)
    new_status_snapshots: Mapped[int] = mapped_column(default=0)

    project: Mapped[Project] = relationship(back_populates="sync_logs")

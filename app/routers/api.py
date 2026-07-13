"""API JSON consumida pelo frontend (SPA em React/TanStack).

Aditiva: os templates Jinja (routers auth/ui) continuam funcionando. Os
formatos de resposta usam camelCase para bater 1:1 com os tipos do frontend
(`src/lib/api.ts`). Números/derivados vêm do banco, o frontend só renderiza.
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import (
    Project,
    ProjectMember,
    SpecFile,
    SpecVersion,
    StatusSnapshot,
    SyncLog,
    User,
)
from app.security import (
    create_session_token,
    current_user_api,
    hash_password,
    require_admin_api,
    verify_password,
)
from app.sync import sync_project

router = APIRouter(prefix="/api")


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.isoformat().replace("+00:00", "Z")


def _sync_status(db: Session, project_id: int) -> tuple[str, SyncLog | None]:
    last = db.scalar(
        select(SyncLog)
        .where(SyncLog.project_id == project_id)
        .order_by(desc(SyncLog.started_at))
        .limit(1)
    )
    if last is None:
        return "never", None
    return ("ok" if last.ok else "failed"), last


def _project_dict(db: Session, project: Project) -> dict:
    status, last = _sync_status(db, project.id)
    return {
        "id": str(project.id),
        "name": project.name,
        "repo": project.repo,
        "branch": project.branch,
        "specsDir": project.specs_dir,
        "statusPath": project.status_path,
        "lastSyncAt": _iso(last.started_at) if last else None,
        "lastSyncOk": status,
        "specsCount": len(project.specs),
    }


def _spec_dict(spec: SpecFile) -> dict:
    return {
        "id": str(spec.id),
        "projectId": str(spec.project_id),
        "path": spec.path,
        "title": spec.title or spec.path,
        "lastUpdated": _iso(spec.last_updated),
        "versionsCount": len(spec.versions),
    }


def _version_dict(v: SpecVersion) -> dict:
    return {
        "id": str(v.id),
        "specFileId": str(v.spec_file_id),
        "commitSha": v.commit_sha,
        "commitDate": _iso(v.commit_date),
        "commitMessage": v.commit_message,
        "author": v.author,
        "content": v.content,
    }


def _status_dict(s: StatusSnapshot) -> dict:
    return {
        "id": str(s.id),
        "projectId": str(s.project_id),
        "commitSha": s.commit_sha,
        "commitDate": _iso(s.commit_date),
        "commitMessage": s.commit_message,
        "content": s.content,
    }


def _get_project_or_404(db: Session, project_id: str) -> Project:
    try:
        pid = int(project_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Projeto não encontrado") from None
    project = db.get(Project, pid)
    if project is None:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    return project


def _user_can_access(db: Session, user: User, project: Project) -> bool:
    """Admin vê tudo; usuário comum só projetos onde é membro."""
    if user.is_admin:
        return True
    return (
        db.scalar(
            select(ProjectMember).where(
                ProjectMember.project_id == project.id,
                ProjectMember.user_id == user.id,
            )
        )
        is not None
    )


def _project_for_user_or_404(db: Session, project_id: str, user: User) -> Project:
    """Como _get_project_or_404, mas 404 também quando o usuário não tem acesso
    (não vaza a existência do projeto para quem não é membro)."""
    project = _get_project_or_404(db, project_id)
    if not _user_can_access(db, user, project):
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    return project


# --------------------------------------------------------------------------- #
# Auth
# --------------------------------------------------------------------------- #


class LoginBody(BaseModel):
    email: str
    password: str


def _set_session_cookie(response: Response, user_id: int) -> None:
    settings = get_settings()
    response.set_cookie(
        settings.session_cookie_name,
        create_session_token(user_id),
        max_age=settings.session_max_age_seconds,
        httponly=True,
        samesite=settings.session_cookie_samesite,  # type: ignore[arg-type]
        secure=settings.session_cookie_secure,
    )


def _user_dict(user: User) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "role": "admin" if user.is_admin else "viewer",
        "createdAt": _iso(user.created_at),
    }


@router.post("/auth/login")
def login(body: LoginBody, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.strip().lower()))
    # Mensagem única — sem enumeração de usuário.
    if user is None or not verify_password(user.password_hash, body.password):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    _set_session_cookie(response, user.id)
    return _user_dict(user)


@router.post("/auth/logout")
def logout(response: Response):
    response.delete_cookie(get_settings().session_cookie_name)
    return {"ok": True}


@router.get("/auth/me")
def me(user: User = Depends(current_user_api)):
    return _user_dict(user)


# --------------------------------------------------------------------------- #
# Projetos
# --------------------------------------------------------------------------- #


class ProjectBody(BaseModel):
    name: str
    repo: str
    branch: str = "main"
    specsDir: str = "specs"
    statusPath: str = "STATUS.md"
    token: str | None = None


@router.get("/projects")
def list_projects(user: User = Depends(current_user_api), db: Session = Depends(get_db)):
    query = select(Project).order_by(Project.name)
    if not user.is_admin:
        # Usuário comum: só os projetos em que é membro.
        query = query.join(ProjectMember).where(ProjectMember.user_id == user.id)
    projects = db.scalars(query).all()
    return [_project_dict(db, p) for p in projects]


@router.get("/projects/{project_id}")
def get_project_detail(
    project_id: str, user: User = Depends(current_user_api), db: Session = Depends(get_db)
):
    project = _project_for_user_or_404(db, project_id, user)
    latest_status = db.scalar(
        select(StatusSnapshot)
        .where(StatusSnapshot.project_id == project.id)
        .order_by(desc(StatusSnapshot.commit_date))
        .limit(1)
    )
    specs = db.scalars(
        select(SpecFile).where(SpecFile.project_id == project.id).order_by(SpecFile.path)
    ).all()
    activity = db.scalars(
        select(SpecVersion)
        .join(SpecFile)
        .where(SpecFile.project_id == project.id)
        .order_by(desc(SpecVersion.commit_date))
        .limit(12)
    ).all()
    _, last_log = _sync_status(db, project.id)
    return {
        "project": _project_dict(db, project),
        "latestStatus": _status_dict(latest_status) if latest_status else None,
        "specs": [_spec_dict(s) for s in specs],
        "recentActivity": [
            {
                "date": _iso(v.commit_date),
                "specId": str(v.spec_file_id),
                "specTitle": v.spec_file.title or v.spec_file.path,
                "commitSha": v.commit_sha,
                "commitMessage": v.commit_message,
                "author": v.author,
            }
            for v in activity
        ],
        "lastSync": {
            "startedAt": _iso(last_log.started_at),
            "ok": last_log.ok,
            "message": last_log.message,
        }
        if last_log
        else None,
    }


@router.post("/projects", status_code=201)
async def create_project(
    body: ProjectBody, admin: User = Depends(require_admin_api), db: Session = Depends(get_db)
):
    repo = body.repo.strip().removeprefix("https://github.com/").strip("/")
    if db.scalar(select(Project).where(Project.repo == repo)):
        raise HTTPException(status_code=400, detail="Repositório já cadastrado")
    project = Project(
        name=body.name.strip(),
        repo=repo,
        branch=body.branch.strip() or "main",
        specs_dir=body.specsDir.strip().strip("/") or "specs",
        status_path=body.statusPath.strip().strip("/") or "STATUS.md",
        token=(body.token or "").strip() or None,
    )
    db.add(project)
    db.commit()
    await sync_project(db, project)  # primeira carga já na criação
    return _project_dict(db, project)


@router.post("/projects/{project_id}/sync")
async def manual_sync(
    project_id: str, admin: User = Depends(require_admin_api), db: Session = Depends(get_db)
):
    project = _get_project_or_404(db, project_id)
    await sync_project(db, project)
    return _project_dict(db, project)


@router.delete("/projects/{project_id}", status_code=204)
def delete_project(
    project_id: str, admin: User = Depends(require_admin_api), db: Session = Depends(get_db)
):
    project = _get_project_or_404(db, project_id)
    db.delete(project)
    db.commit()


# --------------------------------------------------------------------------- #
# Membros do projeto (admin) — quem pode ver aquele projeto
# --------------------------------------------------------------------------- #


class MemberBody(BaseModel):
    userId: str


@router.get("/projects/{project_id}/members")
def list_members(
    project_id: str, admin: User = Depends(require_admin_api), db: Session = Depends(get_db)
):
    project = _get_project_or_404(db, project_id)
    members = db.scalars(
        select(User)
        .join(ProjectMember, ProjectMember.user_id == User.id)
        .where(ProjectMember.project_id == project.id)
        .order_by(User.email)
    ).all()
    return [_user_dict(u) for u in members]


@router.post("/projects/{project_id}/members", status_code=201)
def add_member(
    project_id: str,
    body: MemberBody,
    admin: User = Depends(require_admin_api),
    db: Session = Depends(get_db),
):
    project = _get_project_or_404(db, project_id)
    try:
        uid = int(body.userId)
    except ValueError:
        raise HTTPException(status_code=400, detail="Usuário inválido") from None
    target = db.get(User, uid)
    if target is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    exists = db.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project.id, ProjectMember.user_id == uid
        )
    )
    if exists is None:
        db.add(ProjectMember(project_id=project.id, user_id=uid))
        db.commit()
    return _user_dict(target)


@router.delete("/projects/{project_id}/members/{user_id}", status_code=204)
def remove_member(
    project_id: str,
    user_id: str,
    admin: User = Depends(require_admin_api),
    db: Session = Depends(get_db),
):
    project = _get_project_or_404(db, project_id)
    try:
        uid = int(user_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Membro não encontrado") from None
    member = db.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project.id, ProjectMember.user_id == uid
        )
    )
    if member is not None:
        db.delete(member)
        db.commit()


# --------------------------------------------------------------------------- #
# Specs
# --------------------------------------------------------------------------- #


@router.get("/projects/{project_id}/specs/{spec_id}")
def get_spec_detail(
    project_id: str,
    spec_id: str,
    user: User = Depends(current_user_api),
    db: Session = Depends(get_db),
):
    project = _project_for_user_or_404(db, project_id, user)
    try:
        sid = int(spec_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Spec não encontrada") from None
    spec = db.get(SpecFile, sid)
    if spec is None or spec.project_id != project.id:
        raise HTTPException(status_code=404, detail="Spec não encontrada")
    versions = db.scalars(
        select(SpecVersion)
        .where(SpecVersion.spec_file_id == spec.id)
        .order_by(desc(SpecVersion.commit_date))
    ).all()
    return {
        "spec": _spec_dict(spec),
        "project": _project_dict(db, project),
        "versions": [_version_dict(v) for v in versions],
    }


# --------------------------------------------------------------------------- #
# Usuários (admin)
# --------------------------------------------------------------------------- #


class UserBody(BaseModel):
    email: str
    password: str
    isAdmin: bool = False


@router.get("/users")
def list_users(admin: User = Depends(require_admin_api), db: Session = Depends(get_db)):
    users = db.scalars(select(User).order_by(User.created_at)).all()
    return [_user_dict(u) for u in users]


@router.post("/users", status_code=201)
def create_user(
    body: UserBody, admin: User = Depends(require_admin_api), db: Session = Depends(get_db)
):
    email = body.email.strip().lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")
    user = User(email=email, password_hash=hash_password(body.password), is_admin=body.isAdmin)
    db.add(user)
    db.commit()
    return _user_dict(user)

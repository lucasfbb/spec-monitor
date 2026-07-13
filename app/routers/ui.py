from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Project, SpecFile, SpecVersion, StatusSnapshot, SyncLog, User
from app.rendering import render_markdown, unified_diff_lines
from app.security import current_user, require_admin
from app.sync import sync_project

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def _project_or_404(db: Session, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    return project


@router.get("/")
def dashboard(request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
    projects = db.scalars(select(Project).order_by(Project.name)).all()
    cards = []
    for project in projects:
        last_log = db.scalar(
            select(SyncLog)
            .where(SyncLog.project_id == project.id)
            .order_by(desc(SyncLog.started_at))
            .limit(1)
        )
        specs_count = len(project.specs)
        last_activity = db.scalar(
            select(SpecVersion.commit_date)
            .join(SpecFile)
            .where(SpecFile.project_id == project.id)
            .order_by(desc(SpecVersion.commit_date))
            .limit(1)
        )
        cards.append(
            {
                "project": project,
                "last_log": last_log,
                "specs_count": specs_count,
                "last_activity": last_activity,
            }
        )
    return templates.TemplateResponse(
        request, "dashboard.html", {"cards": cards, "user": user}
    )


@router.get("/projetos/novo")
def new_project_page(request: Request, admin: User = Depends(require_admin)):
    return templates.TemplateResponse(request, "projeto_novo.html", {"user": admin, "erro": None})


@router.post("/projetos/novo")
async def create_project(
    request: Request,
    name: str = Form(...),
    repo: str = Form(...),
    branch: str = Form("main"),
    specs_dir: str = Form("specs"),
    status_path: str = Form("STATUS.md"),
    token: str = Form(""),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    repo = repo.strip().removeprefix("https://github.com/").strip("/")
    if db.scalar(select(Project).where(Project.repo == repo)):
        return templates.TemplateResponse(
            request,
            "projeto_novo.html",
            {"user": admin, "erro": "Repositório já cadastrado"},
            status_code=400,
        )
    project = Project(
        name=name.strip(),
        repo=repo,
        branch=branch.strip() or "main",
        specs_dir=specs_dir.strip().strip("/") or "specs",
        status_path=status_path.strip().strip("/") or "STATUS.md",
        token=token.strip() or None,
    )
    db.add(project)
    db.commit()
    await sync_project(db, project)  # primeira carga já na criação
    return RedirectResponse(f"/projetos/{project.id}", status_code=303)


@router.get("/projetos/{project_id}")
def project_page(
    project_id: int,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    project = _project_or_404(db, project_id)
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
        .limit(20)
    ).all()
    last_log = db.scalar(
        select(SyncLog)
        .where(SyncLog.project_id == project.id)
        .order_by(desc(SyncLog.started_at))
        .limit(1)
    )
    return templates.TemplateResponse(
        request,
        "projeto.html",
        {
            "user": user,
            "project": project,
            "status_html": render_markdown(latest_status.content) if latest_status else None,
            "latest_status": latest_status,
            "specs": specs,
            "activity": activity,
            "last_log": last_log,
        },
    )


@router.post("/projetos/{project_id}/sync")
async def manual_sync(
    project_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)
):
    project = _project_or_404(db, project_id)
    await sync_project(db, project)
    return RedirectResponse(f"/projetos/{project_id}", status_code=303)


@router.post("/projetos/{project_id}/excluir")
def delete_project(
    project_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)
):
    project = _project_or_404(db, project_id)
    db.delete(project)
    db.commit()
    return RedirectResponse("/", status_code=303)


@router.get("/projetos/{project_id}/specs/{spec_id}")
def spec_page(
    project_id: int,
    spec_id: int,
    request: Request,
    versao: int | None = None,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    project = _project_or_404(db, project_id)
    spec = db.get(SpecFile, spec_id)
    if spec is None or spec.project_id != project.id:
        raise HTTPException(status_code=404, detail="Spec não encontrada")
    versions = db.scalars(
        select(SpecVersion)
        .where(SpecVersion.spec_file_id == spec.id)
        .order_by(desc(SpecVersion.commit_date))
    ).all()
    selected = None
    if versao is not None:
        selected = next((v for v in versions if v.id == versao), None)
    if selected is None and versions:
        selected = versions[0]
    return templates.TemplateResponse(
        request,
        "spec.html",
        {
            "user": user,
            "project": project,
            "spec": spec,
            "versions": versions,
            "selected": selected,
            "content_html": render_markdown(selected.content) if selected else None,
        },
    )


@router.get("/projetos/{project_id}/specs/{spec_id}/diff")
def spec_diff(
    project_id: int,
    spec_id: int,
    request: Request,
    de: int,
    para: int,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    project = _project_or_404(db, project_id)
    spec = db.get(SpecFile, spec_id)
    if spec is None or spec.project_id != project.id:
        raise HTTPException(status_code=404, detail="Spec não encontrada")
    old = db.get(SpecVersion, de)
    new = db.get(SpecVersion, para)
    if not old or not new or old.spec_file_id != spec.id or new.spec_file_id != spec.id:
        raise HTTPException(status_code=404, detail="Versão não encontrada")
    lines = unified_diff_lines(
        old.content, new.content, old.commit_sha[:8], new.commit_sha[:8]
    )
    return templates.TemplateResponse(
        request,
        "diff.html",
        {"user": user, "project": project, "spec": spec, "old": old, "new": new, "lines": lines},
    )

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import User
from app.security import create_session_token, hash_password, require_admin, verify_password

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {"erro": None})


@router.post("/login")
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    # Mensagem única — não distinguir "usuário não existe" de "senha errada".
    if user is None or not verify_password(user.password_hash, password):
        return templates.TemplateResponse(
            request, "login.html", {"erro": "Credenciais inválidas"}, status_code=401
        )
    settings = get_settings()
    response = RedirectResponse("/", status_code=303)
    response.set_cookie(
        settings.session_cookie_name,
        create_session_token(user.id),
        max_age=settings.session_max_age_seconds,
        httponly=True,
        samesite="lax",
    )
    return response


@router.post("/logout")
def logout():
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(get_settings().session_cookie_name)
    return response


@router.get("/admin/usuarios")
def users_page(request: Request, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    users = db.scalars(select(User).order_by(User.created_at)).all()
    return templates.TemplateResponse(
        request, "usuarios.html", {"users": users, "user": admin, "erro": None}
    )


@router.post("/admin/usuarios")
def create_user(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    is_admin: bool = Form(False),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    email = email.strip().lower()
    if db.scalar(select(User).where(User.email == email)):
        users = db.scalars(select(User).order_by(User.created_at)).all()
        return templates.TemplateResponse(
            request,
            "usuarios.html",
            {"users": users, "user": admin, "erro": "E-mail já cadastrado"},
            status_code=400,
        )
    db.add(User(email=email, password_hash=hash_password(password), is_admin=is_admin))
    db.commit()
    return RedirectResponse("/admin/usuarios", status_code=303)

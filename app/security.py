from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, HTTPException, Request
from itsdangerous import BadSignature, URLSafeTimedSerializer
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import User

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(get_settings().secret_key, salt="session")


def create_session_token(user_id: int) -> str:
    return _serializer().dumps({"uid": user_id})


def read_session_token(token: str) -> int | None:
    settings = get_settings()
    try:
        data = _serializer().loads(token, max_age=settings.session_max_age_seconds)
    except BadSignature:
        return None
    return data.get("uid")


def _redirect_to_login() -> HTTPException:
    # HTTPException com Location vira redirect — suficiente para UI server-rendered.
    return HTTPException(status_code=303, headers={"Location": "/login"})


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(get_settings().session_cookie_name)
    if not token:
        raise _redirect_to_login()
    user_id = read_session_token(token)
    if user_id is None:
        raise _redirect_to_login()
    user = db.get(User, user_id)
    if user is None:
        raise _redirect_to_login()
    return user


def require_admin(user: User = Depends(current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Apenas administradores")
    return user


# --- Variantes para a API JSON: 401/403 em vez de redirect para /login ---


def current_user_api(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(get_settings().session_cookie_name)
    user_id = read_session_token(token) if token else None
    user = db.get(User, user_id) if user_id is not None else None
    if user is None:
        raise HTTPException(status_code=401, detail="Não autenticado")
    return user


def require_admin_api(user: User = Depends(current_user_api)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Apenas administradores")
    return user

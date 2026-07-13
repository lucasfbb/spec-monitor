import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from app.config import get_settings
from app.db import Base, SessionLocal, engine
from app.models import Project, User
from app.routers import api, auth, ui, webhook
from app.security import hash_password
from app.sync import sync_project

logger = logging.getLogger(__name__)


def seed_admin() -> None:
    """Garante o super admin definido por env (cria ou promove/atualiza senha)."""
    settings = get_settings()
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == settings.admin_email))
        if user is None:
            db.add(
                User(
                    email=settings.admin_email,
                    password_hash=hash_password(settings.admin_password),
                    is_admin=True,
                )
            )
        else:
            user.is_admin = True
            user.password_hash = hash_password(settings.admin_password)
        db.commit()


async def _poll_loop() -> None:
    interval = max(get_settings().sync_interval_minutes, 1) * 60
    while True:
        await asyncio.sleep(interval)
        with SessionLocal() as db:
            projects = db.scalars(select(Project)).all()
            for project in projects:
                await sync_project(db, project)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    seed_admin()
    poller = asyncio.create_task(_poll_loop())
    yield
    poller.cancel()


app = FastAPI(title="spec-monitor", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(api.router)
app.include_router(auth.router)
app.include_router(webhook.router)
app.include_router(ui.router)

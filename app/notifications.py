"""Notificações de mudança por e-mail (canal v0).

Gatilho: um ciclo de polling detectou versões de spec / snapshots de STATUS /
checkpoints novos num projeto. Destinatários: admins + membros do projeto (quem
já pode ver aquele projeto no painel). Canal: SMTP via stdlib — sem dependência
nova. Desativado silenciosamente se SMTP não estiver configurado (mesma lógica
do webhook sem segredo). Telegram e outros canais ficam para depois (STATUS, M1).

Só o polling e o sync manual notificam; a carga inicial de um projeto novo NÃO
(senão o primeiro e-mail listaria todo o histórico como "novidade").
"""

import logging
import smtplib
from datetime import UTC, datetime
from email.message import EmailMessage

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.health import status_staleness
from app.models import Project, ProjectMember, User

logger = logging.getLogger(__name__)


def recipients_for(db: Session, project: Project) -> list[str]:
    """Admins + membros do projeto, sem duplicar. Reusa o RBAC por projeto:
    quem é notificado é exatamente quem enxerga o projeto no painel."""
    admins = db.scalars(select(User.email).where(User.is_admin)).all()
    members = db.scalars(
        select(User.email)
        .join(ProjectMember, ProjectMember.user_id == User.id)
        .where(ProjectMember.project_id == project.id)
    ).all()
    return sorted({e for e in (*admins, *members) if e})


def _fmt_date(dt: datetime | None) -> str:
    if dt is None:
        return "—"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.strftime("%d/%m/%Y %H:%M")


def _lines(changes: list[dict]) -> list[str]:
    out = []
    for c in changes:
        if c["type"] == "spec":
            out.append(f"  • spec «{c['title']}» — {c['message']} ({c['author']})")
        elif c["type"] == "status":
            out.append(f"  • STATUS.md — {c['message']}")
        elif c["type"] == "checkpoint":
            out.append(f"  • checkpoint #{c['number']:02d} — {c['title']}")
    return out


def build_digest(
    db: Session,
    project: Project,
    *,
    spec_changes: list[dict],
    status_changes: list[dict],
    checkpoint_changes: list[dict],
    settings: Settings,
) -> tuple[str, str, str]:
    """(assunto, corpo texto, corpo html) do e-mail de mudança."""
    total = len(spec_changes) + len(status_changes) + len(checkpoint_changes)
    subject = f"[spec-monitor] {project.name}: {total} mudança(s) nas specs"

    parts = []
    if spec_changes:
        parts.append(f"Specs ({len(spec_changes)}):")
        parts += _lines(spec_changes)
    if status_changes:
        parts.append(f"STATUS ({len(status_changes)}):")
        parts += _lines(status_changes)
    if checkpoint_changes:
        parts.append(f"Checkpoints ({len(checkpoint_changes)}):")
        parts += _lines(checkpoint_changes)

    # Aviso de STATUS defasado — cruza as duas features: se as specs andaram e o
    # STATUS ficou para trás, o e-mail já chama atenção para isso.
    stale = status_staleness(db, project, settings.status_stale_days)
    warning = ""
    if stale["stale"]:
        warning = (
            f"⚠️  STATUS.md pode estar defasado: {stale['days_behind']} dia(s) "
            f"atrás da atividade mais recente das specs."
        )

    link = ""
    if settings.app_base_url.strip():
        base = settings.app_base_url.strip().rstrip("/")
        link = f"{base}/projects/{project.id}"

    text_lines = [
        f"Mudanças detectadas em {project.name} ({project.repo}).",
        "",
        *parts,
    ]
    if warning:
        text_lines += ["", warning]
    if link:
        text_lines += ["", f"Ver no painel: {link}"]
    text_lines += ["", "— spec-monitor"]
    text_body = "\n".join(text_lines)

    def esc(s: str) -> str:
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    html_items = "".join(f"<li>{esc(line.strip())}</li>" for line in _all_lines(
        spec_changes, status_changes, checkpoint_changes
    ))
    html_warning = f'<p style="color:#b45309">{esc(warning)}</p>' if warning else ""
    html_link = f'<p><a href="{esc(link)}">Ver no painel</a></p>' if link else ""
    html_body = (
        f"<h2>{esc(project.name)}</h2>"
        f'<p style="color:#555">{esc(project.repo)} — {total} mudança(s)</p>'
        f"<ul>{html_items}</ul>"
        f"{html_warning}{html_link}"
        f'<p style="color:#888;font-size:12px">— spec-monitor</p>'
    )
    return subject, text_body, html_body


def _all_lines(*groups: list[dict]) -> list[str]:
    out: list[str] = []
    for g in groups:
        out += [ln.strip() for ln in _lines(g)]
    return out


def send_email(
    settings: Settings, recipients: list[str], subject: str, text_body: str, html_body: str
) -> None:
    """Envia via SMTP. Fronteira única com o mundo de e-mail (mockável em teste)."""
    msg = EmailMessage()
    msg["From"] = settings.smtp_from.strip() or settings.smtp_user
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as server:
        if settings.smtp_use_tls:
            server.starttls()
        if settings.smtp_user:
            server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(msg)


def notify_sync_changes(
    db: Session,
    project: Project,
    *,
    spec_changes: list[dict],
    status_changes: list[dict],
    checkpoint_changes: list[dict],
) -> bool:
    """Compõe e envia o digest. Retorna True se enviou. No-op (False) se SMTP
    não configurado, sem destinatários, ou sem mudanças."""
    settings = get_settings()
    if not settings.notifications_enabled:
        return False
    if not (spec_changes or status_changes or checkpoint_changes):
        return False
    recipients = recipients_for(db, project)
    if not recipients:
        return False

    subject, text_body, html_body = build_digest(
        db,
        project,
        spec_changes=spec_changes,
        status_changes=status_changes,
        checkpoint_changes=checkpoint_changes,
        settings=settings,
    )
    try:
        send_email(settings, recipients, subject, text_body, html_body)
        logger.info("Notificação enviada para %d destinatário(s): %s", len(recipients), project.repo)
        return True
    except Exception:
        logger.exception("Falha ao enviar notificação de %s", project.repo)
        return False

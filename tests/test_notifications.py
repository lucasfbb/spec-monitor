"""Notificações por e-mail: gatilho, destinatários e o não-notificar na carga
inicial. SMTP habilitado por env; o envio real (send_email) é mockado."""

import pytest
import respx

from app import notifications
from app.config import Settings, get_settings
from app.models import Project, User
from app.security import hash_password
from app.sync import sync_project
from tests.test_sync import _mock_github


def test_send_email_com_host_vazio_da_erro_claro():
    # SMTP_HOST vazio → em vez do críptico "please run connect() first" do
    # smtplib, um erro que aponta a causa (container criado sem as vars).
    settings = Settings(smtp_host="")
    with pytest.raises(RuntimeError, match="SMTP_HOST está vazio"):
        notifications.send_email(settings, ["a@b.com"], "s", "t", "<p>t</p>")


@pytest.fixture()
def smtp_enabled(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.local")
    monkeypatch.setenv("APP_BASE_URL", "https://spec.local")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture()
def sent(monkeypatch):
    """Captura chamadas a send_email em vez de falar SMTP de verdade."""
    calls: list[dict] = []

    def fake_send(settings, recipients, subject, text_body, html_body):
        calls.append(
            {
                "recipients": recipients,
                "subject": subject,
                "text": text_body,
                "html": html_body,
            }
        )

    monkeypatch.setattr(notifications, "send_email", fake_send)
    return calls


def _admin(db) -> User:
    admin = User(email="admin@ex.com", password_hash=hash_password("x"), is_admin=True)
    db.add(admin)
    db.commit()
    return admin


async def test_carga_inicial_nao_notifica(db, smtp_enabled, sent):
    _admin(db)
    project = Project(name="Novo", repo="lucas/notif-init")
    db.add(project)
    db.commit()

    with respx.mock(assert_all_called=False) as m:
        _mock_github(m, "lucas/notif-init")
        await sync_project(db, project, notify=False)  # como na criação do projeto

    assert sent == []


async def test_mudanca_incremental_notifica(db, smtp_enabled, sent):
    _admin(db)
    project = Project(name="Incremental", repo="lucas/notif-inc")
    db.add(project)
    db.commit()

    with respx.mock(assert_all_called=False) as m:
        _mock_github(m, "lucas/notif-inc")
        await sync_project(db, project, notify=False)  # baseline, sem notificar

    with respx.mock(assert_all_called=False) as m:
        _mock_github(m, "lucas/notif-inc", spec_v2=True)  # nova versão da spec 00
        await sync_project(db, project, notify=True)

    assert len(sent) == 1
    msg = sent[0]
    assert msg["recipients"] == ["admin@ex.com"]
    assert "1 mudança" in msg["subject"]
    assert "Spec 00 — Visão" in msg["text"]
    assert "https://spec.local/projects/" in msg["text"]


async def test_sem_mudanca_nao_notifica(db, smtp_enabled, sent):
    _admin(db)
    project = Project(name="Estavel", repo="lucas/notif-estavel")
    db.add(project)
    db.commit()

    with respx.mock(assert_all_called=False) as m:
        _mock_github(m, "lucas/notif-estavel")
        await sync_project(db, project, notify=False)
    with respx.mock(assert_all_called=False) as m:
        _mock_github(m, "lucas/notif-estavel")  # nada novo
        await sync_project(db, project, notify=True)

    assert sent == []


async def test_desativado_sem_smtp_nao_notifica(db, sent):
    get_settings.cache_clear()  # garante settings padrão (sem SMTP_HOST)
    _admin(db)
    project = Project(name="SemSmtp", repo="lucas/notif-sem-smtp")
    db.add(project)
    db.commit()

    with respx.mock(assert_all_called=False) as m:
        _mock_github(m, "lucas/notif-sem-smtp")
        await sync_project(db, project, notify=False)
    with respx.mock(assert_all_called=False) as m:
        _mock_github(m, "lucas/notif-sem-smtp", spec_v2=True)
        await sync_project(db, project, notify=True)

    assert sent == []

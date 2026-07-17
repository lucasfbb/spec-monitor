"""Sync contra API do GitHub mockada (respx) — criação e idempotência."""

import base64
import json

import respx
from httpx import Response

from app.models import Project, SpecFile, SpecVersion, StatusSnapshot
from app.sync import sync_project

REPO = "lucas/exemplo"
REPO2 = "lucas/exemplo2"
REPO_NAO_MONITORADO = "outro/nao-monitorado"


def _content_body(text: str) -> dict:
    return {
        "encoding": "base64",
        "content": base64.b64encode(text.encode()).decode(),
    }


def _commit(sha: str, date: str, message: str) -> dict:
    return {
        "sha": sha,
        "commit": {
            "message": message,
            "author": {"name": "Lucas", "date": date},
            "committer": {"date": date},
        },
    }


def _mock_github(respx_mock, repo: str, spec_v2: bool = False, checkpoints: bool = False):
    # Histórico do STATUS.md
    respx_mock.get(
        f"https://api.github.com/repos/{repo}/commits",
        params={"path": "STATUS.md"},
    ).mock(
        return_value=Response(
            200, json=[_commit("aaa111", "2026-07-10T12:00:00Z", "atualiza status")]
        )
    )

    # Pasta de checkpoints (convenção docs/checkpoints). Sem a flag: 404 —
    # projeto sem linha do tempo, sync segue normal.
    if not checkpoints:
        respx_mock.get(f"https://api.github.com/repos/{repo}/contents/docs/checkpoints").mock(
            return_value=Response(404)
        )
    else:
        respx_mock.get(f"https://api.github.com/repos/{repo}/contents/docs/checkpoints").mock(
            return_value=Response(
                200,
                json=[
                    {
                        "name": "TEMPLATE.md",
                        "path": "docs/checkpoints/TEMPLATE.md",
                        "type": "file",
                    },
                    {
                        "name": "2026-07-12-checkpoint-01.md",
                        "path": "docs/checkpoints/2026-07-12-checkpoint-01.md",
                        "type": "file",
                    },
                ],
            )
        )
        respx_mock.get(
            f"https://api.github.com/repos/{repo}/commits",
            params={"path": "docs/checkpoints/2026-07-12-checkpoint-01.md"},
        ).mock(
            return_value=Response(
                200, json=[_commit("ddd444", "2026-07-12T15:00:00Z", "checkpoint #01")]
            )
        )
        respx_mock.get(
            f"https://api.github.com/repos/{repo}/contents/docs/checkpoints/2026-07-12-checkpoint-01.md"
        ).mock(
            return_value=Response(
                200, json=_content_body("# Checkpoint #01 — fundação\n\nTudo de pé.")
            )
        )
    respx_mock.get(f"https://api.github.com/repos/{repo}/contents/STATUS.md").mock(
        return_value=Response(200, json=_content_body("# STATUS\n\nEtapa A em andamento"))
    )

    # Listagem da pasta specs/
    respx_mock.get(f"https://api.github.com/repos/{repo}/contents/specs").mock(
        return_value=Response(
            200,
            json=[
                {"name": "00-visao.md", "path": "specs/00-visao.md", "type": "file"},
                {"name": "rascunho.txt", "path": "specs/rascunho.txt", "type": "file"},
            ],
        )
    )

    # Histórico e conteúdo da spec
    commits = [_commit("bbb222", "2026-07-09T10:00:00Z", "cria spec 00")]
    if spec_v2:
        commits.insert(0, _commit("ccc333", "2026-07-11T09:00:00Z", "revisa spec 00"))
    respx_mock.get(
        f"https://api.github.com/repos/{repo}/commits",
        params={"path": "specs/00-visao.md"},
    ).mock(return_value=Response(200, json=commits))

    def spec_content(request):
        ref = request.url.params.get("ref")
        text = "# Spec 00 — Visão\n\nv2" if ref == "ccc333" else "# Spec 00 — Visão\n\nv1"
        return Response(200, json=_content_body(text))

    respx_mock.get(f"https://api.github.com/repos/{repo}/contents/specs/00-visao.md").mock(
        side_effect=spec_content
    )


async def test_sync_cria_snapshots_e_versoes(db):
    project = Project(name="Exemplo", repo=REPO)
    db.add(project)
    db.commit()

    with respx.mock(assert_all_called=False) as respx_mock:
        _mock_github(respx_mock, REPO)
        log = await sync_project(db, project)

    assert log.ok, log.message
    assert log.new_status_snapshots == 1
    assert log.new_spec_versions == 1

    spec = db.query(SpecFile).filter_by(project_id=project.id).one()
    assert spec.title == "Spec 00 — Visão"
    assert spec.latest_sha == "bbb222"
    # .txt ignorado
    assert db.query(SpecFile).count() == 1


async def test_sync_e_idempotente_e_detecta_nova_versao(db):
    project = Project(name="Exemplo2", repo=REPO2)
    db.add(project)
    db.commit()

    with respx.mock(assert_all_called=False) as respx_mock:
        _mock_github(respx_mock, REPO2)
        await sync_project(db, project)
        log2 = await sync_project(db, project)  # nada novo

    assert log2.ok
    assert log2.new_spec_versions == 0
    assert log2.new_status_snapshots == 0

    with respx.mock(assert_all_called=False) as respx_mock:
        _mock_github(respx_mock, REPO2, spec_v2=True)  # commit novo na spec
        log3 = await sync_project(db, project)

    assert log3.new_spec_versions == 1
    spec = db.query(SpecFile).filter_by(project_id=project.id).one()
    assert spec.latest_sha == "ccc333"
    versions = (
        db.query(SpecVersion).filter_by(spec_file_id=spec.id).order_by(SpecVersion.commit_date)
    ).all()
    assert [v.commit_sha for v in versions] == ["bbb222", "ccc333"]
    assert db.query(StatusSnapshot).filter_by(project_id=project.id).count() == 1


async def test_sync_checkpoints_cria_linha_do_tempo(db):
    from app.models import Checkpoint

    project = Project(name="ComCheckpoints", repo="lucas/com-checkpoints")
    db.add(project)
    db.commit()

    with respx.mock(assert_all_called=False) as respx_mock:
        _mock_github(respx_mock, "lucas/com-checkpoints", checkpoints=True)
        log = await sync_project(db, project)
        # Segunda rodada: nada muda (idempotente — mesmo commit_sha).
        await sync_project(db, project)

    assert log.ok, log.message
    rows = db.query(Checkpoint).filter_by(project_id=project.id).all()
    assert len(rows) == 1  # TEMPLATE.md ignorado
    cp = rows[0]
    assert cp.number == 1
    assert cp.title == "Checkpoint #01 — fundação"
    assert cp.checkpoint_date is not None and cp.checkpoint_date.day == 12
    assert cp.commit_sha == "ddd444"


def test_webhook_exige_assinatura_valida(client):
    payload = {"repository": {"full_name": REPO_NAO_MONITORADO}, "commits": []}
    body = json.dumps(payload).encode()

    resp = client.post(
        "/webhooks/github",
        content=body,
        headers={"X-Hub-Signature-256": "sha256=invalida", "Content-Type": "application/json"},
    )
    assert resp.status_code == 401

    import hashlib
    import hmac

    signature = hmac.new(b"segredo-webhook-teste", body, hashlib.sha256).hexdigest()
    resp = client.post(
        "/webhooks/github",
        content=body,
        headers={
            "X-Hub-Signature-256": f"sha256={signature}",
            "Content-Type": "application/json",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["acao"] == "repo não monitorado"

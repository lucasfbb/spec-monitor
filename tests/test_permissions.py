"""Controle de acesso por projeto: admin vê tudo, membro só os seus."""

from app.models import Project, User
from app.security import hash_password

FRIEND_PASSWORD = "senha-do-amigo-123"


def _login(client, email, password):
    r = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
        follow_redirects=False,
    )
    assert r.status_code == 200, r.text


def _seed_project_and_friend(db, suffix):
    """Dados únicos por teste (o SQLite de teste persiste entre eles)."""
    email = f"amigo-{suffix}@test.local"
    project = Project(name=f"Privado {suffix}", repo=f"lucas/privado-{suffix}")
    friend = User(email=email, password_hash=hash_password(FRIEND_PASSWORD), is_admin=False)
    db.add_all([project, friend])
    db.commit()
    return project.id, friend.id, email


def test_membro_so_ve_projeto_apos_ser_adicionado(client, db):
    project_id, friend_id, friend_email = _seed_project_and_friend(db, "ver")

    # Admin enxerga o projeto.
    _login(client, "admin@test.local", "senha-de-teste-123")
    assert any(p["id"] == str(project_id) for p in client.get("/api/projects").json())

    # Amigo (não-membro): lista vazia e 404 no detalhe (não vaza existência).
    _login(client, friend_email, FRIEND_PASSWORD)
    assert client.get("/api/projects").json() == []
    assert client.get(f"/api/projects/{project_id}").status_code == 404

    # Admin adiciona o amigo como membro.
    _login(client, "admin@test.local", "senha-de-teste-123")
    r = client.post(f"/api/projects/{project_id}/members", json={"userId": str(friend_id)})
    assert r.status_code == 201
    assert [m["email"] for m in client.get(f"/api/projects/{project_id}/members").json()] == [
        friend_email
    ]

    # Agora o amigo vê o projeto e o detalhe.
    _login(client, friend_email, FRIEND_PASSWORD)
    assert [p["id"] for p in client.get("/api/projects").json()] == [str(project_id)]
    assert client.get(f"/api/projects/{project_id}").status_code == 200

    # Admin remove o acesso — o amigo deixa de ver.
    _login(client, "admin@test.local", "senha-de-teste-123")
    assert client.delete(f"/api/projects/{project_id}/members/{friend_id}").status_code == 204
    _login(client, friend_email, FRIEND_PASSWORD)
    assert client.get("/api/projects").json() == []


def test_nao_admin_nao_gerencia_membros(client, db):
    project_id, friend_id, friend_email = _seed_project_and_friend(db, "gerencia")
    _login(client, friend_email, FRIEND_PASSWORD)
    # Endpoints de gestão são admin-only.
    assert client.get(f"/api/projects/{project_id}/members").status_code == 403
    assert (
        client.post(
            f"/api/projects/{project_id}/members", json={"userId": str(friend_id)}
        ).status_code
        == 403
    )
    assert client.post("/api/projects", json={"name": "x", "repo": "a/b"}).status_code == 403

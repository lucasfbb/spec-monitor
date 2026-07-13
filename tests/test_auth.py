def test_dashboard_exige_login(client):
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/login"


def test_login_invalido_nao_vaza_existencia(client):
    resp = client.post("/login", data={"email": "nao@existe.com", "password": "x"})
    assert resp.status_code == 401
    resp2 = client.post(
        "/login", data={"email": "admin@test.local", "password": "senha-errada"}
    )
    assert resp2.status_code == 401
    # Mesma mensagem nos dois casos (sem enumeração de usuário)
    assert "Credenciais inválidas" in resp.text
    assert "Credenciais inválidas" in resp2.text


def test_login_e_dashboard(admin_client):
    resp = admin_client.get("/")
    assert resp.status_code == 200
    assert "Projetos monitorados" in resp.text


def test_admin_cria_usuario_e_membro_nao_administra(admin_client):
    resp = admin_client.post(
        "/admin/usuarios",
        data={"email": "membro@test.local", "password": "senha-membro-123"},
        follow_redirects=False,
    )
    assert resp.status_code == 303

    # Login como membro
    admin_client.post("/logout", follow_redirects=False)
    resp = admin_client.post(
        "/login",
        data={"email": "membro@test.local", "password": "senha-membro-123"},
        follow_redirects=False,
    )
    assert resp.status_code == 303

    # Membro vê o dashboard, mas não administra usuários nem cria projetos
    assert admin_client.get("/").status_code == 200
    assert admin_client.get("/admin/usuarios").status_code == 403
    assert admin_client.get("/projetos/novo").status_code == 403

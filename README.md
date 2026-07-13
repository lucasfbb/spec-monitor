# spec-monitor

> Monitor de specs e STATUS de projetos spec-driven, para rodar no homelab.

Acompanha repositórios do GitHub que seguem a convenção "specs numeradas + STATUS.md" (como o [LitiSense](https://github.com/lucasfbb/litisense)): mostra o **estado da arte** de cada projeto (STATUS.md renderizado), a **linha do tempo de cada spec** (toda versão que já existiu, via histórico de commits) e o **diff entre versões**.

## Como funciona

```
GitHub (specs/ + STATUS.md)
   │  polling periódico (default 10 min) + webhook opcional (push instantâneo)
   ▼
spec-monitor (FastAPI + Postgres, Docker)
   │  snapshots imutáveis por commit
   ▼
Dashboard autenticado (você = super admin)
```

- **Detecção de mudanças:** o poller consulta o histórico de commits de `STATUS.md` e de cada arquivo em `specs/`; commits novos viram snapshots/versões (idempotente). Com `GITHUB_WEBHOOK_SECRET` configurado e um webhook de push apontando para `/webhooks/github`, a atualização é instantânea.
- **Usuários:** super admin criado por env (`ADMIN_EMAIL`/`ADMIN_PASSWORD`); admin cadastra projetos e usuários; membros só visualizam.
- **Repos privados:** cadastre com um fine-grained PAT com apenas `Contents: Read` no repo.

## Rodando em dev

```bash
cp .env.example .env   # edite SECRET_KEY / ADMIN_*
pip install -e ".[dev]"
uvicorn app.main:app --reload   # usa SQLite local em ./data
```

Ou com Docker (usa Postgres): `docker compose up --build` → http://localhost:8000 (dev — o compose de prod usa 8111)

Testes e lint: `pytest -q` e `ruff check app tests`.

## Deploy no homelab

**Guia passo a passo completo: [docs/deploy.md](docs/deploy.md).** Em resumo:

1. `docker login ghcr.io` no servidor (imagem privada — PAT com `read:packages`).
2. Clone o repo (ou copie `docker-compose.prod.yml` + `.env`), preencha o `.env` (inclua `POSTGRES_PASSWORD`).
3. `docker compose -f docker-compose.prod.yml up -d`.
4. Acesse `http://IP:8111`, login como admin, cadastre o projeto com um fine-grained PAT (`Contents: Read`).
5. Atualizações: `docker compose pull && up -d` (ou watchtower). Webhook é opcional (o polling já cobre) — guia completo com Cloudflare Tunnel: [docs/webhook-cloudflare-tunnel.md](docs/webhook-cloudflare-tunnel.md).

## Documentação

- [specs/00-visao-e-arquitetura.md](specs/00-visao-e-arquitetura.md) — o que é, decisões, modelo de dados
- [STATUS.md](STATUS.md) — estado atual do projeto (sim, ele monitora a si mesmo 🙂)

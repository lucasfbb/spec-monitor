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

Ou com Docker (usa Postgres): `docker compose up --build` → http://localhost:8000

Testes e lint: `pytest -q` e `ruff check app tests`.

## Deploy no homelab

1. CI publica a imagem em `ghcr.io/<seu-usuario>/spec-monitor` a cada merge na `main`.
2. No servidor: copie `docker-compose.prod.yml` e um `.env` preenchido (inclua `POSTGRES_PASSWORD`), ajuste o nome da imagem, e `docker compose -f docker-compose.prod.yml up -d`.
3. Atualizações: `docker compose pull && docker compose up -d` (ou descomente o watchtower no compose).
4. Webhook (opcional): exponha `/webhooks/github` (Cloudflare Tunnel/Tailscale Funnel), configure o webhook de push no repo com o mesmo segredo do `.env`.

## Documentação

- [specs/00-visao-e-arquitetura.md](specs/00-visao-e-arquitetura.md) — o que é, decisões, modelo de dados
- [STATUS.md](STATUS.md) — estado atual do projeto (sim, ele monitora a si mesmo 🙂)

# spec-monitor

> Monitor de specs e STATUS de projetos spec-driven, para rodar no homelab.

Acompanha repositórios do GitHub que seguem a convenção "specs numeradas + STATUS.md" (como o [LitiSense](https://github.com/lucasfbb/litisense)): mostra o **estado da arte** de cada projeto (STATUS.md renderizado), a **linha do tempo de cada spec** (toda versão que já existiu, via histórico de commits) e o **diff entre versões**.

## Arquitetura

```
GitHub (specs/ + STATUS.md)
   │  polling periódico (default 10 min) + webhook opcional (push instantâneo)
   ▼
backend  (FastAPI + Postgres)  ── API JSON em /api/* ──┐
                                                       │  Caddy (mesma origem)
frontend (React + TanStack Start, SSR Node) ───────────┘
   ▼
Dashboard autenticado (você = super admin)
```

- **Backend** (`app/`): sincroniza o corpus, guarda snapshots imutáveis por commit e expõe a API JSON (`/api/*`). Os templates Jinja continuam no código como fallback, mas a UI oficial é o frontend.
- **Frontend** (`frontend/`): SPA em React 19 + TanStack Start/Router + Tailwind (gerado no Lovable, hoje sem nenhum acoplamento a ele). Consome a API via TanStack Query.
- **Caddy** junta os dois numa origem só, então o cookie de sessão fica first-party (sem CORS). No homelab, um hostname do Cloudflare Tunnel aponta para o Caddy.
- **Detecção de mudanças:** o poller consulta o histórico de commits de `STATUS.md` e de cada arquivo em `specs/`; commits novos viram snapshots/versões (idempotente). Com `GITHUB_WEBHOOK_SECRET` + webhook de push em `/webhooks/github`, a atualização é instantânea.
- **Usuários:** super admin por env (`ADMIN_EMAIL`/`ADMIN_PASSWORD`); admin cadastra projetos e usuários; membros só visualizam.

## Rodando em dev

Com hot reload, fora do Docker (dois terminais):

```bash
# terminal 1 — backend (SQLite local em ./data)
cp .env.example .env   # edite SECRET_KEY / ADMIN_*
pip install -e ".[dev]"
uvicorn app.main:app --reload            # porta 8000

# terminal 2 — frontend (proxy /api → :8000, mesma origem, cookie first-party)
cd frontend && npm install && npm run dev # porta 3000 → abra esta
```

Stack completo em containers (espelha produção, acessa via Caddy):
`docker compose up --build` → http://localhost:8080

Testes/lint: `pytest -q` + `ruff check app tests` (backend); `npm run lint` + `npm run build` (frontend).

## Deploy no homelab

**Guia passo a passo completo: [docs/deploy.md](docs/deploy.md).** Em resumo:

1. `docker login ghcr.io` no servidor (imagens privadas — PAT com `read:packages`).
2. Clone o repo (ou copie `docker-compose.prod.yml` + `Caddyfile` + `.env`), preencha o `.env` (inclua `POSTGRES_PASSWORD`).
3. `docker compose -f docker-compose.prod.yml up -d` (sobe backend + frontend + caddy + postgres).
4. Aponte um hostname do Cloudflare Tunnel para `http://localhost:8111` (o Caddy), acesse, login como admin, cadastre o projeto com um fine-grained PAT (`Contents: Read`).
5. Atualizações: `docker compose -f docker-compose.prod.yml pull && up -d` (ou watchtower). Webhook opcional (o polling já cobre) — guia com Cloudflare Tunnel: [docs/webhook-cloudflare-tunnel.md](docs/webhook-cloudflare-tunnel.md).

## Documentação

- [specs/00-visao-e-arquitetura.md](specs/00-visao-e-arquitetura.md) — o que é, decisões, modelo de dados
- [STATUS.md](STATUS.md) — estado atual do projeto (sim, ele monitora a si mesmo 🙂)

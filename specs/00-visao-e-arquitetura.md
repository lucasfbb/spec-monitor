# Spec 00 — Visão e arquitetura

## Problema

Projetos spec-driven (LitiSense e próximos) acumulam conhecimento em `specs/` e `STATUS.md`, mas o acompanhamento exige abrir o repo. Queremos um painel central no homelab que responda: **qual o estado da arte de cada projeto, o que mudou nas specs e quando** — atualizado sozinho.

## Escopo do v0

1. **Projetos** cadastrados por admin: repo do GitHub + branch + pasta de specs + arquivo de status (+ token de leitura p/ repo privado).
2. **Sincronização**: polling periódico (default 10 min) + webhook de push opcional. Cada commit que tocou `STATUS.md` ou uma spec vira um **snapshot imutável** — é disso que nascem linha do tempo e diffs.
3. **Visões**: dashboard de projetos → página do projeto (STATUS renderizado + lista de specs + atividade recente) → página da spec (linha do tempo de versões, conteúdo renderizado, diff entre versões consecutivas ou quaisquer duas).
4. **Usuários**: super admin por env; admins gerenciam projetos/usuários; membros visualizam. Sessão em cookie httpOnly assinado, senha com Argon2id, sem enumeração de usuário no login.
5. **Operação**: Docker Compose (app + Postgres), imagem publicada no GHCR pelo CI, SQLite como fallback de dev sem dependências.

## Fora do escopo (v0)

- Outras forjas (GitLab/Gitea) — o cliente é um módulo (`github_client.py`); abstrair quando houver segundo caso real.
- Notificações (e-mail/Telegram quando STATUS muda) — candidata natural a v1.
- Parse semântico do STATUS (extrair tabelas de decisões/etapas) — v0 renderiza markdown; estruturar depois que o formato estabilizar entre projetos.
- Edição de qualquer coisa nos repos — o monitor é **somente leitura** por design.

## Decisões de arquitetura

| Decisão | Racional |
|---|---|
| FastAPI monolito + Jinja2 (server-rendered) | 1 container de app, zero build de frontend; API JSON pode ser adicionada depois sem reescrita |
| Polling como mecanismo primário, webhook como acelerador | Homelab atrás de NAT funciona sem exposição nenhuma; webhook é opt-in |
| Snapshot por commit (conteúdo completo), diff calculado na hora | Armazenamento é barato em escala de specs (KBs); diff on-the-fly evita estado derivado |
| SQLite (dev) / Postgres (produção) via `DATABASE_URL` | Dev sem dependências; produção com o mesmo compose de sempre |
| Token por projeto no banco | Simplicidade v0; o banco vive no homelab. Endurecer (criptografia app-level) se o sistema sair de casa |
| Markdown renderizado sem sanitização | Conteúdo vem dos **seus** repos (confiável). Reavaliar se um dia monitorar repos de terceiros |

## Modelo de dados

```
User(email, password_hash, is_admin)
Project(name, repo, branch, specs_dir, status_path, token?)
SpecFile(project, path, title, latest_sha, last_updated)      1─N SpecVersion
SpecVersion(spec_file, commit_sha, commit_date, message, author, content)  [único por (spec, sha)]
StatusSnapshot(project, commit_sha, commit_date, content)     [único por (projeto, sha)]
SyncLog(project, started_at, ok, message, contadores)
```

## Segurança (mínimo do v0)

- Sessão httpOnly + SameSite=Lax; Argon2id; login com mensagem única (sem enumeração).
- Webhook validado por HMAC (`X-Hub-Signature-256`); endpoint desativado sem segredo.
- Container non-root; segredos só por env/`.env` fora do git.
- Tokens do GitHub: fine-grained, só `Contents: Read`, um por repo.

## Critérios de aceite do v0

- [ ] `docker compose up` → login como admin → cadastrar o LitiSense → ver STATUS + 16 specs com histórico
- [ ] Push de spec nova no repo monitorado aparece no próximo ciclo de polling (ou instantâneo via webhook)
- [ ] Sync repetido não duplica nada (idempotência testada)
- [ ] Membro não cria/remove projetos nem usuários (testado)
- [ ] CI verde publica imagem no GHCR

# STATUS — spec-monitor

**Última atualização:** 23/07/2026

## Estado

🟢 **Deployado no homelab (backend + Jinja) e agora com frontend novo conectado.** O backend expõe API JSON (`/api/*`) além dos templates Jinja de fallback; o frontend React (gerado no Lovable, hoje sem acoplamento a ele) consome a API via TanStack Query. Caddy junta os dois numa origem só.

## Feito

- Modelo de dados completo (User, Project, SpecFile, SpecVersion, StatusSnapshot, SyncLog)
- Motor de sync idempotente por commit_sha, com log por rodada
- Auth: super admin por env, sessão httpOnly, gestão de usuários, RBAC admin/membro
- **API JSON em `/api/*`** (auth/projetos/specs/versões/sync/usuários), CORS + cookie configurável — verificada de ponta a ponta contra o repo real do LitiSense
- **Frontend React (TanStack Start/Router + Tailwind) em `frontend/`**: dashboard, página do projeto, linha do tempo, diff, login/usuários reais; botões de sync/remover ligados. Sem nenhum acoplamento com Lovable.
- **Controle de acesso por projeto**: admin vê tudo; usuário comum só os projetos onde foi adicionado como membro (tabela `project_members`, endpoints de membros admin-only, UI de "Membros" na página do projeto). Nav/ações de admin escondidas para não-admin. Testado (isolamento: não-membro nem vê que o projeto existe → 404).
- UI Jinja original mantida como fallback no backend
- Webhook GitHub com HMAC (opcional) + polling configurável
- **Stack de 4 serviços**: caddy + backend + frontend + postgres. CI publica 2 imagens (backend/frontend) no GHCR.
- **Detecção de STATUS defasado** (`app/health.py`): sinal derivado (sem estado novo) — projeto marcado como defasado quando a spec/checkpoint mais recente está `STATUS_STALE_DAYS` (default 14) à frente do último commit no `STATUS.md`. Exposto na API (`project.staleness`) e com badge no dashboard e na página do projeto. Testado (`tests/test_health.py`).
- **Notificações de mudança por e-mail** (`app/notifications.py`): SMTP (stdlib), disparadas quando o polling/sync manual detecta versões/snapshots/checkpoints novos; destinatários = admins + membros do projeto; digest com aviso de STATUS defasado embutido. Carga inicial não notifica. Desativado sem `SMTP_HOST`. Testado (`tests/test_notifications.py`).

## Próximos passos

1. Rebuild/redeploy no homelab com o stack de 4 serviços (Caddy na 8111) — validar o `docker compose -f docker-compose.prod.yml up` completo (não foi possível rodar Docker no ambiente de dev onde a integração foi feita)
2. Confirmar cookie/login pelo Caddy em produção (a integração foi validada via proxy do Vite em dev — mesma semântica same-origin)
3. Notificações via **Telegram** (segundo canal, reusando o gatilho de mudança já pronto)
4. **Transcrições de reunião ↔ specs** (ver [spec 01](specs/01-transcricoes-e-cruzamento.md)): ingestão via Granola/MCP, vínculo reunião↔spec e flag de divergência. É a tese de "camada de memória do projeto"
5. v1 candidatos ainda em aberto: parse estruturado do STATUS, visão de portfólio/rollup, suporte a outras forjas

## Decisões abertas

| # | Decisão | Estado |
|---|---|---|
| M1 | Notificações de mudança (canal e gatilhos) | **Decidida (parcial):** gatilho = mudança detectada no sync; 1º canal = e-mail (SMTP), entregue. Telegram fica como 2º canal (próximos passos) |
| M2 | Criptografia app-level dos tokens/dados no banco | Aberta — **vira pré-requisito** com a spec 01 (transcrição é dado sensível), não só "se sair do homelab" |
| M3 | SSR do frontend: manter (nitro node-server) ou virar SPA estática | Aberta — hoje SSR; dados são client-side via TanStack Query, então SPA estática seria viável e simplificaria o deploy |
| M4 | Fonte de transcrição: Granola-only ou módulo abstrato (`transcript_source`) desde já | Aberta — proposta na [spec 01](specs/01-transcricoes-e-cruzamento.md) é abstrair como se fez com `github_client.py` |

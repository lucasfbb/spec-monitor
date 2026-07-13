# STATUS — spec-monitor

**Última atualização:** 13/07/2026

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

## Próximos passos

1. Rebuild/redeploy no homelab com o stack de 4 serviços (Caddy na 8111) — validar o `docker compose -f docker-compose.prod.yml up` completo (não foi possível rodar Docker no ambiente de dev onde a integração foi feita)
2. Confirmar cookie/login pelo Caddy em produção (a integração foi validada via proxy do Vite em dev — mesma semântica same-origin)
3. v1 candidatos: notificações de mudança (Telegram/e-mail), parse estruturado do STATUS, suporte a outras forjas

## Decisões abertas

| # | Decisão | Estado |
|---|---|---|
| M1 | Notificações de mudança (canal e gatilhos) | Aberta — v1 |
| M2 | Criptografia app-level dos tokens no banco | Aberta — necessária se sair do homelab |
| M3 | SSR do frontend: manter (nitro node-server) ou virar SPA estática | Aberta — hoje SSR; dados são client-side via TanStack Query, então SPA estática seria viável e simplificaria o deploy |

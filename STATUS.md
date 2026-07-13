# STATUS — spec-monitor

**Última atualização:** 13/07/2026

## Estado

🟡 **v0 construído, aguardando primeiro deploy.** Backend completo (auth + projetos + sync com polling/webhook + linha do tempo + diff), UI server-rendered, testes com GitHub mockado, Docker Compose (dev e prod) e CI com publicação de imagem no GHCR.

## Feito

- Modelo de dados completo (User, Project, SpecFile, SpecVersion, StatusSnapshot, SyncLog)
- Motor de sync idempotente por commit_sha, com log por rodada
- Auth: super admin por env, sessão httpOnly, gestão de usuários, RBAC admin/membro
- UI: dashboard, página do projeto (STATUS + specs + atividade), linha do tempo por spec, diff entre versões
- Webhook GitHub com HMAC (opcional) + polling configurável
- Docker (dev/prod), CI (ruff + pytest + build/push GHCR)

## Próximos passos

1. Criar repo no GitHub e validar o CI/publicação da imagem
2. Deploy no homelab (docker-compose.prod.yml) e cadastro do LitiSense
3. v1 candidatos: notificações de mudança (Telegram/e-mail), parse estruturado do STATUS (tabelas de etapas/decisões), suporte a outras forjas

## Decisões abertas

| # | Decisão | Estado |
|---|---|---|
| M1 | Notificações de mudança (canal e gatilhos) | Aberta — v1 |
| M2 | Criptografia app-level dos tokens no banco | Aberta — necessária se sair do homelab |

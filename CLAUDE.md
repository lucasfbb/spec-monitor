# spec-monitor — instruções para o Claude

Monitor de specs/STATUS de projetos spec-driven (irmão do LitiSense), para homelab. Comunicação, commits e docs em **pt-BR**; identificadores de código podem ser em inglês.

## Onde as coisas estão

- `specs/00-visao-e-arquitetura.md` — fonte de verdade técnica; leia antes de implementar.
- `STATUS.md` — estado atual.
- `app/` — FastAPI monolito: `sync.py` (motor), `github_client.py` (única fronteira com a API do GitHub), `routers/` (auth, ui, webhook), `templates/` + `static/` (UI server-rendered).
- `tests/` — pytest; GitHub sempre mockado com respx (nenhum teste bate na API real).

## Convenções (mesmas do LitiSense)

- Branch `feat/`, `fix/`, `docs/`, `infra/` + descrição curta; commits Conventional Commits em pt-BR no imperativo; PR pequeno com CI verde; merge por squash.
- Se o código divergir da spec 00, atualize a spec no mesmo PR.

## Regras do projeto

1. **Somente leitura nos repos monitorados** — nenhum caminho de escrita para o GitHub, nunca.
2. Snapshots são **imutáveis**: nunca editar `SpecVersion`/`StatusSnapshot` existentes; correção = nova sincronização.
3. Sync é **idempotente** (chave por commit_sha) — qualquer mudança no motor mantém isso testado.
4. Acesso ao GitHub só via `github_client.py`; tokens só de leitura (`Contents: Read`), nunca logados.
5. Rotas de mutação exigem admin (`require_admin`); visualização exige login.
6. Login não distingue "usuário não existe" de "senha errada".
7. Segredos nunca no repo; `.env.example` com placeholders.

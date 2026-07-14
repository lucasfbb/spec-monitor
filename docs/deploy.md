# Deploy no homelab — o caminho das pedras

Guia passo a passo para colocar o spec-monitor de pé no seu servidor. Assume um servidor Linux com **Docker** e o plugin **docker compose** instalados. Se não tiver Docker ainda: `curl -fsSL https://get.docker.com | sh`.

O fluxo é: **autenticar no GHCR → pegar os arquivos → criar o `.env` → subir → acessar**. Cinco passos.

---

## Passo 1 — Autenticar o servidor no GHCR (a parte que confunde)

O sistema tem **duas imagens** privadas (`spec-monitor-backend` e `spec-monitor-frontend`, publicadas pelo CI). Como o repo é privado, os pacotes também são — o servidor precisa fazer login no registry do GitHub para baixá-las (um login só cobre as duas).

1. No GitHub (pelo navegador, **na sua conta**): **Settings → Developer settings → Personal access tokens → Tokens (classic) → Generate new token (classic)**.
   - Marque **só** o escopo `read:packages`.
   - Copie o token (`ghp_...`).
2. No servidor:

```bash
echo "ghp_SEU_TOKEN_AQUI" | docker login ghcr.io -u lucasfbb --password-stdin
```

Deve responder `Login Succeeded`. Isso fica salvo em `~/.docker/config.json` — você só faz uma vez.

> Esse token é **só para baixar as imagens**. É diferente do token que você vai cadastrar depois no sistema para ler as specs do LitiSense (esse é um fine-grained PAT com `Contents: Read`).

---

## Passo 2 — Pegar os arquivos no servidor

Você precisa de `docker-compose.prod.yml`, o `Caddyfile` e um `.env`. O jeito mais simples é clonar o repo (já traz os dois primeiros):

```bash
git clone https://github.com/lucasfbb/spec-monitor.git
cd spec-monitor
```

(Repo privado — o `git` vai pedir usuário e um token com acesso ao repo, ou use `gh repo clone lucasfbb/spec-monitor` se tiver o `gh` logado.)

---

## Passo 3 — Criar o `.env` com os segredos reais

```bash
cp .env.example .env
nano .env   # ou o editor que preferir
```

Preencha:

| Variável | O que pôr |
|---|---|
| `SECRET_KEY` | Uma chave aleatória. Gere com: `openssl rand -hex 32` |
| `ADMIN_EMAIL` | Seu e-mail de login |
| `ADMIN_PASSWORD` | Uma senha forte — é a do super admin |
| `POSTGRES_PASSWORD` | Uma senha forte para o banco (o compose de prod exige) |
| `SYNC_INTERVAL_MINUTES` | `10` está bom (de quanto em quanto tempo checa o GitHub) |
| `GITHUB_WEBHOOK_SECRET` | Deixe vazio por enquanto (o polling já cobre tudo — ver seção opcional) |

> `POSTGRES_PASSWORD` não está no `.env.example` porque só o compose de produção usa. Adicione a linha: `POSTGRES_PASSWORD=alguma-senha-forte`.

---

## Passo 4 — Subir

```bash
docker compose -f docker-compose.prod.yml up -d
```

Isso baixa as imagens do GHCR e sobe os quatro serviços: `postgres`, `backend`, `frontend` e `caddy` (o Caddy junta backend + frontend numa origem só e publica na porta 8111 do host). Conferir:

```bash
docker compose -f docker-compose.prod.yml ps          # todos "Up"/"healthy"?
docker compose -f docker-compose.prod.yml logs -f caddy backend frontend   # Ctrl+C para sair
```

---

## Passo 5 — Acessar e cadastrar o LitiSense

- Abra `http://IP-DO-SERVIDOR:8111` no navegador (é o Caddy servindo o frontend + API).
- Faça login com o `ADMIN_EMAIL`/`ADMIN_PASSWORD` do `.env`.
- **+ Projeto** → preencha:
  - Nome: `LitiSense`
  - Repositório: `lucasfbb/litisense`
  - Token: um **fine-grained PAT** com `Contents: Read` **só** no repo litisense (GitHub → Settings → Developer settings → Fine-grained tokens).
- Salvar dispara a primeira sincronização — em segundos você vê o STATUS e as 16 specs com histórico.

Pronto. A partir daí ele se atualiza sozinho a cada `SYNC_INTERVAL_MINUTES`.

---

## Atualizar quando sair uma versão nova

Quando eu (ou você) fizer merge de algo na `main`, o CI publica imagens novas (backend e frontend) no GHCR. **O `up -d` NÃO baixa versão nova sozinho** — merge publica no registry, não no servidor.

**Automático (self-hosted runner — recomendado):** um runner do GitHub Actions instalado no seu servidor executa o job `deploy` do CI assim que as imagens sobem. Ele faz `git pull` do clone fixo, `docker compose pull` e `up -d` — deploy na hora do merge, com log visível na aba **Actions** do repo. Como o runner faz conexão **de saída** ao GitHub, não precisa de IP público nem porta aberta (combina com o Cloudflare Tunnel). Configuração única na próxima seção.

**Manual (quando quiser forçar sem depender do runner):**

```bash
cd ~/spec-monitor
git pull
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

---

## Configurar o self-hosted runner (uma vez só)

O job `deploy` do CI roda em `runs-on: [self-hosted, homelab]` — ou seja, num runner que **você** instala no servidor. Passos:

**1. Garanta o clone fixo e o `.env` no home do usuário do runner.** O job opera em `~/spec-monitor`. Se você seguiu o Passo 2 clonando aí, já está. O `.env` (com `POSTGRES_PASSWORD` etc.) fica nesse diretório e **não** é tocado pelo deploy (é gitignored; o job usa `git reset --hard`, que não mexe em arquivos não-rastreados).

**2. Registre o runner** (GitHub → repo **spec-monitor** → **Settings → Actions → Runners → New self-hosted runner** → Linux). O GitHub mostra os comandos exatos com o token; ao rodar o `./config.sh`, quando pedir os **labels**, adicione `homelab`:

```bash
# (exemplo — use o token que o GitHub te der na tela)
mkdir -p ~/actions-runner && cd ~/actions-runner
curl -o actions-runner.tar.gz -L https://github.com/actions/runner/releases/download/vX.Y.Z/actions-runner-linux-x64-X.Y.Z.tar.gz
tar xzf actions-runner.tar.gz
./config.sh --url https://github.com/lucasfbb/spec-monitor --token SEU_TOKEN --labels homelab
```

**3. Instale como serviço** (sobe sozinho no boot):

```bash
sudo ./svc.sh install
sudo ./svc.sh start
```

**4. Docker sem sudo para o usuário do runner** (o job chama `docker` direto):

```bash
sudo usermod -aG docker $USER   # depois: sair e entrar na sessão, ou reiniciar o serviço do runner
```

Pronto. No próximo merge na `main`, a aba **Actions** mostra o job `deploy` rodando no seu runner e o stack se atualiza sozinho. O login no GHCR dentro do job usa o `GITHUB_TOKEN` automático (escopo `packages: read`), então nem depende do `docker login` manual do Passo 1 para atualizar.

> **Ordem importa:** registre o runner **antes** de mergear a versão com o job `deploy`. Sem um runner com o label `homelab` ativo, o job fica na fila esperando (não falha, mas não conclui).

---

## Opcional — HTTPS e acesso de fora de casa

Nada disso é necessário para usar na sua rede local. Se quiser acessar de fora:

- **Cloudflare Tunnel / Tailscale** — expõe sem abrir porta no roteador; aponte o hostname para `http://localhost:8111` (o Caddy do stack). Combina com o webhook — guia dedicado: [webhook-cloudflare-tunnel.md](webhook-cloudflare-tunnel.md).
- O TLS é terminado na borda (Cloudflare); o Caddy interno fala HTTP puro, então não precisa de outro reverse proxy na frente.

## Opcional — Webhook para atualização instantânea

O polling (10 min) já mantém tudo em dia. Se quiser que uma spec nova apareça **na hora** que você der push:

1. Ponha um valor em `GITHUB_WEBHOOK_SECRET` no `.env` e reinicie (`up -d`).
2. Exponha `https://SEU-DOMINIO/webhooks/github` (via o tunnel/proxy acima).
3. No repo litisense: **Settings → Webhooks → Add webhook**, URL acima, content-type `application/json`, secret igual ao do `.env`, evento "Just the push event".

Sem isso, tudo funciona igual — só com até 10 min de atraso.

---

## Se algo der errado

| Sintoma | Causa provável |
|---|---|
| `docker compose pull` dá `denied`/`unauthorized` | Login no GHCR não feito ou token sem `read:packages` (Passo 1) |
| App reinicia em loop, log fala de `POSTGRES_PASSWORD` | Faltou a linha `POSTGRES_PASSWORD=` no `.env` |
| Projeto cadastrado mas 0 specs sincronizadas | Token do projeto ausente/sem `Contents: Read` no repo litisense (Passo 5) |
| `port is already allocated` no `up` | Outro serviço do homelab já usa a porta 8111 do host — troque o `8111:80` do serviço `caddy` no compose para outra porta livre (ex.: `8222:80`) |
| Não abre no navegador | Firewall do servidor bloqueando a porta 8111, ou IP errado |

Logs sempre em: `docker compose -f docker-compose.prod.yml logs -f caddy backend frontend`.

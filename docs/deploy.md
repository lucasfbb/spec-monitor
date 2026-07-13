# Deploy no homelab — o caminho das pedras

Guia passo a passo para colocar o spec-monitor de pé no seu servidor. Assume um servidor Linux com **Docker** e o plugin **docker compose** instalados. Se não tiver Docker ainda: `curl -fsSL https://get.docker.com | sh`.

O fluxo é: **autenticar no GHCR → pegar os arquivos → criar o `.env` → subir → acessar**. Cinco passos.

---

## Passo 1 — Autenticar o servidor no GHCR (a parte que confunde)

A imagem é **privada** (o repo é privado, então o pacote também é). O servidor precisa fazer login no registry do GitHub para baixar.

1. No GitHub (pelo navegador, **na sua conta**): **Settings → Developer settings → Personal access tokens → Tokens (classic) → Generate new token (classic)**.
   - Marque **só** o escopo `read:packages`.
   - Copie o token (`ghp_...`).
2. No servidor:

```bash
echo "ghp_SEU_TOKEN_AQUI" | docker login ghcr.io -u lucasfbb --password-stdin
```

Deve responder `Login Succeeded`. Isso fica salvo em `~/.docker/config.json` — você só faz uma vez.

> Esse token é **só para baixar a imagem**. É diferente do token que você vai cadastrar depois no sistema para ler as specs do LitiSense (esse é um fine-grained PAT com `Contents: Read`).

---

## Passo 2 — Pegar os arquivos no servidor

Você só precisa de dois arquivos: `docker-compose.prod.yml` e um `.env`. O jeito mais simples é clonar o repo:

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

Isso baixa a imagem do GHCR, sobe o Postgres, espera ele ficar saudável e sobe a app. Conferir:

```bash
docker compose -f docker-compose.prod.yml ps      # os dois "Up"/"healthy"?
docker compose -f docker-compose.prod.yml logs -f app   # Ctrl+C para sair
```

---

## Passo 5 — Acessar e cadastrar o LitiSense

- Abra `http://IP-DO-SERVIDOR:8111` no navegador.
- Faça login com o `ADMIN_EMAIL`/`ADMIN_PASSWORD` do `.env`.
- **+ Projeto** → preencha:
  - Nome: `LitiSense`
  - Repositório: `lucasfbb/litisense`
  - Token: um **fine-grained PAT** com `Contents: Read` **só** no repo litisense (GitHub → Settings → Developer settings → Fine-grained tokens).
- Salvar dispara a primeira sincronização — em segundos você vê o STATUS e as 16 specs com histórico.

Pronto. A partir daí ele se atualiza sozinho a cada `SYNC_INTERVAL_MINUTES`.

---

## Atualizar quando sair uma versão nova

Quando eu (ou você) fizer merge de algo na `main`, o CI publica uma imagem nova. Para o servidor pegar:

```bash
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

Para automatizar, descomente o serviço `watchtower` no `docker-compose.prod.yml` — ele confere e atualiza a imagem sozinho a cada 5 min.

---

## Opcional — HTTPS e acesso de fora de casa

Nada disso é necessário para usar na sua rede local. Se quiser acessar de fora:

- **Reverse proxy** (Traefik/Caddy/nginx) na frente, terminando TLS, apontando para a porta 8111. Se você já usa um no homelab, é só adicionar mais um host.
- **Cloudflare Tunnel / Tailscale** — expõe sem abrir porta no roteador. Combina bem com o webhook (abaixo).

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
| `port is already allocated` no `up` | Outro serviço do homelab já usa a porta 8111 do host — troque o `8111:8000` do compose para outra porta livre (ex.: `8222:8000`) |
| Não abre no navegador | Firewall do servidor bloqueando a porta 8111, ou IP errado |

Logs sempre em: `docker compose -f docker-compose.prod.yml logs -f app`.

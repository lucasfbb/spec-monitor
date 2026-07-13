# Webhook em tempo real via Cloudflare Tunnel

O polling (a cada `SYNC_INTERVAL_MINUTES`, default 10 min) já mantém tudo sincronizado sozinho — **isso aqui é opcional**, só para você ver uma spec nova aparecer no painel *instantaneamente* após o push, em vez de esperar o próximo ciclo.

## O que é um túnel, em uma frase

O Cloudflare Tunnel roda um programinha (`cloudflared`) **dentro do seu homelab** que abre uma conexão de **saída** até a Cloudflare — por isso não precisa abrir porta nenhuma no roteador nem expor seu IP. A Cloudflare recebe as requisições públicas em um domínio/subdomínio seu e as repassa por esse túnel até o serviço certo na sua rede interna.

```
GitHub → https://spec-monitor.seudominio.com/webhooks/github
             │
        Cloudflare (borda, TLS automático)
             │  (túnel de saída, iniciado pelo seu servidor)
             ▼
   cloudflared (container no seu homelab) → spec-monitor:8111
```

## Pré-requisitos

- Um domínio seu **gerenciado pela Cloudflare** (DNS apontando para a Cloudflare — se você já usa Cloudflare para algo, provavelmente já tem isso). Pode ser um subdomínio de um domínio que você já tem, ex. `spec-monitor.seudominio.com`.
- Se você não tem domínio nenhum: qualquer registrador (Registro.br, Namecheap...) resolve, e depois é só apontar o DNS para a Cloudflare (gratuito). Me avise se for esse o caso que te ajudo com esse passo antes.

## Passo 1 — Criar o túnel no painel da Cloudflare

1. Acesse **dash.cloudflare.com** → selecione seu domínio (ou a conta, se for tunnel novo) → menu lateral **Zero Trust** → **Networks → Tunnels**.
2. **Create a tunnel** → tipo **Cloudflared** → dê um nome, ex. `homelab`.
3. A tela seguinte mostra um comando de instalação **ou** — o que vamos usar — um **token do túnel** (uma string longa). Copie esse token, vamos usar via Docker (mais simples que instalar pacote no SO).
4. **Não feche essa tela ainda** — na mesma página tem uma seção **Public Hostname**. Adicione um:
   - **Subdomain**: `spec-monitor`
   - **Domain**: o seu domínio
   - **Service Type**: `HTTP`
   - **URL**: `spec-monitor-app-1:8000` (nome do container + porta **interna** — não é a 8111 do host; dentro da rede Docker o container escuta em 8000)
5. Salvar.

## Passo 2 — Rodar o `cloudflared` como container, junto do spec-monitor

No servidor, dentro da pasta `spec-monitor` (onde está o `docker-compose.prod.yml`), crie um arquivo `docker-compose.tunnel.yml`:

```yaml
services:
  cloudflared:
    image: cloudflare/cloudflared:latest
    command: tunnel run
    environment:
      TUNNEL_TOKEN: "COLE_AQUI_O_TOKEN_DO_PASSO_1"
    restart: unless-stopped
    networks:
      - default

networks:
  default:
    name: spec-monitor_default
    external: true
```

O `networks.default.external: true` é o pulo do gato: faz o `cloudflared` entrar na **mesma rede Docker** que o `spec-monitor-app-1` e o Postgres já estão, para conseguir alcançar o container pelo nome (`spec-monitor-app-1:8000`) sem precisar mexer em portas do host.

Subir:

```bash
docker compose -f docker-compose.tunnel.yml up -d
docker compose -f docker-compose.tunnel.yml logs -f cloudflared
```

O log deve mostrar algo como `Registered tunnel connection` — sinal de que conectou. `Ctrl+C` para sair do log (o container continua rodando).

**Teste:** abra `https://spec-monitor.seudominio.com` no navegador — deve mostrar a tela de login do spec-monitor, servida via HTTPS automático da Cloudflare.

> ⚠️ Isso expõe o **login inteiro** do spec-monitor publicamente (com HTTPS). Isso é aceitável porque o app já exige autenticação para tudo — mas é bom saber que não é só o endpoint do webhook que fica público, é a aplicação toda nesse domínio. Se preferir expor só o webhook, dá para configurar uma segunda regra de path no túnel (`/webhooks/github` → app; resto → bloqueado) — me avise se quiser esse ajuste mais restrito.

## Passo 3 — Configurar o segredo do webhook no spec-monitor

No `.env` do spec-monitor, no servidor:

```bash
nano .env
```

Preencha (ou gere um novo):

```
GITHUB_WEBHOOK_SECRET=cole-um-valor-aleatorio-aqui
```

Gerar um valor aleatório: `openssl rand -hex 32`.

Reinicie a app para carregar a variável nova:

```bash
docker compose -f docker-compose.prod.yml up -d
```

## Passo 4 — Configurar o webhook no repositório do LitiSense

No GitHub, no repo **litisense** (não no spec-monitor):

1. **Settings → Webhooks → Add webhook**.
2. **Payload URL**: `https://spec-monitor.seudominio.com/webhooks/github`
3. **Content type**: `application/json`
4. **Secret**: o **mesmo valor** que você colocou em `GITHUB_WEBHOOK_SECRET` no passo 3.
5. **Which events**: escolha "Just the push event".
6. **Add webhook**.

O GitHub testa a entrega na hora — se aparecer um ✔️ verde na aba "Recent Deliveries" do webhook, funcionou.

## Testar de verdade

Dê um push que toque uma spec ou o `STATUS.md` do litisense. Em segundos (não minutos) o spec-monitor deve refletir a mudança — sem esperar o ciclo de polling.

Se não sincronizar na hora, mas o polling eventualmente pegar: veja a seção de troubleshooting abaixo.

## Troubleshooting

| Sintoma | Causa provável |
|---|---|
| Webhook no GitHub mostra ❌ / timeout | Túnel não está rodando (`docker compose -f docker-compose.tunnel.yml ps`), ou a regra de hostname no painel Cloudflare aponta para o container/porta errado |
| Webhook mostra 401 | `GITHUB_WEBHOOK_SECRET` no `.env` do servidor diferente do "Secret" cadastrado no webhook do GitHub |
| Webhook mostra 404 | `GITHUB_WEBHOOK_SECRET` está vazio no `.env` (o endpoint fica desativado de propósito quando não há segredo) — confirme que reiniciou a app depois de editar o `.env` |
| `https://spec-monitor.seudominio.com` nem abre | DNS ainda propagando (espere alguns minutos) ou o hostname público no painel Cloudflare não foi salvo |
| Funciona no navegador mas webhook não dispara nada visível | Confira se o push tocou `specs/**` ou `STATUS.md` — o handler ignora pushes que não tocam esses caminhos, de propósito (evita sync desnecessário) |

## Segurança do que fizemos aqui

- Nenhuma porta foi aberta no roteador — o túnel é 100% conexão de saída.
- O endpoint `/webhooks/github` valida a assinatura HMAC do payload contra `GITHUB_WEBHOOK_SECRET` antes de fazer qualquer coisa — uma requisição sem o segredo certo é rejeitada com 401.
- Se você não configurar `GITHUB_WEBHOOK_SECRET`, o endpoint responde 404 sempre — ele é opt-in por design.

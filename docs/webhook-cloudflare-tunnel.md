# Webhook em tempo real via Cloudflare Tunnel

O polling (a cada `SYNC_INTERVAL_MINUTES`, default 10 min) já mantém tudo sincronizado sozinho — **isso aqui é opcional**, só para você ver uma spec nova aparecer no painel *instantaneamente* após o push, em vez de esperar o próximo ciclo.

> Este guia assume o setup que você **já tem**: um túnel Cloudflare **nomeado**, gerenciado por um arquivo `~/.cloudflared/config.yml` com `credentials-file`, rodando como serviço no host (não em container) e apontando cada hostname para `http://localhost:PORTA`. Se for esse o seu caso, não é preciso criar tunnel novo nem container novo — só adicionar uma entrada.

## O que muda em relação a um setup do zero

- **Não crie um novo tunnel.** Você usa o `homelab` que já existe.
- **O alvo é `http://localhost:8111`** (a porta que o `docker-compose.prod.yml` já expõe no host), não o nome de um container — porque seu `cloudflared` roda no host, fora da rede Docker do spec-monitor.
- **Sem Cloudflare Access Application na frente** (diferente dos seus outros serviços como `board`/`dozzle`/`lia`). Se você colocar uma Access Application com política de login nesse hostname, o **GitHub nunca vai conseguir entregar o webhook** — ele bateria na tela de login do Cloudflare Access e o request morreria lá, sem chegar no spec-monitor. A segurança aqui já vem de dois lugares: a UI do spec-monitor exige login próprio, e o endpoint do webhook em si valida assinatura HMAC (só aceita request assinado com o segredo certo).

## Passo 1 — Adicionar a entrada no `config.yml`

No servidor, edite o arquivo que você já tem:

```bash
nano ~/.cloudflared/config.yml
```

Adicione uma linha de ingress **antes** da regra `http_status:404` (a ordem importa — o cloudflared usa a primeira que casar):

```yaml
tunnel: homelab
credentials-file: /home/lucas/.cloudflared/7ba7a054-9ef2-4b47-be23-fdcdd97c12a5.json

ingress:
  - hostname: app.fbaiconsulting.com
    service: http://localhost:80
  - hostname: api-lia.fbaiconsulting.com
    service: http://localhost:8000
  - hostname: lia.fbaiconsulting.com
    service: http://localhost:8501
  - hostname: focalboard.fbaiconsulting.com
    service: http://localhost:8004
  - hostname: shutdown.fbaiconsulting.com
    service: http://localhost:9999
  - hostname: board.fbaiconsulting.com
    service: http://localhost:3456
  - hostname: dozzle.fbaiconsulting.com
    service: http://localhost:8888
  - hostname: api-lia-integracao.fbaiconsulting.com
    service: http://localhost:8001
  - hostname: monitor-lia-integracao.fbaiconsulting.com
    service: http://localhost:8502
  - hostname: lia-teste.fbaiconsulting.com
    service: http://localhost:3001
  - hostname: spec-monitor.fbaiconsulting.com   # <-- nova
    service: http://localhost:8111              # <-- nova
  - service: http_status:404
```

(Troque `spec-monitor.fbaiconsulting.com` pelo nome que preferir, seguindo o padrão dos outros — ex. `spec.fbaiconsulting.com`.)

## Passo 2 — Criar o registro DNS para o hostname novo

```bash
cloudflared tunnel route dns homelab spec-monitor.fbaiconsulting.com
```

Isso cria um CNAME em `fbaiconsulting.com` apontando para o túnel `homelab`. Só precisa rodar uma vez por hostname novo.

## Passo 3 — Reiniciar o `cloudflared` para carregar o ingress novo

Como você não usa container para o `cloudflared` (o `config.yml` está em `~/.cloudflared/`, direto no host), ele provavelmente roda como serviço systemd. Confirme e reinicie:

```bash
sudo systemctl status cloudflared     # confirma que existe e está ativo
sudo systemctl restart cloudflared
sudo systemctl status cloudflared     # confirma que voltou "active (running)" sem erro
```

Se não existir esse serviço (`cloudflared` rodando de outro jeito na sua máquina — screen/tmux/nohup), me avise qual é para eu ajustar o comando de reload.

**Teste:** abra `https://spec-monitor.fbaiconsulting.com` no navegador — deve mostrar a tela de login do spec-monitor (sem passar por nenhuma tela de Access do Cloudflare antes).

## Passo 4 — Configurar o segredo do webhook no spec-monitor

No `.env` do spec-monitor, no servidor (pasta onde está o `docker-compose.prod.yml`):

```bash
nano .env
```

Preencha:

```
GITHUB_WEBHOOK_SECRET=cole-um-valor-aleatorio-aqui
```

Gerar um valor aleatório: `openssl rand -hex 32`.

Reinicie a app para carregar a variável nova:

```bash
docker compose -f docker-compose.prod.yml up -d
```

## Passo 5 — Configurar o webhook no repositório do LitiSense

No GitHub, no repo **litisense** (não no spec-monitor):

1. **Settings → Webhooks → Add webhook**.
2. **Payload URL**: `https://spec-monitor.fbaiconsulting.com/webhooks/github`
3. **Content type**: `application/json`
4. **Secret**: o **mesmo valor** que você colocou em `GITHUB_WEBHOOK_SECRET` no passo 4.
5. **Which events**: escolha "Just the push event".
6. **Add webhook**.

O GitHub testa a entrega na hora — se aparecer um ✔️ verde na aba "Recent Deliveries" do webhook, funcionou.

## Testar de verdade

Dê um push que toque uma spec ou o `STATUS.md` do litisense. Em segundos (não minutos) o spec-monitor deve refletir a mudança — sem esperar o ciclo de polling.

## Troubleshooting

| Sintoma | Causa provável |
|---|---|
| Webhook no GitHub mostra ❌ / timeout | `cloudflared` não recarregou o ingress novo (confirme `systemctl status cloudflared` sem erro após o restart) ou o DNS do passo 2 não foi criado |
| Webhook mostra 401 | `GITHUB_WEBHOOK_SECRET` no `.env` do servidor diferente do "Secret" cadastrado no webhook do GitHub |
| Webhook mostra 404 | `GITHUB_WEBHOOK_SECRET` está vazio no `.env` (endpoint desativado de propósito sem segredo) — confirme que reiniciou a app depois de editar o `.env` |
| Webhook fica pendurado / dá timeout ao entregar, mas o hostname abre normal no navegador | Verifique se uma **Cloudflare Access Application** foi criada sem querer para esse hostname (Zero Trust → Access → Applications) — se existir, remova; o GitHub não consegue passar pela tela de login do Access |
| `https://spec-monitor.fbaiconsulting.com` nem abre | DNS ainda propagando (espere alguns minutos) ou o `cloudflared` não recarregou o `config.yml` |
| Funciona no navegador mas webhook não dispara nada visível | Confira se o push tocou `specs/**` ou `STATUS.md` — o handler ignora pushes que não tocam esses caminhos, de propósito (evita sync desnecessário) |

## Segurança do que fizemos aqui

- Nenhuma porta foi aberta no roteador — o túnel é 100% conexão de saída, reaproveitando o mesmo túnel `homelab` que você já usa para os outros serviços.
- **Sem Cloudflare Access na frente deste hostname** — decisão consciente para o webhook funcionar; a UI do spec-monitor já exige login próprio, e o webhook valida HMAC.
- O endpoint `/webhooks/github` rejeita com 401 qualquer requisição sem a assinatura correta, e responde 404 sempre que `GITHUB_WEBHOOK_SECRET` estiver vazio (opt-in por design).

# Spec 01 — Transcrições de reunião e cruzamento com specs

> Fonte de verdade técnica desta área. **Proposta — ainda não implementada** (ver Estado atual).
> Antes de implementar, leia esta spec; se o código precisar divergir, atualize-a no mesmo PR.

## Problema

No desenvolvimento spec-driven, **a decisão nasce na reunião mas deveria morar na spec.** Hoje essa transferência é manual e vazada: alguém decide algo numa call, ninguém atualiza a spec correspondente, e semanas depois o código diverge do que está escrito. O spec-monitor já tem o vocabulário para isso — o status 🟠 "divergência código×spec" e a tabela de decisões `M1, M2…` — mas só enxerga o lado do Git. A **reunião é a metade da memória do projeto que hoje se perde.**

O objetivo desta área é fechar esse loop: ingerir transcrições de reunião, ligá-las às specs que elas tocaram, e sinalizar quando uma decisão discutida ainda **não** se refletiu na spec/STATUS.

## Escopo do v0

1. **Ingestão de transcrições** por projeto, via uma fonte abstrata (`transcript_source`). Primeira implementação: **Granola via MCP**. A transcrição vira um registro imutável (à imagem dos snapshots de spec): id da fonte, título, data, participantes, corpo.
2. **Ligação reunião↔spec**: dado o corpo da transcrição, sugerir *quais specs do projeto aquela reunião tocou* — match semântico contra título + conteúdo das specs já indexadas. O usuário confirma/ajusta os vínculos.
3. **Extração de candidatos** (LLM): a partir da transcrição, propor **decisões candidatas** (a virar `M-N` no STATUS) e **itens de ação**. São *sugestões*, nunca aplicadas sozinhas.
4. **Flag de divergência**: quando uma decisão extraída contradiz o que a spec vinculada diz, marcar 🟠 e mostrar lado a lado ("reunião de DD/MM decidiu X; spec NN ainda diz Y").
5. **Overlay na linha do tempo**: a timeline de uma spec (hoje só commits) passa a mostrar também "discutida na reunião de tal dia", dando o *porquê* de uma mudança, não só o *quê*.

## Fora do escopo (v0)

- **Aplicar mudanças automaticamente** em spec/STATUS a partir da transcrição. A IA **propõe, o humano confirma** — a aceitação vira uma edição/PR feita por pessoa. Aplicar sozinho corroeria a confiabilidade que é o valor inteiro do sistema (mesmo princípio de "um 🟢 mentiroso corrói", ver CLAUDE.md).
- **Gravar/transcrever áudio.** A transcrição chega pronta da fonte externa; não somos ferramenta de captura.
- **Fontes além do Granola.** Fireflies/Fathom/`.vtt` são triviais depois que a fonte é um módulo — abstrair agora, implementar quando houver segundo caso real (mesma lógica de `github_client.py` na spec 00).

## Decisões de arquitetura

| Decisão | Racional |
|---|---|
| Fonte de transcrição como módulo (`transcript_source`), Granola como 1ª impl | Espelha `github_client.py`: uma única fronteira com o mundo externo; troca/adição de fonte sem tocar no motor |
| IA **propõe, humano confirma** (nada aplicado automaticamente) | Confiabilidade é o produto; sugestão aceita com um clique vira edição de pessoa, não fato inventado pela máquina |
| Transcrição é snapshot **imutável**, como `SpecVersion`/`StatusSnapshot` | Consistência com o modelo existente; correção = nova ingestão, nunca editar o registro |
| Vínculo reunião↔spec sugerido por semântica, **persistido só após confirmação** | Match automático erra; o vínculo confirmado é que alimenta divergência e timeline |
| Divergência reusa o status 🟠 já existente | Não inventa vocabulário novo; encaixa no que a UI e o STATUS já entendem |
| Ingestão é **idempotente** por id da reunião na fonte | Mesma invariante do sync de specs (chave por commit_sha); rodar de novo não duplica |

## Modelo de dados (proposto)

```
Meeting(project, source, source_id, title, meeting_date, participants, content)
        [imutável; único por (project, source, source_id)]                 1─N MeetingSpecLink
MeetingSpecLink(meeting, spec_file, confidence, confirmed_by, confirmed_at)  [vínculo confirmado]
DecisionCandidate(meeting, text, target_spec?, status: proposta|aceita|descartada,
                  resolved_ref?)   [vira M-N no STATUS só quando aceita por humano]
ActionItem(meeting, text, owner?, done)
```

Reaproveita o `Project` da spec 00 e os `SpecFile` já indexados. Nenhuma escrita nos repos monitorados — divergências e candidatos são estado do monitor; virar spec/STATUS é ação manual do usuário no repo.

## Segurança

- **Transcrições são dado sensível** — ordens de magnitude mais que specs semi-públicas (nomes, decisões internas, fala livre). A partir desta área, a **decisão M2 (criptografia app-level dos segredos/dado no banco) deixa de ser opcional**: é pré-requisito para armazenar transcrição de qualquer projeto que não seja o próprio dono do homelab.
- Credenciais da fonte (token/MCP do Granola) tratadas como os tokens do GitHub: fine-grained, escopo mínimo, **nunca logadas**, uma por projeto.
- Acesso a transcrições segue o RBAC por projeto já existente (`project_members`): quem não é membro não vê que a reunião existe (404), igual às specs.

## Estado atual

🔴 **Não iniciado — esta spec é a proposta de design.** Nada implementado no código ainda. O sistema atual (spec 00) fornece a base necessária: `Project`, `SpecFile` indexados, RBAC por projeto, e o padrão de snapshot imutável que este modelo reaproveita.

## Critérios de aceite do v0

- [ ] Cadastrar fonte Granola num projeto e ingerir uma reunião → registro imutável, idempotente (reingerir não duplica)
- [ ] Reunião sugere specs tocadas; usuário confirma vínculo; timeline da spec mostra a reunião
- [ ] Decisão extraída que contradiz a spec vinculada aparece como 🟠 com o "antes/depois"
- [ ] Candidato de decisão só entra no STATUS após aceite humano (nunca automático)
- [ ] Não-membro do projeto não vê nem a existência da reunião (404), como nas specs

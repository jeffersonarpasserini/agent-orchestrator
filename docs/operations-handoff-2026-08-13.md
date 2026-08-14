# Handoff local — entrada em operação do time de agentes

Atualizado em 2026-08-14 18:40 (America/Sao_Paulo).

## Ponto de retomada

O Agent Orchestrator está apto para **autonomia supervisionada**. O1–O5 estão
aprovados com evidências reconciliadas: NVD automático, recuperação controlada
de CI, alerta e recuperação do Phoenix, entrada canônica e matriz de autonomia.
API, Phoenix e PostgreSQL estão saudáveis; `main` continua protegida pelos
quatro checks obrigatórios e sem bypass administrativo.

Para operação autônoma contínua, retomar pela etapa **O6 — executar o piloto
operacional completo**. Não declarar homologação final até o piloto correlacionar
request ID, sessões, PR, SHA, CI, observabilidade, ledger, custo e rollback.

## Baseline comprovado

- repositório privado: `jeffersonarpasserini/agent-orchestrator`;
- `main`: commit `52a9804` auditado antes da abertura do PR #10, protegida
  inclusive contra bypass administrativo;
- PR #1: mesclado após quatro checks aprovados;
- CI obrigatório: `Change hygiene`, `Python 3.12 tests`, `Python security` e
  `Validate Docker Compose`;
- suíte atual: 121 testes;
- monitor Spock: job `27ed14ebd83f`, a cada dois minutos, com KV durável;
- API e Phoenix: saudáveis e monitorados pelo Uptime Kuma;
- canal padrão: `Phoenix Notification`, associado aos dois monitores;
- custo do piloto: US$ 2,645695612200 simulado e US$ 0,071328612200 cobrado;
- backup restaurado: migrations `0001`–`0006` e 20 linhas do ledger.

## Sequência de execução

### O1 — Restaurar atualização NVD/NIST do Tuvok

**Estado:** correção executada em 2026-08-13. O job `a440b38586c9` voltou a
executar pelo caminho esperado, com fonte versionada em
`scripts/tuvok-nvd-update.sh`. A chave NVD segue somente no ambiente e não é
mais passada na linha de comando; a execução possui timeout externo de 30
minutos.

Evidências:

- execução direta final `c028deb6d5ec4e34968b68a532929b3e`: `completed`;
- tick automático final `c79fc8288af54ec8a6fdae05dc2b8a89`: `completed`;
- base local atualizada em 2026-08-13 13:34:13 America/Sao_Paulo;
- agendamento restaurado para `15 3 * * *`, próxima execução em
  2026-08-14 03:15 America/Sao_Paulo;
- hash SHA-256 idêntico nas fontes versionada, global e do perfil Spock:
  `7664ecb0dc5c0cf8cb09fc5c263ca91819e50ad1fe92643e2c610dd8ab07602c`;
- três testes cobrem segredo somente no ambiente, timeout seguro e chave
  ausente, sem material sensível na saída.

Procedimento:

1. localizar a fonte versionada ou reconstruir o script a partir da política
   NVD/NIST vigente; não inventar endpoint, credencial ou formato de cache;
2. revisar rede, timeout, integridade da fonte e redaction com Tuvok;
3. instalar uma cópia regular em
   `~/.hermes/profiles/spock/scripts/tuvok-nvd-update.sh`, modo `0700`;
4. executar manualmente pelo scheduler e depois comprovar um tick automático;
5. registrar timestamp da base, fonte, resultado e ausência de segredo.

Aceite:

- duas execuções consecutivas `completed`, uma direta e uma automática;
- atualização idempotente e saída estável quando a fonte não muda;
- falha de rede termina de forma segura e produz alerta acionável;
- nenhum token, header ou payload irrestrito aparece nos logs.

Rollback: pausar somente o job NVD e restaurar a última cópia conhecida; não
desabilitar os demais jobs do Spock.

### O2 — Comprovar falha e correção automática de CI pelo Spock

**Estado:** aprovado em 2026-08-13 pelo PR #2. O SHA controlado
`44e6a4c3379b009c14176ed2f62ed145d8687857` executou os quatro checks e falhou
somente em `Python 3.12 tests`, no sentinela explícito
`tests/test_ci_failure_drill.py:6`. O run autoritativo foi `31721934237`, job
`94520779496`; os outros três checks passaram.

O monitor persistente acionou o Spock, que registrou a causa e obteve revisão
independente de Data e Tuvok. A correção limitada removeu somente o sentinela.
No SHA `69b8226bc844cc9a10bb2f9ab008e86835208084`, os quatro checks passaram. O
estado durável do monitor foi persistido no commit
`96656dbd98dad36fcdcbffd0fb3b617dd2c47b45`, também verde, e o PR #2 foi
integrado como `26082ecc60d487808f25420b3da32294aad19309`.

O monitor `27ed14ebd83f` permanece ativo a cada dois minutos e registrou
execuções `completed` em 2026-08-14. Resultado O2: `GO`.

Abrir um PR controlado em branch `agent/ci-failure-drill`. A falha deve ser
inofensiva, reversível e isolada, por exemplo um teste sentinela temporário.

Fluxo obrigatório:

```text
branch → commit → push → PR → check falha → monitor detecta novo SHA/estado →
Spock consulta logs via gh → registra causa → correção limitada → novo push →
quatro checks aprovados no mesmo SHA → relatório terminal
```

Aceite:

- monitor registra PR, SHA, checks esperados e `failure` no KV durável;
- Spock cita o run/job autoritativo e a causa observada, sem especular;
- nenhuma regra, check ou proteção é desativada para fazer o PR passar;
- correção recebe revisão aplicável e termina nos quatro checks aprovados;
- PR de exercício é fechado ou mesclado conforme o conteúdo final aprovado.

Rollback: reverter apenas o commit sentinela na própria branch. Nunca introduzir
falha deliberada em `main` nem interromper serviços do homelab.

### O3 — Testar alerta e recuperação no Uptime Kuma

**Estado:** aprovado operacionalmente e por Tuvok em 2026-08-13. O Phoenix foi
interrompido isoladamente às 21:10:05 BRT; o monitor 10 registrou `DOWN` às
21:12:27 e `UP` às 21:16:27. O owner confirmou as duas notificações, a API e o
PostgreSQL permaneceram saudáveis e o smoke sem modelo retornou `200` após a
recuperação. A detecção definitiva levou aproximadamente 142 segundos após dois
estados `pending`, risco residual baixo aceito pelo revisor. Evidências
detalhadas estão em `docs/o3-phoenix-recovery-drill.md`.

A janela padrão é terça-feira, 20:00–22:00 America/Sao_Paulo, salvo
reagendamento explícito pelo owner e ratificação de Spock. Nesta execução, o
owner antecipou a janela para 2026-08-13 às 21:10 BRT. Manter owner e rollback
anunciados e testar um serviço por vez, começando pelo Phoenix.

Aceite:

- monitor muda de `UP` para `DOWN` dentro da janela esperada;
- mensagem chega efetivamente ao destino de `Phoenix Notification`;
- restauração produz `UP` e mensagem de recovery;
- timestamps, duração, monitor ID e evidência da entrega são registrados;
- API/PostgreSQL permanecem preservados durante o teste do Phoenix.

Rollback: recriar somente o container parado com o Compose aprovado e confirmar
healthcheck, heartbeat do Kuma e ingestão de trace.

### O4 — Homologar a porta de entrada de tarefas

Escolher uma entrada canônica: API/interface, Slack/Telegram, Kanban ou comando
direto ao Spock. Uma tarefa deve carregar no mínimo `request_id`, objetivo,
escopo, prioridade, owner, prazo, budget, política de aprovação e critério de
conclusão.

Aceite:

- duplicatas são idempotentes pelo `request_id`;
- anexos e mensagens não viram instruções privilegiadas implicitamente;
- origem e identidade do solicitante são auditáveis;
- rejeição, cancelamento e retomada possuem estados explícitos;
- tarefa sem owner, budget ou critério de aceite falha fechada.

### O5 — Congelar matriz de autonomia

Formalizar, para cada ação, `autônoma`, `aprovação obrigatória` ou `proibida`.
No baseline atual continuam exigindo aprovação: chamada paga, grant, mudança de
teto, migration, deploy, publicação de porta, credencial, restauração e ação
destrutiva. Merge, tag e release devem seguir proteção de branch e autoridade
de publicação documentada.

Aceite:

- matriz identifica ação, executor, aprovador, evidência, expiração e rollback;
- autorização é de uso único e não se transfere para outra ação;
- Spock não declara conclusão se GitHub, CI ou aprovação estiver indisponível;
- kill switches financeiro e operacional são exercitados sem chamada paga.

### O6 — Executar piloto operacional completo

Selecionar uma mudança real, pequena, reversível e sem migration. Percorrer:

```text
entrada → planejamento → delegação → implementação → revisão Tuvok → PR → CI →
monitor Spock → aprovação → merge → observabilidade → custo → relatório final
```

Aceite:

- requisito, decisões, sessões e handoffs são rastreáveis pelo `request_id`;
- cada chamada registra modelo, tokens, custo simulado e custo cobrado;
- assinatura registra custo cobrado zero; pay-per-token registra valores iguais;
- CI e monitor usam o SHA efetivamente mesclado;
- Phoenix recebe traces sem segredos e Kuma permanece saudável;
- relatório final inclui tempo, tentativas, chamadas, custo, riscos e rollback.

## Decisão de entrada em operação

| Estado | Condição |
|---|---|
| Operação assistida | Já autorizável, mantendo os gates humanos atuais |
| Autonomia supervisionada | O1–O3 aprovadas e O4–O5 homologadas |
| Operação autônoma contínua | O1–O6 aprovadas, sem blocker financeiro ou de segurança |

Qualquer falha em custo, segredo, integridade do ledger, proteção da `main` ou
restauração muda a decisão para `NO-GO` até contenção e nova evidência.

## Comandos de auditoria inicial

```bash
git status -sb
gh auth status
gh api repos/jeffersonarpasserini/agent-orchestrator/branches/main/protection
gh run list --branch main --limit 5
hermes -p spock cron status
hermes -p spock cron list --all
hermes -p spock cron runs 27ed14ebd83f
hermes -p spock cron runs a440b38586c9
docker compose ps
```

Não imprimir `.env`, `auth.json`, ambientes completos de containers, DSNs ou
tokens durante a coleta de evidências.

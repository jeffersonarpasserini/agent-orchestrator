# O6 — piloto operacional completo da homologação

## Envelope canônico

- `request_id`: `O6:server-homologation-20260814`
- objetivo: consolidar e comprovar os gates finais de homologação do Agent
  Orchestrator sem migration, deploy ou chamada paga;
- escopo: documentação de homologação, checklist OpenSpec, revisão independente,
  PR, CI, monitor Spock, merge autorizado, observabilidade e ledger;
- prioridade: alta;
- owner: `jeffersonarpasserini`;
- prazo: `2026-08-21T22:00:00-03:00`;
- budget: `USD 0`, chamadas pagas proibidas;
- política de aprovação: commit, push, PR e merge exigem autorização do owner;
  deploy, migration, credencial, publicação de porta, grant e ação destrutiva
  permanecem proibidos neste piloto;
- critérios de aceite:
  - O1–O5 reconciliados com evidência autoritativa;
  - tarefa persistida e replay idempotente pela API canônica;
  - diff limitado à homologação e sem segredos;
  - revisão independente Tuvok e decisão final Spock;
  - quatro checks aprovados no mesmo SHA e monitor Spock observado;
  - merge autorizado e SHA de `main` confirmado;
  - API, Phoenix, PostgreSQL e Kuma saudáveis após o merge;
  - ledger registra custo simulado e cobrado, com cobrança real zero;
  - relatório final inclui sessões, tentativas, riscos e rollback.

## Rollback

Reverter somente o commit documental do piloto por PR protegido. Como esta
mudança não altera imagem, schema, credencial, porta ou serviço, rollback
operacional não deve reiniciar containers nem restaurar banco.

## Estado

O1–O5 foram reconciliados em 2026-08-14. A tarefa foi criada pela API canônica
em `2026-08-14T21:43:30.343110+00:00`, com principal
`jeffersonarpasserini`, origem `api:homelab` e estado `received`. Uma segunda
submissão do mesmo envelope retornou o mesmo timestamp e
`idempotent_replay=true`, sem criar nova tarefa.

Essa é evidência operacional coletada pelo operador no host, por resposta da
API interna, sem imprimir a credencial. Ela não é reproduzível somente pelo
checkout e permanece sujeita à reconciliação final com a linha e os eventos no
PostgreSQL antes da decisão de homologação.

A revisão independente preliminar do PR #9 recebeu `GO` do Tuvok na sessão
`20260814_183736_1e7799`. A revisão do PR #10 recebeu `GO condicional` na
sessão `20260814_185825_8c55b6`; as duas condições documentais foram corrigidas
antes do merge.

## Sessões e handoffs

- planejamento e implementação: Codex no workspace compartilhado; o produto
  não expõe session ID local para este turno;
- revisão preliminar do PR #9: Tuvok, sessão `20260814_183736_1e7799`, `GO`;
- revisão do PR #10: Tuvok, sessão `20260814_185825_8c55b6`, `GO condicional`;
- condição apontada: atualizar o baseline de `main` e declarar a proveniência
  externa da evidência de runtime; ambas corrigidas após a revisão;
- monitor: job Spock `27ed14ebd83f`; a execução de 18:52 validou o SHA inicial
  `fb9a6483`, a execução autoritativa de 19:04:06 validou o SHA final
  `65ccef4886c9dc00a45ec92103539f711ea853f2` e persistiu
  `last_result=success`, e a execução pós-merge de 19:07:42 correlacionou esse
  head ao squash `c3be1a652f50000b1319137188a57ac143ad26f6`.

## Evidências de PR, CI e merge

- PR #10: `Prepare server homologation pilot`;
- SHA final da branch: `65ccef4`;
- checks no mesmo SHA: `Change hygiene`, `Python 3.12 tests`,
  `Python security` e `Validate Docker Compose`, todos aprovados;
- monitor Spock `27ed14ebd83f` executado manualmente após os checks, com
  resultado `succeeded`;
- squash merge autorizado em 2026-08-14;
- SHA integrado em `main`: `c3be1a652f50000b1319137188a57ac143ad26f6`.

## Evidências pós-merge

- API `agent-orchestrator-api-1`: `running=true`, health `healthy`;
- Phoenix `agent-orchestrator-phoenix-1`: `running=true`, health `healthy`;
- PostgreSQL `honcho-database-1`: `running=true`, health `healthy`;
- Uptime Kuma: container `uptime-kuma`, health `healthy`;
- tarefa canônica reconciliada no PostgreSQL: uma linha em estado `received` e
  exatamente um evento `received`;
- ledger O6 final: 6 sessões, 45 chamadas, 1.020,735 segundos, custo simulado
  US$ 1,622381649 e custo cobrado US$ 0,00;
- billing routes: `alibaba-coding-plan` para Tuvok e `openai-codex` para Spock,
  ambas incluídas em assinatura;
- rollback documental comprovado por aplicação reversa em modo `--check` do
  commit `c3be1a6`, sem modificar o worktree.

O smoke pós-merge sem modelo retornou `completed`. O Phoenix persistiu o trace
`5f674037c05b6007e632749f5138a025`, span `workflow.smoke`, entre
`2026-08-14 22:13:25.723197+00:00` e
`2026-08-14 22:13:25.727830+00:00`. A inspeção registrou somente a chave de
atributo `workflow`; nenhuma chave continha `authorization`, `password`,
`secret`, `token`, `dsn` ou `credential`.

### Reconciliação por sessão

| Sessão | Modelo/rota | Chamadas | Entrada/cache/output/reasoning | Simulado | Cobrado |
|---|---|---:|---:|---:|---:|
| `20260814_183736_1e7799` | `deepseek-v4-pro` / `alibaba-coding-plan` | 13 | 65.541 / 514.048 / 5.962 / 3.209 | US$ 0,035560699 | US$ 0,00 |
| `20260814_185825_8c55b6` | `deepseek-v4-pro` / `alibaba-coding-plan` | 10 | 49.614 / 309.760 / 4.254 / 2.372 | US$ 0,026405950 | US$ 0,00 |
| `cron_27ed14ebd83f_20260814_184811` | `gpt-5.6-sol` / `openai-codex` | 6 | 39.322 / 142.848 / 2.684 / 1.082 | US$ 0,348554000 | US$ 0,00 |
| `cron_27ed14ebd83f_20260814_185052` | `gpt-5.6-sol` / `openai-codex` | 5 | 41.014 / 111.616 / 2.851 / 1.218 | US$ 0,346408000 | US$ 0,00 |
| `cron_27ed14ebd83f_20260814_190314` | `gpt-5.6-sol` / `openai-codex` | 5 | 39.070 / 104.448 / 1.760 / 559 | US$ 0,300374000 | US$ 0,00 |
| `20260814_191018_2d94ff` | `gpt-5.6-sol` / `openai-codex` | 6 | 53.501 / 201.728 / 6.557 / 2.611 | US$ 0,565079000 | US$ 0,00 |

Os snapshots de preço são `deepseek-official-2026-08-12` e
`openai-2026-08-12`. Reasoning já integra output e não é somado novamente.

Não houve migration, deploy, mudança de credencial, publicação de porta,
grant, chamada pay-as-you-go, reinício ou indisponibilidade de serviço.

## Riscos residuais aceitos

- o filename do handoff conserva a data original `2026-08-13`, embora o
  conteúdo registre a atualização posterior; impacto apenas cosmético;
- o contêiner da API monta Tuvok, mas não Spock, em `/hermes-state`; por isso a
  coleta das sessões Spock ocorreu em modo somente leitura no host e o upsert
  oficial foi executado dentro da API;
- os itens pós-homologação registrados no OpenSpec permanecem não bloqueantes.

O primeiro parecer final do Spock, sessão `20260814_191018_2d94ff`, foi
`GO condicional`. As condições eram: correlacionar monitor e SHAs; explicitar
ingestão/redaction do trace; detalhar ledger por sessão; validar OpenSpec e
atualizar Graphify. As quatro condições foram tratadas neste relatório antes da
solicitação do parecer definitivo.

O parecer definitivo do Spock, na mesma sessão
`20260814_191018_2d94ff`, foi **GO pleno**. O revisor confirmou que não resta
blocker financeiro, de segurança, ledger, proteção da `main`, observabilidade
ou rollback. A sessão decisória foi reconciliada no ledger após o veredito,
elevando o total final para seis sessões e 45 chamadas, ainda com custo cobrado
zero.

## Decisão final de homologação

- **Veredito:** GO para operação autônoma contínua.
- **Autorização do proprietário:** concedida em 2026-08-14.
- **Revisão Spock:** GO pleno, sessão `20260814_191018_2d94ff`.
- **Baseline homologada:** `c3be1a652f50000b1319137188a57ac143ad26f6`,
  acrescida apenas deste registro final de evidências.
- **Pendências remanescentes:** itens pós-homologação, sem caráter bloqueador.

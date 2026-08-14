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
`20260814_183736_1e7799`. O PR, merge, observabilidade, ledger e decisão final
do O6 serão preenchidos somente após cada evidência existir.

## Sessões e handoffs

- planejamento e implementação: Codex no workspace compartilhado; o produto
  não expõe session ID local para este turno;
- revisão preliminar do PR #9: Tuvok, sessão `20260814_183736_1e7799`, `GO`;
- revisão do PR #10: Tuvok, sessão `20260814_185825_8c55b6`, `GO condicional`;
- condição apontada: atualizar o baseline de `main` e declarar a proveniência
  externa da evidência de runtime; ambas corrigidas após a revisão;
- monitor: job Spock `27ed14ebd83f`, execução manual concluída após publicação
  do SHA `fb9a6483a0e678549dfb379b04226e18ad3cebe8`.

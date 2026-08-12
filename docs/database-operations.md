# Operação do banco da orquestração

O banco `agent_orchestrator` compartilha a instância PostgreSQL do Honcho, mas
usa banco, role e senha exclusivos. A senha existe somente nos arquivos `.env`
locais ignorados pelo Git.

## Limites de acesso

- o role é owner apenas do banco homônimo;
- `PUBLIC` não possui `CONNECT` no banco;
- o role não acessa `honcho` nem `db_qualitascare`;
- não há privilégios de superuser, criação de role/banco ou replicação;
- `vector` permanece desativada até uma migration justificar seu uso.

## Backup e restauração

O backup inicial é lógico, com `pg_dump --format=custom`, salvo no diretório
ignorado `agent-orchestrator/backups/`. Esse caminho está sob
`/data/homelab` no Kopia. O teste restaura em banco temporário, valida a versão
da migration e remove o banco ao final, sem interromper Honcho.

Antes da operação contínua, o dump deve ser automatizado, ter retenção definida
no Kopia e emitir alerta em caso de falha. Snapshot de volume não substitui o
dump consistente.


## Evidência da Fase 2

Validação executada em 2026-08-10:

- migration aplicada: `0001_baseline`;
- dump: `agent_orchestrator-phase2.dump`, formato custom, sem owner/ACL;
- SHA-256: `983571c0c7f93972108ccc3ae9ad2ec50c85fdb25c4f26953aafe79e7c2a09a8`;
- restauração PostgreSQL: versão `0001_baseline` confirmada em banco temporário;
- snapshot Kopia: `11ed0479f0d151d43c15ea91e0acdd8c`;
- root Kopia: `k68521aca9dc8461d1e354d682da5e1f8`;
- restauração Kopia: 1 arquivo restaurado e hash idêntico;
- banco e diretório temporários removidos após validação.

## Evidência da migration 0006

Validação executada em 2026-08-12:

- dump pré-migration: `agent_orchestrator-pre-0006-20260812.dump`, formato
  custom, sem owner/ACL e modo `0600`;
- SHA-256: `577a473f6ece3060895c37a9708a7138e0c75f4b6f27e6bd4487a579038fb3b3`;
- restauração validada em PostgreSQL 16 efêmero, isolado de rede e com dados
  em `tmpfs`;
- migrations `0001`–`0005` e as 13 linhas do ledger confirmadas na restauração;
- container temporário removido após a validação;
- migration `0006_pilot_cost_breakdown` aplicada pelo usuário
  `agent_orchestrator`;
- backfill concluído a partir dos IDs de sessão, sem chamadas de modelo;
- total simulado: US$ 1,400755612200;
- total cobrado: US$ 0,071328612200;
- economia atribuída às assinaturas: US$ 1,329427000000;
- constraints confirmaram `cost_usd = billed_cost_usd` e
  `billed_cost_usd <= simulated_cost_usd` em todas as 13 tarefas.
- imagem `agent-orchestrator:0.1.0` reconstruída e somente o serviço `api`
  recriado; PostgreSQL e Phoenix não foram reiniciados;
- readiness confirmou o banco `agent_orchestrator` e o usuário
  `agent_orchestrator`;
- `GET /pilot/summary` confirmou 13 tarefas, 31 chamadas, US$ 1,4007556122
  simulados, US$ 0,0713286122 cobrados e US$ 1,329427 de economia.

O backfill corrigiu `O04`: o ledger antigo incluía três IDs de evidência,
mas contabilizava somente a chamada DeepSeek Pro. A nova soma inclui também a
chamada DeepSeek Flash, elevando o cobrado de US$ 0,009611963 para
US$ 0,013719428600; a chamada Sol permaneceu com cobrança zero e custo
equivalente simulado.

## Evidência da release candidata da Fase 9

- dump: `agent_orchestrator-phase9-rc1.dump`, formato custom, sem owner/ACL,
  modo `0600`;
- SHA-256: `df03ef7efb8e814a9dc3a4b022a488b3991dd9a40447250783337c54354de895`;
- restore validado em PostgreSQL 16 efêmero, sem rede e em `tmpfs`;
- confirmadas migrations `0001`–`0006`, 20 tarefas e totais financeiros do
  fechamento da Fase 8;
- ambiente temporário removido após a validação.

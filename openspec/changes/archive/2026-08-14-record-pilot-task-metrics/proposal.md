## Why

O piloto medido precisa de um ledger local reproduzível por tarefa, sem
duplicar registros quando uma formalização é repetida e sem incluir
credenciais no payload persistido.

## What Changes

- Persistir agregados de tentativas, chamadas, latência e custo por tarefa.
- Usar `task_id` como identidade idempotente e atualizar o registro existente.
- Registrar perfis/modelos e IDs de sessão como evidência rastreável.
- Permitir leitura ordenada para o resumo local do piloto.

## Impact

A migration `0002_pilot_task_metrics` adiciona uma tabela no schema
`orchestrator`. Não há endpoint de escrita, credencial no payload, chamada de
modelo, commit, push ou deploy.

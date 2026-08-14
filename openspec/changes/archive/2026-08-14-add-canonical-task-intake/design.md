## Context

A API está restrita ao homelab, mas alcance de rede não prova identidade. O
primeiro contrato operacional possui um único solicitante canônico; expansão a
múltiplos principals exigirá mecanismo de identidade separado.

## Decision

- `TASK_INTAKE_BEARER_TOKEN` permanece somente no ambiente da API.
- `TASK_INTAKE_PRINCIPAL` e `TASK_INTAKE_ORIGIN` são definidos pelo servidor.
- O token é comparado em tempo constante e nunca persistido, logado ou traçado.
- O payload é serializado canonicamente e recebe SHA-256.
- Uma transação insere tarefa e evento `received`; conflito consulta o hash.
- Mesmo ID/hash retorna a linha existente; mesmo ID/hash diferente retorna 409.
- Eventos são append-only. Retomada exige nova autorização quando a transição
  envolver ação material; aprovações anteriores não são copiadas.

## Safety

- tamanho de texto, arrays e budget é limitado antes de acessar o banco;
- timestamps devem ter timezone e prazos vencidos são rejeitados;
- moeda inicial é `USD`, teto não negativo e chamada paga é explicitamente
  `forbidden` ou `approval_required`;
- anexos ficam fora do primeiro release;
- respostas e traces usam request ID, principal e estado, nunca token ou corpo
  irrestrito;
- indisponibilidade de banco ou configuração retorna erro genérico e não aceita
  a tarefa em memória.

## Rollback

Desabilitar o endpoint removendo a credencial e restaurar a imagem anterior. A
tabela permanece preservada; rollback não apaga tarefas ou eventos.

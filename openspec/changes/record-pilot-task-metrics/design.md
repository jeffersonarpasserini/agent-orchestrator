## Context

Cada tarefa do piloto pode envolver mais de uma sessão e até dois ciclos de
revisão. O ledger precisa representar o resultado agregado sem transformar uma
reexecução do mesmo registro em duplicata.

## Decision

`task_id` é a chave primária. A escrita usa `INSERT ... ON CONFLICT (task_id)
DO UPDATE`, substitui todos os agregados e atualiza `recorded_at`. Arrays de
perfis/modelos e evidências são serializados como JSONB. A conexão é recebida
por configuração e nunca integra os parâmetros do registro.

Escritas concorrentes do mesmo `task_id` seguem semântica last-write-wins. Isso
é aceitável no piloto, cujo registro é serializado pelo gate humano; uma
expansão para múltiplos escritores exigirá versão ou lock otimista.

`cost_usd` permanece como alias compatível de `billed_cost_usd`. O novo
`simulated_cost_usd` representa o custo equivalente calculado por tokens. O
catálogo de preços é versionado por snapshot; fontes proxy são identificadas e
nunca apresentadas como preço oficial do provider observado.

## Safety

- tentativas devem ser positivas;
- chamadas, latência e custo não podem ser negativos;
- a transação é confirmada somente depois do upsert;
- a API expõe somente leitura do resumo agregado, sem endpoint de escrita;
- IDs de evidência não devem conter prompts ou credenciais.

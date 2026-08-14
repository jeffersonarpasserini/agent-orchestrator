# pilot-task-metrics Specification

## Purpose
TBD - created by archiving change record-pilot-task-metrics. Update Purpose after archive.
## Requirements
### Requirement: Métricas são agregadas por tarefa piloto

O orquestrador MUST persistir resultado, perfis/modelos, tentativas, chamadas,
latência, custo e evidências de cada tarefa usando `task_id` como identidade.

O custo MUST distinguir o equivalente simulado pelo consumo de tokens do valor
efetivamente cobrado. Em billing por assinatura, o cobrado MUST ser zero; em
billing por token, simulado e cobrado MUST ser iguais.

#### Scenario: Primeira gravação

- **WHEN** uma tarefa ainda não existe no ledger
- **THEN** seus agregados e evidências são inseridos em uma transação

#### Scenario: Repetição da mesma tarefa

- **WHEN** o mesmo `task_id` é registrado novamente
- **THEN** o registro existente é atualizado sem criar uma segunda linha

### Requirement: Payload do ledger não contém credenciais

O registro MUST receber somente agregados operacionais e IDs de evidência; a
URL de conexão e outras credenciais MUST permanecer fora dos parâmetros
persistidos.

#### Scenario: Escrita parametrizada

- **WHEN** uma métrica é registrada
- **THEN** a conexão usa a configuração privada e os parâmetros SQL não contêm
  essa URL

### Requirement: Agregados inválidos são rejeitados

Tentativas MUST ser positivas e chamadas, latência e custo MUST ser não
negativos antes da persistência.

#### Scenario: Valor negativo

- **WHEN** latência ou custo é negativo
- **THEN** a métrica é rejeitada antes de abrir a conexão

#### Scenario: Assinatura incluída

- **WHEN** uma sessão OpenAI Codex ou Qwen Token Plan tem uso de tokens
- **THEN** o ledger registra o preço equivalente em `simulated_cost_usd` e zero
  em `billed_cost_usd`

#### Scenario: Cobrança por token

- **WHEN** uma sessão usa billing pay-per-token
- **THEN** `simulated_cost_usd` e `billed_cost_usd` são iguais

#### Scenario: Preço Qwen por proxy

- **WHEN** `qwen3.8-max` é estimado sem preço USD oficial do Token Plan
- **THEN** o snapshot usa `qwen/qwen3.8-2.4t-a95b` a US$ 2/MTok de entrada e
  US$ 6/MTok de saída, com status `proxy_estimate`

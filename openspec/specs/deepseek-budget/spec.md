# deepseek-budget Specification

## Purpose
TBD - created by archiving change enforce-deepseek-pilot-budget. Update Purpose after archive.
## Requirements
### Requirement: Chamadas DeepSeek respeitam os tetos aprovados

O orquestrador MUST bloquear uma nova chamada DeepSeek quando o gasto persistido
do dia atingir US$ 1 ou o gasto desde o início do piloto atingir US$ 10.

#### Scenario: Orçamento disponível

- **WHEN** ambos os gastos persistidos estão abaixo dos respectivos tetos
- **THEN** a chamada pode prosseguir

#### Scenario: Teto diário atingido

- **WHEN** o gasto DeepSeek do dia é igual ou superior a US$ 1
- **THEN** a chamada é bloqueada antes de contatar o provedor

#### Scenario: Teto total atingido

- **WHEN** o gasto DeepSeek do piloto é igual ou superior a US$ 10
- **THEN** a chamada é bloqueada antes de contatar o provedor

### Requirement: Evidência financeira falha fechada

O orquestrador MUST bloquear chamadas DeepSeek quando configuração, banco ou
custo necessário não puder ser validado.

#### Scenario: Custo desconhecido

- **WHEN** uma sessão DeepSeek aplicável não possui custo real nem estimado
- **THEN** uma nova chamada DeepSeek é bloqueada

#### Scenario: Outro provedor

- **WHEN** o perfil não usa DeepSeek
- **THEN** o gate financeiro DeepSeek não altera sua execução

### Requirement: Snapshot agregado não expõe credenciais

A API local MUST expor o snapshot do piloto usando somente gastos e limites
agregados, sem credenciais, URLs de banco, caminhos de arquivos, perfis ou
tokens. O endpoint permanece restrito ao bind local do homelab.

#### Scenario: Snapshot disponível

- **WHEN** a evidência financeira pode ser validada
- **THEN** `GET /pilot/budget` retorna somente os gastos diário e acumulado e os
  respectivos limites

#### Scenario: Evidência indisponível

- **WHEN** o guard relata uma falha de evidência financeira
- **THEN** `GET /pilot/budget` retorna HTTP 503 com mensagem genérica, sem
  detalhes internos da falha

### Requirement: Bloqueio financeiro é um estado terminal do workflow

O workflow MUST converter uma falha do gate financeiro em `budget_blocked` e
terminar sem iniciar ou atribuir uma sessão de modelo.

#### Scenario: Teto ou evidência bloqueia a execução

- **WHEN** o adaptador relata `BudgetError` antes da chamada ao provedor
- **THEN** o workflow retorna `status=budget_blocked` com a causa operacional e
  mantém texto, sessão, correlação, uso e tool calls vazios

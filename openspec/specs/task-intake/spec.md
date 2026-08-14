# task-intake Specification

## Purpose
TBD - created by archiving change add-canonical-task-intake. Update Purpose after archive.
## Requirements
### Requirement: Entrada canônica autentica identidade fora do payload

A API MUST aceitar tarefas somente com bearer token válido e MUST derivar
principal e origem da configuração confiável do servidor.

#### Scenario: Credencial ausente ou inválida

- **WHEN** uma requisição não apresenta o token canônico válido
- **THEN** a API retorna 401 sem persistir tarefa ou evento

#### Scenario: Conteúdo tenta declarar identidade

- **WHEN** o payload contém campo extra de principal, origem ou autoridade
- **THEN** a validação rejeita o payload

### Requirement: Envelope obrigatório falha fechado

A API MUST exigir request ID, objetivo, escopo, prioridade, owner, prazo,
budget, política de aprovação e critérios de aceite dentro dos limites.

#### Scenario: Campo material ausente

- **WHEN** owner, budget ou critério de aceite está ausente ou vazio
- **THEN** a API retorna 422 sem persistência parcial

### Requirement: Request ID é idempotente e persistente

A API MUST persistir um hash canônico do envelope no PostgreSQL.

#### Scenario: Repetição equivalente

- **WHEN** o mesmo principal envia o mesmo request ID e envelope equivalente
- **THEN** a API retorna a tarefa existente sem novo evento

#### Scenario: Reutilização conflitante

- **WHEN** o mesmo request ID é enviado com hash diferente
- **THEN** a API retorna 409 e preserva a tarefa original

### Requirement: Ciclo de vida é auditável

Cancelamento e retomada MUST produzir eventos append-only com ator, timestamp e
estado, sem transferir aprovações consumidas ou expiradas.

#### Scenario: Retomada após cancelamento

- **WHEN** uma tarefa cancelada é retomada pelo principal autorizado
- **THEN** um evento `resumed` é criado e qualquer ação material volta a
  `awaiting_approval`

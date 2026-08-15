# server-homologation Specification

## Purpose
Definir os gates rastreáveis e fail-closed para homologar o servidor e executar
um piloto operacional completo sem promover automaticamente pilotos opcionais.

## Requirements
### Requirement: Homologação usa gates rastreáveis e fail-closed

O servidor MUST ser homologado somente quando O1–O6 possuírem evidência
autoritativa, revisão aplicável, rollback e resultado explícito.

#### Scenario: Gate sem evidência suficiente

- **WHEN** qualquer gate bloqueante não possui SHA, sessão, teste, estado do
  serviço ou aprovação exigida
- **THEN** a decisão permanece `NO-GO` ou `GO condicional` e identifica a
  pendência sem inferir conclusão

#### Scenario: Gates bloqueantes aprovados

- **WHEN** O1–O6 satisfazem seus critérios e não existe bloqueador financeiro,
  de segredo, ledger, proteção da `main` ou restauração
- **THEN** a decisão pode registrar `GO` para operação autônoma contínua no SHA
  efetivamente verificado

### Requirement: Piloto O6 percorre o fluxo operacional completo

O piloto O6 MUST partir da entrada canônica e percorrer planejamento,
implementação, revisão, PR, CI, monitoramento, aprovação, merge,
observabilidade, custo e relatório final.

#### Scenario: Piloto concluído

- **WHEN** uma mudança pequena, real, reversível e sem migration termina
- **THEN** request ID, decisões, sessões, SHA, checks, traces, ledger, custo e
  rollback são correlacionáveis no relatório final

#### Scenario: Cobrança ou telemetria ambígua

- **WHEN** custo cobrado, rota de billing, trace ou SHA não pode ser comprovado
- **THEN** O6 não é aprovado e a homologação permanece bloqueada

### Requirement: Estado vivo é verificado no ambiente correto

Checks locais e inspeções Docker MUST distinguir limitações do sandbox do
estado real do host e MUST NOT imprimir credenciais, DSNs ou ambientes completos.

#### Scenario: Endpoint do host inacessível no sandbox

- **WHEN** a rede isolada não alcança um endpoint publicado em loopback
- **THEN** a evidência usa healthcheck do container ou uma verificação aprovada
  no host e registra a limitação

### Requirement: Pilotos posteriores não são promovidos por associação

Reserva DeepSeek, mudanças futuras de modelo e OpenObserve MUST manter seus
próprios gates, autorizações, janelas e rollback.

#### Scenario: Homologação inicial sem piloto opcional concluído

- **WHEN** a arquitetura homologada mantém uma capacidade opcional desabilitada
  ou ainda sujeita a promoção independente
- **THEN** suas pendências são pós-homologação e não são marcadas como
  concluídas nem ativadas automaticamente

### Requirement: Decisão final é publicada sem esconder riscos residuais

O relatório de homologação MUST listar escopo, versão, evidências, pendências
não bloqueantes, riscos aceitos, owners e procedimento de rollback.

#### Scenario: Promoção para homologado

- **WHEN** o owner aprova a decisão final após CI e revisão independentes
- **THEN** documentação e inventário refletem o mesmo estado e nenhuma pendência
  bloqueante permanece aberta

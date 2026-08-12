## ADDED Requirements

### Requirement: OpenObserve é implantado inicialmente de forma isolada

O homelab MUST executar o piloto OpenObserve em modo single-node, com versão,
volume, credenciais e limites explícitos, sem alterar a disponibilidade do
Phoenix.

#### Scenario: Piloto iniciado

- **WHEN** OpenObserve é implantado em homologação
- **THEN** usa versão fixada, volume próprio e porta vinculada ao loopback

#### Scenario: OpenObserve falha

- **WHEN** o novo backend fica indisponível
- **THEN** workflows e exportação para Phoenix continuam funcionando

### Requirement: Telemetria sensível é filtrada antes da ingestão

O Collector MUST remover credenciais, DSNs, prompts sensíveis e dados pessoais
ou clínicos antes de enviar telemetria ao OpenObserve.

#### Scenario: Atributo proibido é recebido

- **WHEN** um evento contém dado fora da allowlist ou padrão sensível conhecido
- **THEN** o valor é removido ou mascarado antes da exportação

#### Scenario: Política não pode ser aplicada

- **WHEN** a redaction não pode ser comprovada
- **THEN** a fonte afetada não é habilitada no piloto

### Requirement: A adoção é reversível e baseada em evidências

O piloto MUST comprovar retenção, consumo de recursos, backup, restauração e
rollback antes de qualquer consolidação de observabilidade.

#### Scenario: Período comparativo concluído

- **WHEN** ao menos uma semana de telemetria controlada foi observada
- **THEN** cobertura, custo operacional, recursos e usabilidade são comparados com Phoenix

#### Scenario: Rollback acionado

- **WHEN** OpenObserve não satisfaz um critério bloqueante
- **THEN** seu exportador é removido sem apagar dados e Phoenix permanece como backend ativo

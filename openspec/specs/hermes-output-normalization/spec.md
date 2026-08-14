# hermes-output-normalization Specification

## Purpose
TBD - created by archiving change normalize-tirith-warning. Update Purpose after archive.
## Requirements
### Requirement: Avisos operacionais iniciais do Tirith não contaminam o payload

O adaptador MUST remover uma ou mais linhas iniciais contíguas que correspondam exatamente ao aviso operacional conhecido do Tirith antes de devolver o texto do agente.

#### Scenario: Aviso seguido por JSON

- **WHEN** stdout começa com o aviso exato do Tirith seguido por um objeto JSON
- **THEN** o texto normalizado contém somente o objeto JSON diretamente analisável

#### Scenario: Múltiplos avisos iniciais

- **WHEN** stdout começa com mais de uma linha contígua do aviso exato
- **THEN** todas essas linhas iniciais são removidas

### Requirement: Conteúdo do agente permanece íntegro

O adaptador MUST preservar conteúdo que não seja uma linha inicial exata do aviso conhecido e MUST manter a extração de session ID existente.

#### Scenario: Saída sem aviso

- **WHEN** stdout não começa com o aviso exato
- **THEN** o comportamento de normalização existente permanece inalterado

#### Scenario: Texto semelhante após início do payload

- **WHEN** a linha do aviso aparece depois que o payload começou
- **THEN** ela é preservada como conteúdo do agente

#### Scenario: Session ID presente

- **WHEN** stdout contém um session ID reconhecido
- **THEN** o ID continua sendo extraído e o payload restante continua correto

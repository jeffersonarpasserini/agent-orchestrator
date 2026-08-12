## ADDED Requirements

### Requirement: GLM-5.2 usa somente o Token Plan Individual

Chamadas do candidato MUST usar o ID exato `glm-5.2`, a credencial dedicada e o
endpoint OpenAI-compatible do Token Plan, sem fallback para outro billing mode.

#### Scenario: Chamada autorizada

- **WHEN** o candidato executa uma chamada GLM-5.2
- **THEN** o consumo aparece como Credits no Token Plan

#### Scenario: Credencial ou endpoint incompatível

- **WHEN** a configuração não comprova o par correto de credencial e endpoint
- **THEN** a chamada é bloqueada antes de contatar o provedor

#### Scenario: Cota indisponível

- **WHEN** o saldo ou a janela aplicável não pode ser comprovado ou está esgotado
- **THEN** o piloto para sem fallback pay-as-you-go

### Requirement: Function calling do GLM preserva o contrato de ferramentas

A integração MUST enviar os parâmetros exigidos pelo GLM e MUST devolver tool
calls válidas sem expor reasoning como resposta final.

#### Scenario: Ferramentas disponíveis

- **WHEN** uma chamada GLM inclui ferramentas
- **THEN** a integração usa streaming e `tool_stream: true`

#### Scenario: Tool call emitida

- **WHEN** GLM-5.2 seleciona uma ferramenta
- **THEN** nome, argumentos e correlação são preservados para execução controlada

#### Scenario: Parâmetro incompatível

- **WHEN** o cliente não consegue enviar ou interpretar o contrato exigido
- **THEN** a avaliação falha explicitamente e não simula sucesso sem ferramentas

### Requirement: Thinking é controlado e contabilizado

A integração MUST separar `reasoning_content` do conteúdo final, limitar a
conclusão e registrar o consumo aplicável ao piloto.

#### Scenario: Thinking habilitado

- **WHEN** GLM-5.2 retorna raciocínio e resposta
- **THEN** o payload final contém somente a resposta e as métricas contabilizam o raciocínio

#### Scenario: Conversa continua

- **WHEN** uma segunda chamada depende do turno anterior
- **THEN** o reasoning é preservado integralmente ou removido por uma decisão explícita com `clear_thinking`

#### Scenario: Limite de consumo atingido

- **WHEN** o limite aprovado de conclusão ou Credits é alcançado
- **THEN** a execução termina ou é bloqueada sem aumentar silenciosamente o orçamento

### Requirement: Concorrência respeita o plano Lite

O piloto MUST limitar chamadas Token Plan concorrentes para não exceder a
capacidade contratada de 1–2 agentes.

#### Scenario: Duas chamadas Token Plan estão ativas

- **WHEN** uma terceira chamada Token Plan é solicitada
- **THEN** ela aguarda capacidade ou falha de forma transitória e explícita

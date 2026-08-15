# agent-model-routing Specification

## Purpose
Definir gates comparáveis e rastreáveis para trocar o modelo efetivo de um
perfil sem ampliar suas permissões, responsabilidades ou autoridade.
## Requirements
### Requirement: GLM-5.2 é avaliado isoladamente antes da promoção

O sistema MUST manter `la-forge` em `qwen3.8-max` enquanto `glm-5.2` não tiver
passado pelos gates de protocolo, qualidade, segurança, consumo e rollback.

#### Scenario: Piloto ainda não aprovado

- **WHEN** qualquer gate obrigatório ainda não possui evidência aprovada
- **THEN** o modelo efetivo de `la-forge` permanece `qwen3.8-max`

#### Scenario: Todos os gates aprovados

- **WHEN** Tuvok aprova a revisão independente e Spock registra a decisão final
- **THEN** `glm-5.2` pode ser promovido como modelo efetivo de `la-forge`

#### Scenario: Gate reprovado

- **WHEN** um gate bloqueante falha ou não pode ser comprovado
- **THEN** o candidato não é promovido e o baseline permanece disponível

### Requirement: O papel e a governança de La Forge permanecem estáveis

A troca de modelo MUST NOT ampliar permissões, alterar responsabilidades ou
remover os gates humanos e independentes aplicáveis ao perfil.

#### Scenario: Modelo candidato executa a avaliação

- **WHEN** `glm-5.2` recebe a tarefa representativa
- **THEN** usa o mesmo OpenSpec, contexto, ferramentas, limites e critérios do baseline

#### Scenario: Decisão material é necessária

- **WHEN** a tarefa contém ambiguidade ou conflito fora do escopo aprovado
- **THEN** La Forge encaminha a decisão a Spock em vez de ampliar o escopo

### Requirement: A avaliação é comparável e rastreável

O piloto MUST registrar evidências suficientes para comparar `glm-5.2` e
`qwen3.8-max` sem depender de impressão subjetiva não documentada.

#### Scenario: Execuções comparativas concluídas

- **WHEN** os dois modelos concluem o cenário aprovado
- **THEN** sessões, resultado, tool calls, tokens, latência e Credits são registrados

#### Scenario: Condições divergentes

- **WHEN** contexto, permissões ou critérios diferem entre as execuções
- **THEN** a comparação é inválida e não pode autorizar promoção

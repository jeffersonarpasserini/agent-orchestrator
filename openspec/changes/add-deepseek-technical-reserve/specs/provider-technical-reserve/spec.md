# ADDED Requirements

## Requirement: QwenCloud é a rota primária

Perfis DeepSeek migrados MUST tentar somente a rota `qwencloud_primary` na
execução normal. A rota `deepseek_reserve` MUST permanecer desabilitada por
padrão e fora das fallback chains implícitas do Hermes.

### Scenario: Capacidade primária disponível

- **WHEN** o Token Plan aceita a chamada
- **THEN** somente o QwenCloud é usado e nenhum grant de reserva é criado

## Requirement: Somente falhas elegíveis solicitam reserva

O orquestrador MUST usar uma allowlist de razões normalizadas para produzir
`reserve_required`. Status HTTP isolado ou resposta de baixa qualidade MUST NOT
autorizar a reserva.

### Scenario: Janela ou Credits esgotados

- **WHEN** o provider comprova `subscription_window_exhausted` ou
  `subscription_credits_exhausted`
- **THEN** o workflow pode terminar em `reserve_required` sem chamar a DeepSeek
  direta

### Scenario: Observação em modo shadow

- **WHEN** uma falha elegível ocorre para um perfil observado e o kill switch
  está desligado
- **THEN** `reserve_required` contém somente tarefa, perfil, papel, modelos e
  razão normalizada, sem prompt, credencial, sessão, uso ou chamada de reserva

### Scenario: Reserva negada no shadow

- **WHEN** o operador nega uma solicitação elegível
- **THEN** o workflow termina em `reserve_denied` sem chamar provider

### Scenario: Erro não elegível

- **WHEN** ocorre erro de autenticação, payload, ferramenta, política, modelo,
  código local ou evidência financeira
- **THEN** a execução falha explicitamente e a reserva não é solicitada

## Requirement: Reserva exige grant humano de uso único

Uma chamada `deepseek_reserve` MUST exigir grant válido, aprovado por humano,
vinculado a tarefa, perfil, modelo, custo, quantidade de chamadas e expiração.

### Scenario: Grant ausente

- **WHEN** o workflow está em `reserve_required` sem grant
- **THEN** nenhuma chamada direta é enviada

### Scenario: Grant válido

- **WHEN** o grant corresponde integralmente ao pedido e aos tetos
- **THEN** ele é consumido atomicamente e o estado interno muda para
  `reserve_approved` antes de uma única tentativa

### Scenario: Reutilização ou alteração

- **WHEN** um grant consumido, expirado ou de outro escopo é apresentado
- **THEN** a reserva termina bloqueada sem chamada ao provider

### Scenario: Aprovação apresentada no modo shadow

- **WHEN** uma decisão aprovada e um grant são apresentados no modo shadow
- **THEN** o workflow retorna `reserve_denied` e não consome o grant

## Requirement: Orçamento direto é independente e fail-closed

O gasto DeepSeek direto MUST possuir tetos diário, mensal, por tarefa e por
grant independentes dos Credits do Token Plan.

### Scenario: Saldo e tetos comprovados

- **WHEN** saldo, gasto e custo máximo podem ser comprovados abaixo dos limites
- **THEN** uma reserva previamente aprovada pode prosseguir

### Scenario: Saldo insuficiente ou evidência indisponível

- **WHEN** a DeepSeek retorna saldo insuficiente ou qualquer evidência exigida
  não pode ser validada
- **THEN** a reserva termina em `budget_blocked` sem contorno automático

## Requirement: Modelos são mapeados explicitamente por rota

O orquestrador MUST selecionar IDs a partir de tabela versionada e MUST NOT
inferir equivalência entre variantes ou snapshots de providers diferentes.

### Scenario: Flash migrado

- **WHEN** um perfil Flash solicita reserva
- **THEN** o roteamento usa o par explicitamente validado
  `deepseek-v4-flash-0731` / `deepseek-v4-flash` e registra o modelo efetivo

### Scenario: Compatibilidade não comprovada

- **WHEN** thinking, ferramentas, JSON, streaming ou limites não passam nos
  testes de uma rota
- **THEN** essa rota permanece bloqueada para o perfil

## Requirement: Resultado ambíguo não é repetido

Retry automático da reserva MUST ser proibido quando a chamada pode ter sido
aceita pelo provider.

### Scenario: Timeout apó envio

- **WHEN** não é possível provar se a inferência foi executada
- **THEN** o workflow retorna `reserve_outcome_unknown` e exige reconciliação
  antes de novo grant

## Requirement: Toda reserva é auditável sem segredos

O ledger MUST distinguir rota, causa, grant, aprovador, modelo efetivo, sessão,
tokens, latência e custo, sem persistir API keys ou prompts sensíveis.

### Scenario: Reserva concluída

- **WHEN** uma chamada direta termina
- **THEN** seu custo e billing route são atribuídos à tarefa e ao grant

## Requirement: Kill switch restaura falha explícita

O operador MUST poder desabilitar globalmente a reserva sem alterar a rota
primária.

### Scenario: Kill switch ativo

- **WHEN** a rota primária está bloqueada e o kill switch está ativo
- **THEN** o workflow retorna `budget_blocked` e ignora grants pendentes

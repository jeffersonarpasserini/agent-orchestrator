# agent-team-governance Specification

## ADDED Requirements

### Requirement: Painel multidisciplinar de specs

Toda spec de projeto MUST passar por Seven, Troi e B'Elanna antes da decisão
final de Spock. Os participantes MUST poder propor modificações justificadas.

#### Scenario: Elaboração ou revisão de spec

- **WHEN** uma spec nova ou existente entra em revisão
- **THEN** Seven pesquisa lacunas e alternativas
- **AND** Troi valida intenção, escopo e critérios de aceite
- **AND** B'Elanna valida viabilidade técnica e integrações
- **AND** Spock consolida as propostas e toma a decisão final

### Requirement: Desenvolvimento complexo em paralelo

La Forge MUST poder liderar tarefas complexas em paralelo com outros
desenvolvedores, com escopos independentes. Contratos, schema ou arquitetura
compartilhados MUST permanecer coordenados e sujeitos à decisão de Spock.

#### Scenario: Implementação com múltiplas frentes

- **WHEN** uma spec aprovada contém uma frente complexa e frentes independentes
- **THEN** La Forge lidera a frente complexa
- **AND** B'Elanna, Barclay, Data ou outros especialistas podem executar frentes paralelas
- **AND** Rutherford valida integração e regressão
- **AND** Tuvok conduz revisão independente

### Requirement: Owners separados para a reserva DeepSeek

O sistema MUST registrar responsabilidades separadas para decisão, operação,
segurança, finanças, banco, testes, documentação e execução do piloto.

#### Scenario: Descoberta dos owners

- **WHEN** a política da reserva é consultada
- **THEN** Spock responde por grants e decisão final
- **AND** O'Brien responde por operação, incidentes e kill switch
- **AND** Tuvok responde por segurança e revisão independente
- **AND** Data responde por finanças, ledger e reconciliação
- **AND** Bashir responde por migration, backup e restauração
- **AND** Rutherford responde por testes e evidências
- **AND** Uhura responde pela documentação
- **AND** Barclay executa o piloto Flash inicial

### Requirement: Alfred coordena somente relatórios

Alfred MUST poder solicitar status e relatórios a qualquer agente e consolidar
pendências, riscos, custos e evidências. Essa coordenação MUST NOT autorizar
mutações, gastos, grants, deploy, commit, alteração ou aprovação de specs.

#### Scenario: Alfred solicita relatório

- **WHEN** Alfred cria um pedido de relatório para um agente conhecido
- **THEN** o sistema retorna um artefato marcado como `report_only`
- **AND** nenhuma autoridade material é adicionada ao pedido

#### Scenario: Outro perfil tenta usar a coordenação de Alfred

- **WHEN** outro perfil tenta criar o pedido em nome do coordenador pessoal
- **THEN** o sistema rejeita a solicitação

### Requirement: Política consultável sem efeitos colaterais

O sistema MUST expor o catálogo e os workflows por operações somente leitura e
MUST NOT despachar perfis como efeito da consulta.

#### Scenario: Consulta da equipe

- **WHEN** um consumidor consulta agentes ou workflows
- **THEN** recebe responsabilidades, autoridades e ordem declaradas
- **AND** nenhum agente é executado

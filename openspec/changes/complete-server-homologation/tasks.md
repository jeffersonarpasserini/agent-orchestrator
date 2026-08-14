## 1. Consolidar baseline e gates O1–O5

- [x] 1.1 Atualizar o handoff com O1 aprovado e evidências atuais do job NVD
- [x] 1.2 Registrar formalmente O2 a partir do PR #2, incluindo SHA com falha,
  detecção do monitor, causa, correção, SHA verde e estado final
- [x] 1.3 Revalidar O3 pelos registros do Kuma e pelo healthcheck atual de API,
  Phoenix e PostgreSQL, sem repetir indisponibilidade fora de janela
- [x] 1.4 Reconciliar O4 com migration `0007`, contrato canônico, autenticação,
  idempotência, cancelamento, retomada e rollback já exercitado
- [x] 1.5 Reconciliar O5 com a matriz de autonomia e os kill switches financeiro
  e operacional exercitados sem chamada paga
- [x] 1.6 Confirmar proteção de `main`, quatro checks obrigatórios, jobs Spock e
  ausência de bypass usado na homologação

## 2. Executar e fechar O6

- [x] 2.1 Definir request ID, objetivo, escopo, owner, prazo, budget, política de
  aprovação, critérios de aceite e rollback de uma mudança real sem migration
- [x] 2.2 Submeter a tarefa pela entrada canônica e comprovar identidade,
  idempotência e trilha persistente
- [x] 2.3 Registrar planejamento, delegação, implementação e sessões por agente
- [x] 2.4 Obter revisão independente de Tuvok sobre diff, segurança e evidências
- [x] 2.5 Abrir PR, observar o monitor Spock e obter os quatro checks no mesmo SHA
- [x] 2.6 Obter aprovação de merge, integrar pela proteção de branch e verificar o
  SHA efetivamente presente em `main`
- [x] 2.7 Confirmar readiness, Phoenix, Kuma, PostgreSQL e ausência de segredo em
  logs/traces após o merge
- [x] 2.8 Reconciliar chamadas, tokens, custo simulado, custo cobrado e rota de
  billing no ledger
- [x] 2.9 Exercitar ou comprovar rollback da mudança no menor escopo seguro
- [x] 2.10 Publicar relatório O6 com tempo, tentativas, chamadas, custos, riscos,
  sessões, PR, SHA e decisão final de Spock

## 3. Fechar a atualização documental GLM em curso

- [x] 3.1 Revisar o diff do PR #9 e confirmar que contém somente os dois arquivos
  do piloto GLM
  - Evidência: SHA `09e6abb639e846af68f89a864e1f8e9734995d4a`, quatro
    checks aprovados e revisão Tuvok `GO` na sessão
    `20260814_183736_1e7799`; backup confirmado no host em modo `0600` com
    SHA-256 `7e01432ccca68d71870d828377de7f47dc2e9221c2cf096222ee671742c2f336`.
- [x] 3.2 Tirar o PR #9 de draft após revisão aplicável, observar os quatro checks
  e integrar somente com autorização de merge
- [x] 3.3 Atualizar a branch/local baseline após o merge sem perder trabalho

## 4. Pendências do piloto GLM-5.2

- [ ] 4.1 Confirmar saldo, cota e janela do Token Plan Individual Lite
- [ ] 4.2 Definir tarefa full stack, critérios e limites idênticos para os modelos
- [ ] 4.3 Validar chamada simples, streaming, session ID e métricas
- [ ] 4.4 Validar saída estruturada sem contaminação por `reasoning_content`
- [ ] 4.5 Validar function calling com `tool_stream: true`
- [ ] 4.6 Validar segundo turno com thinking preservado ou limpo explicitamente
- [ ] 4.7 Cobrir parâmetros GLM com testes sem alterar outros provedores
- [ ] 4.8 Executar o cenário aprovado com `qwen3.8-max`
- [ ] 4.9 Verificar saldo e executar o mesmo cenário com `glm-5.2`
- [ ] 4.10 Registrar sessões, chamadas, tokens, thinking, latência e Credits
- [ ] 4.11 Solicitar revisão independente de Tuvok
- [ ] 4.12 Solicitar decisão final de Spock
- [ ] 4.13 Promover `glm-5.2` somente se todos os gates forem aprovados
- [ ] 4.14 Atualizar descrição, inventário e avaliação sem alegações obsoletas
- [ ] 4.15 Executar suíte completa, smoke real e validação estrita de fallback
- [ ] 4.16 Comprovar consumo em Credits e ausência de pay-as-you-go
- [ ] 4.17 Validar rollback para `qwen3.8-max`
- [ ] 4.18 Registrar conclusão ou remover o candidato e manter o baseline

## 5. Pendências da reserva técnica DeepSeek

- [ ] 5.1 Registrar perfis, modelos, endpoints e billing modes sem credenciais
- [ ] 5.2 Confirmar allowlist e termos vigentes do Token Plan Individual
- [ ] 5.3 Confirmar modelos, saldo e endpoint de consulta DeepSeek direta
- [ ] 5.4 Aprovar tetos diário, mensal, por grant e por tarefa
- [ ] 5.5 Definir owners de aprovação, incidentes, reconciliação e revogação
- [ ] 5.6 Separar credenciais e impedir herança/fallback implícito
- [ ] 5.7 Normalizar erros QwenCloud sem depender apenas do status HTTP
- [ ] 5.8 Adicionar `reserve_running`, `reserve_expired` e
  `reserve_outcome_unknown`
- [ ] 5.9 Estender schema para rota, grant, causa, modelo efetivo e custo direto
- [ ] 5.10 Registrar tentativas e resultados idempotentemente
- [ ] 5.11 Adicionar métricas por rota e alertas para ativação da reserva
- [ ] 5.12 Criar painel sem prompts, segredos ou labels de alta cardinalidade
- [ ] 5.13 Documentar consulta, auditoria e retenção das evidências
- [ ] 5.14 Provar que autenticação, payload inválido e erro local não acionam reserva
- [ ] 5.15 Provar uso único e atomicidade do grant sob concorrência
- [ ] 5.16 Provar separação de credenciais, logs e billing modes
- [ ] 5.17 Provar kill switch e rollback para `budget_blocked`
- [ ] 5.18 Executar suíte completa, avaliação de perfis e revisão independente
- [ ] 5.19 Executar shadow e revisar falsos positivos de elegibilidade
- [ ] 5.20 Habilitar um perfil Flash com teto mínimo e aprovação por chamada

## 6. Pendências do piloto OpenObserve

- [ ] 6.1 Inventariar CPU, memória, disco, portas e redes disponíveis
- [ ] 6.2 Definir fontes, atributos permitidos e retenção
- [ ] 6.3 Fixar versão e revisar release notes, licença e vulnerabilidades
- [ ] 6.4 Adicionar OpenObserve single-node com volume e credenciais próprios
- [ ] 6.5 Adicionar OpenTelemetry Collector com healthcheck e limites
- [ ] 6.6 Configurar redaction e fan-out para Phoenix e OpenObserve
- [ ] 6.7 Manter portas em loopback e redes com privilégio mínimo
- [ ] 6.8 Validar traces nos dois backends sem duplicação no produtor
- [ ] 6.9 Ingerir logs e métricas por etapas e medir recursos
- [ ] 6.10 Confirmar ausência de segredos e dados sensíveis
- [ ] 6.11 Criar dashboards e healthcheck no Uptime Kuma
- [ ] 6.12 Testar backup, restauração e rollback
- [ ] 6.13 Comparar OpenObserve e Phoenix durante ao menos uma semana
- [ ] 6.14 Registrar evidências e riscos residuais
- [ ] 6.15 Decidir manter ambos, consolidar ou remover OpenObserve
- [ ] 6.16 Avaliar HA somente em mudança OpenSpec posterior

## 7. Higiene, arquivamento e decisão final

- [x] 7.1 Arquivar `add-canonical-task-intake` após confirmar que specs canônicas
  refletem o runtime
- [x] 7.2 Arquivar `record-pilot-task-metrics`
- [x] 7.3 Arquivar `enforce-deepseek-pilot-budget`
- [x] 7.4 Arquivar `normalize-tirith-warning`
- [x] 7.5 Instalar/habilitar parser SQL do Graphify e reprocessar os sete arquivos
  SQL atualmente sem AST
- [x] 7.6 Revisar os nós isolados do Graphify e classificar falso positivo versus
  relacionamento ausente
- [x] 7.7 Executar suíte completa, `git diff --check`, validação estrita de todas
  as mudanças ativas e `graphify update .`
- [x] 7.8 Publicar relatório de homologação com blockers, pendências não
  bloqueantes, owners, riscos aceitos e rollback
- [x] 7.9 Obter revisão final de Tuvok e decisão final de Spock
- [x] 7.10 Obter autorização do owner para declarar o servidor homologado e
  registrar `GO`, `GO condicional` ou `NO-GO`

# 1. Contrato e baseline

- [x] 1.1 Registrar perfis DeepSeek, modelos, endpoints e billing modes atuais sem credenciais
- [x] 1.2 Confirmar allowlist exata e termos vigentes do Token Plan Individual
- [x] 1.3 Confirmar modelos, saldo e endpoint de consulta da conta DeepSeek direta
- [x] 1.4 Aprovar tetos diário, mensal, por grant e por tarefa da reserva
- [x] 1.5 Definir owners para aprovação, incidentes, reconciliação e revogação

# 2. Modelo de configuração

- [x] 2.1 Criar rotas tipadas `qwencloud_primary` e `deepseek_reserve`
- [x] 2.2 Separar credenciais e impedir herança/fallback implícito entre providers
- [x] 2.3 Adicionar tabela explícita de modelos primário/reserva
- [x] 2.4 Adicionar kill switch global e habilitação por perfil, ambos desligados por padrão
- [x] 2.5 Validar startup fail-closed para configuração incompleta ou ambígua

# 3. Classificação e estados

- [x] 3.1 Normalizar erros QwenCloud sem depender apenas do status HTTP
- [x] 3.2 Implementar allowlist de razões elegíveis à reserva
- [x] 3.3 Adicionar `reserve_required` e `reserve_denied` em modo shadow
- [x] 3.4 Adicionar transição interna `reserve_approved` após consumo exato
- [x] 3.4a Adicionar `reserve_running`, `reserve_expired` e `reserve_outcome_unknown`
- [x] 3.5 Garantir que erros não elegíveis preservem falha explícita sem reserva
- [x] 3.6 Impedir ciclos QwenCloud ↔ DeepSeek e retry automático da reserva

# 4. Gate humano

- [x] 4.1 Definir grant persistido com tarefa, perfil, modelo, teto, chamadas, expiração e aprovador
- [x] 4.2 Consumir o grant atomicamente e uma única vez
- [x] 4.3 Rejeitar grant expirado, reutilizado, alterado ou destinado a outro escopo
- [x] 4.4 Implementar revogação e trilha de auditoria do aprovador
- [x] 4.5 Validar migration e consumo único em PostgreSQL efêmero
- [x] 4.6 Manter modo shadow que nunca chama a DeepSeek direta

# 5. Orçamento da reserva

- [x] 5.1 Implementar consulta de saldo DeepSeek sem expor a API key
- [x] 5.2 Criar guard diário, mensal, por tarefa e por grant separado do Token Plan
- [x] 5.3 Reservar custo máximo antes da chamada e reconciliar custo final
- [x] 5.4 Tratar saldo insuficiente, custo desconhecido e evidência indisponível como fail-closed
- [x] 5.5 Implementar reconciliação manual de `reserve_outcome_unknown`

# 6. Compatibilidade de modelos

- [x] 6.1 Validar `deepseek-v4-flash-0731` no QwenCloud contra `deepseek-v4-flash` direto
- [x] 6.2 Validar `deepseek-v4-pro` em cada endpoint sem presumir snapshot idêntico
- [x] 6.3 Cobrir thinking, ferramentas, JSON, streaming, contexto e limites de output
- [x] 6.4 Registrar diferenças funcionais e bloquear perfis incompatíveis

# 7. Ledger e observabilidade

- [x] 7.1 Estender schema para rota, grant, causa primária, modelo efetivo e custo direto
- [x] 7.2 Registrar tentativas e resultados de forma idempotente
- [x] 7.3 Adicionar métricas por rota e alertas para toda ativação da reserva
- [x] 7.4 Criar painel sem prompts, secrets ou labels de alta cardinalidade
- [x] 7.5 Documentar consulta, auditoria e retenção das evidências

# 8. Testes de segurança e falha

- [x] 8.1 Provar que autenticação, payload inválido e erro local não acionam reserva
- [x] 8.2 Provar que timeout ambíguo não gera retry ou cobrança duplicada
- [x] 8.3 Provar uso único e atomicidade do grant sob concorrência
- [x] 8.4 Provar separação de credenciais, logs e billing modes
- [x] 8.5 Provar kill switch e rollback para `budget_blocked`
- [x] 8.6 Executar suíte completa, avaliação de perfis e revisão independente

# 9. Piloto e promoção

- [x] 9.1 Executar modo shadow e revisar falsos positivos de elegibilidade
- [x] 9.2 Habilitar um perfil Flash com teto mínimo e aprovação por chamada
- [x] 9.3 Comparar custo, qualidade e comportamento das duas rotas
- [x] 9.4 Obter decisão final de Spock antes de expandir
- [x] 9.5 Documentar rollback e realizar go/no-go por perfil

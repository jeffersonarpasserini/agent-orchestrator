# 1. Contrato e baseline

- [ ] 1.1 Registrar perfis DeepSeek, modelos, endpoints e billing modes atuais sem credenciais
- [ ] 1.2 Confirmar allowlist exata e termos vigentes do Token Plan Individual
- [ ] 1.3 Confirmar modelos, saldo e endpoint de consulta da conta DeepSeek direta
- [ ] 1.4 Aprovar tetos diário, mensal, por grant e por tarefa da reserva
- [ ] 1.5 Definir owners para aprovação, incidentes, reconciliação e revogação

# 2. Modelo de configuração

- [x] 2.1 Criar rotas tipadas `qwencloud_primary` e `deepseek_reserve`
- [ ] 2.2 Separar credenciais e impedir herança/fallback implícito entre providers
- [x] 2.3 Adicionar tabela explícita de modelos primário/reserva
- [x] 2.4 Adicionar kill switch global e habilitação por perfil, ambos desligados por padrão
- [x] 2.5 Validar startup fail-closed para configuração incompleta ou ambígua

# 3. Classificação e estados

- [ ] 3.1 Normalizar erros QwenCloud sem depender apenas do status HTTP
- [x] 3.2 Implementar allowlist de razões elegíveis à reserva
- [x] 3.3 Adicionar `reserve_required` e `reserve_denied` em modo shadow
- [x] 3.4 Adicionar transição interna `reserve_approved` após consumo exato
- [ ] 3.4a Adicionar `reserve_running`, `reserve_expired` e `reserve_outcome_unknown`
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

- [ ] 6.1 Validar `deepseek-v4-flash-0731` no QwenCloud contra `deepseek-v4-flash` direto
- [ ] 6.2 Validar `deepseek-v4-pro` em cada endpoint sem presumir snapshot idêntico
- [ ] 6.3 Cobrir thinking, ferramentas, JSON, streaming, contexto e limites de output
- [ ] 6.4 Registrar diferenças funcionais e bloquear perfis incompatíveis

# 7. Ledger e observabilidade

- [ ] 7.1 Estender schema para rota, grant, causa primária, modelo efetivo e custo direto
- [ ] 7.2 Registrar tentativas e resultados de forma idempotente
- [ ] 7.3 Adicionar métricas por rota e alertas para toda ativação da reserva
- [ ] 7.4 Criar painel sem prompts, secrets ou labels de alta cardinalidade
- [ ] 7.5 Documentar consulta, auditoria e retenção das evidências

# 8. Testes de segurança e falha

- [ ] 8.1 Provar que autenticação, payload inválido e erro local não acionam reserva
- [x] 8.2 Provar que timeout ambíguo não gera retry ou cobrança duplicada
- [ ] 8.3 Provar uso único e atomicidade do grant sob concorrência
- [ ] 8.4 Provar separação de credenciais, logs e billing modes
- [ ] 8.5 Provar kill switch e rollback para `budget_blocked`
- [ ] 8.6 Executar suíte completa, avaliação de perfis e revisão independente

# 9. Piloto e promoção

- [ ] 9.1 Executar modo shadow e revisar falsos positivos de elegibilidade
- [ ] 9.2 Habilitar um perfil Flash com teto mínimo e aprovação por chamada
- [ ] 9.3 Comparar custo, qualidade e comportamento das duas rotas
- [ ] 9.4 Obter decisão final de Spock antes de expandir
- [ ] 9.5 Documentar rollback e realizar go/no-go por perfil

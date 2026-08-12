# 1. Preparação

- [ ] 1.1 Registrar baseline efetivo de `la-forge`, sem copiar credenciais
- [ ] 1.2 Confirmar saldo, cota e janela do Token Plan Individual Lite
- [ ] 1.3 Criar backup restrito da configuração e procedimento de rollback
- [ ] 1.4 Definir tarefa full stack, critérios e limites idênticos para os dois modelos

# 2. Compatibilidade do Hermes

- [ ] 2.1 Criar candidato isolado com `glm-5.2`, endpoint Token Plan e sem fallback
- [ ] 2.2 Validar chamada simples, streaming, session ID e métricas
- [ ] 2.3 Validar saída estruturada sem contaminação por `reasoning_content`
- [ ] 2.4 Validar function calling com `tool_stream: true`
- [ ] 2.5 Validar segundo turno com thinking preservado ou limpo explicitamente
- [ ] 2.6 Cobrir parâmetros GLM com testes sem alterar outros provedores

# 3. Avaliação comparativa

- [ ] 3.1 Executar o cenário aprovado com `qwen3.8-max`
- [ ] 3.2 Verificar saldo e executar o mesmo cenário com `glm-5.2`
- [ ] 3.3 Registrar sessões, chamadas, tokens, thinking, latência e Credits
- [ ] 3.4 Solicitar revisão independente de Tuvok
- [ ] 3.5 Solicitar decisão final de Spock

# 4. Promoção ou rejeição

- [ ] 4.1 Promover `glm-5.2` somente se todos os gates forem aprovados
- [ ] 4.2 Atualizar descrição, inventário e avaliação do perfil sem alegações obsoletas
- [ ] 4.3 Executar suíte completa, smoke test real e validação estrita de fallback
- [ ] 4.4 Comprovar consumo em Credits e ausência de cobrança pay-as-you-go
- [ ] 4.5 Validar rollback para `qwen3.8-max`
- [ ] 4.6 Registrar a conclusão; se reprovado, remover o candidato e manter o baseline

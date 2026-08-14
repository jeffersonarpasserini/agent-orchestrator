# 1. Preparação

- [x] 1.1 Registrar baseline efetivo de `la-forge`, sem copiar credenciais
- [x] 1.2 Confirmar saldo, cota e janela do Token Plan Individual Lite
- [x] 1.3 Criar backup restrito da configuração e procedimento de rollback
- [x] 1.4 Definir tarefa full stack, critérios e limites idênticos para os dois modelos

# 2. Compatibilidade do Hermes

- [x] 2.1 Criar candidato isolado com `glm-5.2`, endpoint Token Plan e sem fallback
- [x] 2.2 Validar chamada simples, streaming, session ID e métricas
- [x] 2.3 Validar saída estruturada sem contaminação por `reasoning_content`
- [x] 2.4 Validar function calling com `tool_stream: true`
- [x] 2.5 Validar segundo turno com thinking preservado ou limpo explicitamente
- [x] 2.6 Cobrir parâmetros GLM com testes sem alterar outros provedores

# 3. Avaliação comparativa

- [x] 3.1 Executar o cenário aprovado com `qwen3.8-max` (reprovado por timeout,
  ausência de resposta final e tentativa de escrita)
- [x] 3.2 Verificar saldo e executar o mesmo cenário com `glm-5.2`
- [x] 3.3 Registrar sessões, chamadas, tokens, thinking, latência e Credits
- [x] 3.4 Solicitar revisão independente de Tuvok
- [x] 3.5 Solicitar decisão final de Spock

# 4. Promoção ou rejeição

- [x] 4.1 Promover `glm-5.2` somente se todos os gates forem aprovados
- [x] 4.2 Atualizar descrição, inventário e avaliação do perfil sem alegações obsoletas
- [x] 4.3 Executar suíte completa, smoke test real e validação estrita de fallback
- [x] 4.4 Comprovar consumo em Credits e ausência de cobrança pay-as-you-go
- [x] 4.5 Validar rollback para `qwen3.8-max`
- [x] 4.6 Registrar a conclusão; promoção aprovada e rollback Qwen preservado

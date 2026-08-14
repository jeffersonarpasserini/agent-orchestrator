## 1. Contrato

- [x] 1.1 Registrar limites aprovados e comportamento fail-closed

## 2. Implementação

- [x] 2.1 Implementar leitura e agregação de custos persistidos
- [x] 2.2 Integrar o gate antes da chamada DeepSeek
- [x] 2.3 Configurar US$ 1/dia e US$ 10/piloto
- [x] 2.4 Expor snapshot agregado na API local sem credenciais
- [x] 2.5 Propagar falha financeira como estado `budget_blocked` no workflow

## 3. Verificação

- [x] 3.1 Cobrir liberação, tetos e falhas de evidência
- [x] 3.2 Executar suíte completa e validação estrita
- [x] 3.3 Verificar allowlist da resposta e erro 503 sem detalhes internos
- [x] 3.4 Verificar estado bloqueado sem sessão, uso ou tool calls

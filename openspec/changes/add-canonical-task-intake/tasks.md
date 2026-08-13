## 1. Contrato

- [x] 1.1 Congelar envelope, identidade, idempotência e estados
- [x] 1.2 Definir rollback e limites de segurança

## 2. Implementação

- [ ] 2.1 Obter aprovação específica para migration e credencial
- [x] 2.2 Criar migration `0007_task_intake.sql`
- [x] 2.3 Implementar store transacional e hash canônico
- [x] 2.4 Implementar autenticação e endpoints de entrada/estado
- [x] 2.5 Integrar configuração fail-closed ao ambiente da API

## 3. Verificação

- [x] 3.1 Cobrir validação, autenticação, idempotência e conflito
- [x] 3.2 Cobrir cancelamento, retomada e aprovação não transferível
- [ ] 3.3 Revisão independente de Tuvok
- [ ] 3.4 Aplicar migration e executar smoke somente com aprovação
- [ ] 3.5 Executar CI, observabilidade e rollback testado

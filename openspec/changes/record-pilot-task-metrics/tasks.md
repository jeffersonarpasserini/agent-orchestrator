## 1. Contrato

- [x] 1.1 Definir agregados, identidade idempotente e restrições

## 2. Implementação

- [x] 2.1 Criar migration da tabela de métricas
- [x] 2.2 Implementar upsert por `task_id`
- [x] 2.3 Implementar leitura ordenada do ledger

## 3. Verificação

- [x] 3.1 Testar validação de agregados
- [x] 3.2 Testar contrato de conflito e ausência de credencial no payload
- [x] 3.3 Validar escrita e resumo no PostgreSQL do homelab

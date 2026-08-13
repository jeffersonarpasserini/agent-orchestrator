## Why

O4 exige uma porta de entrada canônica, idempotente e auditável. A API atual
possui apenas endpoints operacionais e não autentica solicitantes nem persiste
o ciclo de vida de tarefas.

## What Changes

- Adicionar autenticação bearer para uma identidade canônica configurada no
  servidor, sem aceitar identidade no payload.
- Validar o envelope obrigatório e persistir tarefa, hash canônico e eventos no
  PostgreSQL.
- Repetir idempotentemente um request equivalente e rejeitar conflito por ID.
- Expor cancelamento e retomada como transições auditáveis.
- Falhar fechado sem autenticação, owner, budget ou critério de aceite.

## Impact

Requer migration `0007`, nova credencial operacional e deploy da API. Nenhuma
dessas ações é autorizada apenas pela aprovação deste documento; cada uma segue
a matriz de autonomia.

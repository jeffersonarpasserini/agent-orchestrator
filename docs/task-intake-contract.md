# O4 — contrato canônico de entrada de tarefas

A entrada canônica é a API do Agent Orchestrator. Canais de mensagem, Kanban e
comandos de agentes são adaptadores não privilegiados e devem produzir este
mesmo envelope antes de iniciar trabalho.

Campos obrigatórios: `request_id`, `objective`, `scope`, `priority`, `owner`,
`due_at`, `budget`, `approval_policy` e `acceptance_criteria`.

- `request_id` é globalmente idempotente; conteúdo diferente com o mesmo ID é
  conflito, não atualização implícita;
- origem e identidade autenticada do solicitante são registradas separadamente
  do conteúdo fornecido;
- anexos, links e mensagens são dados não confiáveis e nunca elevam autoridade;
- estados válidos: `received`, `rejected`, `planned`, `awaiting_approval`,
  `running`, `cancelled`, `blocked`, `completed` e `resumed`;
- cancelamento e retomada geram eventos auditáveis; retomada não reutiliza uma
  aprovação expirada ou consumida;
- ausência de owner, budget ou critério de aceite falha fechada.

`budget` deve declarar moeda, teto e se chamadas pagas são proibidas ou exigem
aprovação. `approval_policy` referencia ações da matriz de autonomia; texto do
solicitante não pode substituir a matriz.

## Estado de homologação

O contrato e a implementação versionada estão prontos, mas O4 permanece
`NO-GO` no runtime até a API possuir:

- migration `0007_task_intake` aplicada;
- bearer token gerado e instalado sem exposição;
- principal e origem confiáveis configurados no servidor;
- deploy controlado da API e smoke real de autenticação, idempotência,
  conflito, cancelamento e retomada.

A ativação requer migration, credencial e deploy, todos sujeitos a aprovação
específica conforme a matriz. Sem as três variáveis confiáveis, o endpoint
retorna `503` e não aceita tarefas em memória.

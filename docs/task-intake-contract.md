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

O contrato e a implementação estão ativos no runtime desde 2026-08-13:

- migration `0007_task_intake` aplicada pelo papel `agent_orchestrator`;
- bearer token aleatório de 256 bits instalado sem exposição, com `.env`
  em modo `0600`;
- principal `jeffersonarpasserini` e origem `api:homelab` definidos pelo
  servidor e observados na trilha persistente;
- credencial inválida retornou `401`; intake desabilitado retornou `503`;
- payload sem owner retornou `422` e nenhuma linha foi persistida;
- criação retornou `201`, replay equivalente retornou a mesma tarefa com
  `idempotent_replay=true` e conflito retornou `409`;
- cancelamento e retomada produziram exatamente os eventos `cancelled` e
  `resumed`; a tarefa terminou em `awaiting_approval`, sem herdar aprovação;
- somente uma tarefa e três eventos foram persistidos, todos com custo zero;
- rollback para a imagem anterior retornou readiness saudável e endpoint O4
  ausente (`404`); a imagem O4 foi restaurada e voltou saudável;
- workflow smoke sem modelo concluiu e API/Phoenix permaneceram `200 OK` nos
  monitores 8 e 10.

Resultado operacional: aprovado. Resultado O4: `PENDING REVIEW`, pois a revisão
independente de Tuvok ainda exige autorização para uma chamada paga. Sem as três
variáveis confiáveis, o endpoint permanece fail-closed com `503` e não aceita
tarefas em memória. O status só muda para `GO` após a revisão ser registrada e
eventuais bloqueios serem resolvidos.

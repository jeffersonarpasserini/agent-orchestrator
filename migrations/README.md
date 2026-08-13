# Migrations

As migrations são executadas exclusivamente pelo usuário `agent_orchestrator`
no banco homônimo. Elas não podem usar credencial administrativa nem acessar
`honcho` ou `db_qualitascare`.

A migration `0001_baseline.sql` cria o schema e o controle de versão. O
framework será fixado na Fase 3. `vector` só será ativada por migration
explícita quando um workflow demonstrar necessidade.

A retenção inicial será de 30 dias para execuções e traces e de pelo menos 180
dias para auditoria de aprovações e migrations. A limpeza será um job explícito
e observável, nunca cascade implícito.

`0003_deepseek_reserve_grants.sql` define grants de reserva de uso único. A
migration está versionada, mas sua presença no repositório não autoriza aplicação
no homelab. Ela deve passar por gate operacional, backup e validação de restore
antes de ser aplicada.

`0004_deepseek_reserve_costs.sql` registra o custo máximo comprometido e a
reconciliação de tokens/custo efetivo por grant. Ela segue o mesmo gate e também
não está autorizada para aplicação no homelab.

`0005_deepseek_reserve_manual_reconciliation.sql` mantém a decisão humana e a
referência de evidência para resultados ambíguos. Ela também permanece apenas
versionada e não autorizada no homelab.

`0006_pilot_cost_breakdown.sql` separa custo equivalente simulado de custo
efetivamente cobrado. O campo legado `cost_usd` permanece como alias do custo
cobrado. A migration foi aplicada no homelab em 2026-08-12 após dump e
restauração validados; a evidência está em `docs/database-operations.md`.

`0007_task_intake.sql` cria as tabelas persistentes de tarefas e eventos para
O4. Ela foi aplicada em 2026-08-13, após autorização específica e dump lógico
protegido. A evidência está em `docs/database-operations.md`.

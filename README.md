# Agent Orchestrator

Orquestração multiagente do homelab com Hermes como gateway de modelos e
mensageria, LangGraph para workflows retomáveis, Honcho para memória de longo
prazo e Phoenix para observabilidade.

## Estado

As Fases 0 a 8 estão concluídas. A Fase 8 fechou com 20/20 tarefas, 90% de
sucesso na primeira tentativa, ledger PostgreSQL e custos simulados/cobrados separados.
O adaptador Hermes-LangGraph possui execução, correlação, uso, tool calls,
timeout, bloqueio de fallback e bloqueio financeiro validados. A reserva técnica
DeepSeek direta passou por um smoke estrito de uma chamada com grant de uso
único, mas permanece fora da promoção geral até concluir seus gates de
segurança e observabilidade. Fases 9 e 10 ainda não estão concluídas.

## Princípios

- GPT-5.6 é acessado pelo Hermes e `openai-codex`, sem `OPENAI_API_KEY`.
- Credenciais e dados operacionais nunca entram no Git.
- Bancos, usuários e permissões são isolados por aplicação.
- Deploy, migrations destrutivas e infraestrutura exigem aprovação humana.
- Custos por assinatura registram valor equivalente simulado e cobrança zero;
  rotas pay-per-token registram os dois valores iguais.
- Hermes e Honcho permanecem operacionais durante a implantação.

## Estrutura

- `docs/`: arquitetura, plano e decisões.
- `src/orchestrator/`: API, adaptadores, agentes, grafos e políticas.
- `migrations/`: migrations do banco exclusivo da orquestração.
- `tests/`: testes unitários, integração e avaliações.

## Plano

Consulte [docs/HERMES_LANGGRAPH_PROJECT.md](docs/HERMES_LANGGRAPH_PROJECT.md).

Baselines e critérios:

- [Baseline não secreto dos perfis](docs/phase-0-profile-baseline.md)
- [Resultados da validação de provedores](docs/phase-1-provider-results.md)
- [Critérios objetivos do piloto](docs/pilot-acceptance-criteria.md)
- [Checklist de tarefa do piloto](docs/pilot-task-checklist.md)
- [Monitor persistente de PR e CI do Spock](docs/spock-github-ci-monitor.md)
- [Handoff para entrada em operação](docs/operations-handoff-2026-08-13.md)
- [Exercício O3 de alerta e recuperação](docs/o3-phoenix-recovery-drill.md)
- [Contrato canônico de entrada de tarefas](docs/task-intake-contract.md)
- [Matriz de autonomia](docs/autonomy-matrix.md)
- [Operação do banco](docs/database-operations.md)
- [Operação da stack](docs/operations.md)
- [Adaptador Hermes CLI](docs/hermes-adapter.md)

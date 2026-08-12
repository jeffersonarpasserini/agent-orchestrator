# Changelog

## 0.1.0-rc1 — 2026-08-12

Primeira release candidata operacional do Agent Orchestrator.

Após o congelamento da candidata, os monitores HTTP da API e do Phoenix foram
vinculados ao canal padrão ativo do Uptime Kuma, concluindo o gate operacional
da Fase 9 sem mover a tag RC1.

### Incluído

- API FastAPI local com readiness PostgreSQL e healthchecks;
- integração Hermes/LangGraph com correlação, usage e tool calls;
- budget DeepSeek fail-closed e estado `budget_blocked`;
- ledger PostgreSQL da amostra de 20 tarefas;
- custos equivalentes simulados e custos efetivamente cobrados separados;
- Phoenix 19.4.0 para traces;
- reserva técnica DeepSeek com grant de uso único, ainda não promovida;
- migrations `0001` a `0006` e restauração validada.

### Evidência

- Fase 8: GO, 20/20 tarefas e 90% na primeira tentativa;
- regressão: 117/117 testes;
- imagem API: `agent-orchestrator:0.1.0`, digest local
  `sha256:f0044b980b8d9478df45dceb41d0904fd2297a68e6cb2fc3ccbc15f27d13ae74`;
- Phoenix: `arizephoenix/phoenix:version-19.4.0-nonroot`, digest
  `sha256:21b75beb03f283e5e0c7e0a3b0ab54d4ace1ce4d31ff76112fd7319d15795444`.

### Restrições

- release ainda sem commit/tag porque o repositório não possui `HEAD`;
- reserva direta limitada ao smoke estrito;
- OpenObserve pertence à Fase 10 e não integra esta candidata.

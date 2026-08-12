# Adaptador Hermes CLI

## Interface

O adaptador usa a CLI não interativa por perfil:

```text
hermes -p <profile> chat -q <task> -Q --source tool --max-turns <n> --pass-session-id
```

O modo `hermes -z/--oneshot` não é usado porque ativa automaticamente `HERMES_YOLO_MODE=1` e respeita a cadeia de fallback do perfil.

## Controles

`HermesCliAdapter.run_agent(profile, task, context, limits)`:

- valida o nome do perfil contra uma gramática restrita;
- remove `OPENAI_API_KEY` e `HERMES_YOLO_MODE` do subprocesso;
- executa `fallback list` antes de cada chamada e rejeita qualquer cadeia ativa ou não verificável;
- adiciona um marcador único `[ao:<correlation_id>]` ao prompt;
- resolve a sessão correspondente em `sessions list --source tool` pelo marcador, sem depender da ordem das execuções;
- limita turnos e tempo;
- encerra todo o grupo de processos em timeout ou cancelamento;
- normaliza resposta e erros de processo.

## Evidências

- sete testes isolados do adaptador cobrem sucesso, correlação, fallback, erro, timeout, cancelamento e injeção;
- teste real com Spock retornou `CORRELATION_OK` e resolveu a sessão Hermes `20260810_155017_e630c7`;
- o container da API não contém `OPENAI_API_KEY`.

## Próximo incremento

A captura estruturada de tool calls e uso ainda não é exposta por `chat -Q`. Ela será lida dos registros da sessão Hermes ou pelo backend JSON-RPC autenticado. O executável e `~/.hermes` permanecem exclusivamente no host; a API não deve receber credenciais por bind mount.

## Aceite da Fase 4

O teste real final executou um nó LangGraph com o perfil Spock e retornou `LANGGRAPH_SP0CK_OK`. A execução foi correlacionada à sessão `20260810_160619_dfe7ef` e normalizou provedor, modelo, chamadas de API, tokens, custo e tool calls diretamente do banco SQLite do perfil em modo somente leitura.

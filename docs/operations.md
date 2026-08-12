# Operação da stack

## Subir e verificar

```bash
docker compose up -d --build
docker compose ps
curl --fail http://127.0.0.1:8088/health/ready
curl --fail -X POST http://127.0.0.1:8088/workflows/smoke \
  -H 'content-type: application/json' \
  -d '{"message":"phase-3"}'
```

A API fica somente em `127.0.0.1:8088`. Phoenix fica em
`127.0.0.1:6006` (UI e OTLP HTTP) e `127.0.0.1:4317` (OTLP gRPC).
Não há `OPENAI_API_KEY` na stack.

## Healthchecks

- `/health/live`: processo HTTP ativo;
- `/health/ready`: conexão real com o banco como `agent_orchestrator`;
- Phoenix: resposta HTTP na porta 6006;
- workflow fictício: `POST /workflows/smoke`, sem chamada de modelo.

## Troubleshooting

- Banco indisponível: confirmar a rede externa `homelab-data`, o alias
  `shared-postgres` e a saúde de `honcho-database-1`.
- Phoenix indisponível: verificar migrations e permissões no schema `phoenix`
  com `docker compose logs phoenix`.
- Trace ausente: verificar `OTEL_EXPORTER_OTLP_ENDPOINT` e executar novamente o
  workflow fictício; o exportador usa OTLP HTTP em `/v1/traces`.
- Rollback: `docker compose down`. Isso não interrompe Hermes, Honcho nem o
  PostgreSQL compartilhado e não remove dados do banco.
- Segredos: manter `.env` fora do Git e nunca registrar a saída expandida do
  Compose.

## Recuperação do circuit breaker DeepSeek

O circuit breaker financeiro não mantém uma flag de reset. Antes de cada
chamada DeepSeek, ele recalcula os gastos a partir dos `state.db` em modo
somente leitura. O workflow retorna `budget_blocked` quando o teto foi atingido
ou quando a evidência financeira não pode ser validada.

1. Identificar na mensagem se o bloqueio é diário, total do piloto ou de
   evidência. Não editar custos no SQLite para liberar chamadas.
2. Para o teto diário, aguardar o próximo dia no timezone de
   `DEEPSEEK_PILOT_STARTED_AT`; o recálculo libera automaticamente a chamada se
   o novo total estiver abaixo do teto.
3. Para o teto total, manter o bloqueio até uma decisão humana atualizar o teto
   ou iniciar outro piloto. Registrar a decisão antes de mudar o `.env`.
4. Para falha de evidência, restaurar a disponibilidade e o schema compatível
   de todos os `state.db` dos perfis DeepSeek; não contornar o fail-closed.
5. Verificar localmente o snapshot, sem imprimir variáveis de ambiente ou
   credenciais:

```bash
set -a
. ./.env
set +a
.venv/bin/python -c 'from orchestrator.budget import DeepSeekBudgetGuard; from orchestrator.settings import Settings; s=Settings.from_env(); print(DeepSeekBudgetGuard(s.hermes_profiles_root, daily_limit_usd=s.deepseek_daily_budget_usd, pilot_limit_usd=s.deepseek_pilot_budget_usd, pilot_started_at=s.deepseek_pilot_started_at).snapshot())'
```

Uma nova chamada só deve ser tentada depois de o snapshot passar e a causa da
recuperação estar registrada no ledger do piloto.

## Reserva técnica DeepSeek direta

A fundação de configuração existe, mas a reserva **não está habilitada**. O
modo padrão é `off` com kill switch ativo. O comportamento operacional vigente
continua sendo `budget_blocked`; não adicionar fallback ao perfil Hermes nem
copiar a chave DeepSeek para a configuração QwenCloud.

A fundação implementada usa QwenCloud como primário e exige o estado
`reserve_required`, grant humano de uso único, consulta de saldo, tetos diretos
independentes, uma tentativa e ledger por rota. Ela permanece fora do bootstrap
e sem segredo. Para reconciliar resultado ambíguo, usar somente a CLI e as
evidências descritas no runbook; nunca editar as tabelas diretamente. Consultar
`docs/deepseek-technical-reserve.md` e o OpenSpec
`add-deepseek-technical-reserve` antes de qualquer mudança. O smoke test em
`docs/deepseek-reserve-smoke-runbook.md` permanece não autorizado.

## Homepage e Uptime Kuma

A publicação da UI Phoenix fora do loopback exige autenticação e decisão de
hostname. Até essa decisão, não adicionar link que aponte para localhost do
navegador do usuário. O container usa a variante `nonroot`, UID `65532`, rootfs
read-only, capabilities removidas, `no-new-privileges` e apenas as variáveis de
ambiente selecionadas no Compose. Phoenix é o plano de diagnóstico; alertas HTTP
de disponibilidade pertencem ao Uptime Kuma. O Uptime Kuma já alcança
`http://api:8088/health/ready` pela rede Docker. O monitor
`Agent Orchestrator API` foi criado com intervalo de 60 segundos e validado com
HTTP 200. Criar ou alterar monitores pela interface autenticada, sem publicar a
porta internamente para a LAN.

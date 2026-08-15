# Piloto OpenObserve no homelab

## Baseline e limites

Inventário de 2026-08-15 (BRT): 16 CPUs, 62 GiB RAM (42 GiB disponíveis),
8 GiB swap e 59 GiB livres no filesystem Docker, já em 86% de uso. O piloto
limita OpenObserve a 1 CPU/1 GiB, Collector a 0,5 CPU/256 MiB e retenção global
a 7 dias. As portas 5080, 4318 e 13133 são publicadas apenas em loopback.

Versões fixadas: OpenObserve `v0.92.1` e OpenTelemetry Collector Contrib
`0.158.0`, ambas também presas por digest no Compose. OpenObserve usa AGPL-3.0;
o homelab executa a imagem não modificada.
A vulnerabilidade GHSA-m8gj-6r85-3r6m afeta versões anteriores a 0.14.1 e não
atinge a versão fixada. Revisar release notes e advisories antes de upgrades.

## Escopo de ingestão

A fase inicial aceita somente traces OTLP da API. O produtor envia uma vez ao
Collector; este aplica allowlist e fan-out para Phoenix e OpenObserve. Logs e
métricas de aplicações ficam desabilitados até uma mudança explícita após a
validação dos traces. Métricas internas do Collector ficam disponíveis apenas
na rede Docker.

Campos de resource permitidos: `service.name`, `service.version`,
`deployment.environment.name` e metadados `telemetry.sdk.*`. Campos de span
permitidos: perfil do agente, tipo de erro e dimensões HTTP/RPC de baixa
cardinalidade. Eventos preservam somente tipo da exceção e indicador `escaped`.
Prompts, respostas, tokens, cookies, authorization, API keys, DSNs, URLs
completas, dados pessoais e clínicos são removidos por `keep_keys`. A política
usa `error_mode: propagate`: se não puder ser aplicada, o batch não é exportado.

## Segredos e inicialização

Defina em `.env` uma conta exclusiva:

```text
OPENOBSERVE_ROOT_EMAIL=<email operacional exclusivo>
OPENOBSERVE_ROOT_PASSWORD=<segredo aleatório longo>
```

Nunca registre esses valores em Git. Valide e inicie:

```bash
docker compose config --quiet
docker compose up -d openobserve otel-collector
docker compose up -d --build api
```

A UI fica em `http://127.0.0.1:5080`. O Collector recebe a API internamente em
`http://otel-collector:4318/v1/traces`; não existe segundo exportador no
produtor.

## Dashboards e monitoração

Criar no OpenObserve um dashboard `agent-orchestrator-pilot` com: spans/minuto,
erros por `error.type`, p95 de duração e contagem por `agent.profile`. Nenhum
painel deve usar prompt, resposta, task ID, session ID ou outro label de alta
cardinalidade.

No Uptime Kuma, criar monitor HTTP `OpenObserve homelab` para
`http://openobserve:5080/healthz`, intervalo 60 s, retries 3, conectado à rede
`agent-orchestrator_observability-edge`. O monitor não contém credenciais e verifica
somente `status=ok`.

Aplicado em 2026-08-15: dashboard `agent-orchestrator-pilot` (ID
`7494459516637937664`) com quatro painéis versionados em
`observability/openobserve-dashboard.json`. O painel de spans/minuto foi
executado com sucesso na API de busca. O monitor Uptime Kuma ID 11 está ativo
com intervalo de 60 s, três tentativas e resposta HTTP 200 confirmada a partir
do próprio contêiner.

## Backup, restore e rollback

O backup para OpenObserve e Collector, preserva o volume e reinicia ambos:

```bash
scripts/openobserve-backup.sh
scripts/openobserve-restore-verify.sh backups/openobserve/<arquivo>.tar.gz
```

Rollback sem apagar dados:

```bash
docker compose stop otel-collector openobserve
```

Depois, restaure temporariamente
`OTEL_EXPORTER_OTLP_ENDPOINT=http://phoenix:6006/v1/traces` na API e recrie
somente `api`. O volume `openobserve-data` deve permanecer intacto até decisão
humana.

## Evidência de recursos e recuperação

Em 2026-08-15, após traces, um log sintético e uma métrica gauge sintética,
o snapshot de recursos registrou OpenObserve em `237.9 MiB / 1 GiB`, Collector
em `31.61 MiB / 256 MiB` e Phoenix em `383.2 MiB / 2 GiB`; todos estavam abaixo
de 0,2% de CPU no instante medido. O log teve seu corpo substituído por
`[redacted]`; atributos de recurso e datapoint passaram pelas allowlists.

O backup consistente `openobserve-20260815T181951Z.tar.gz` passou na verificação
SHA-256 e foi restaurado com sucesso em volume temporário, depois removido. O
trap de recuperação também reiniciou OpenObserve e Collector corretamente após
uma falha intermediária simulada por permissão de arquivo.

## Comparação de sete dias

Registrar diariamente: spans aceitos/exportados/falhos, disponibilidade,
CPU/RAM, crescimento do volume, latência de consulta, cobertura, qualidade da
UI e trabalho operacional. Phoenix permanece fonte de verdade durante todo o
período. A decisão manter ambos/consolidar/remover só pode ser tomada após sete
dias completos; HA continua fora de escopo e exige nova OpenSpec.

O período começou em 2026-08-15. O Dia 1 está registrado em
`docs/openobserve-phoenix-comparison.csv`; a primeira decisão elegível será em
2026-08-22, após completar sete dias de evidências.

## Evidências e riscos residuais

Evidências locais: Compose renderizado com o `.env` operacional; autenticação
confirmada sem imprimir credenciais; configuração do Collector validada pelo
binário oficial 0.158.0; imagens baixadas e digests confirmados; testes estáticos
cobrem pinning, loopback, limites, volume, produtor único, redaction, fan-out e
independência da API. Em 2026-08-15, o trace sintético
`pilot-protobuf-redaction-check` foi enviado uma única vez ao Collector e
localizado nos dois destinos: no OpenObserve com `agent_profile=spock` e no
Phoenix com `agent.profile=spock`. Os atributos sintéticos `api_key` e
`authorization`, ambos contendo `REDACTION_SENTINEL_PROTO_20260815`, não
apareceram em nenhum destino.

Riscos residuais: disco do host já em 86%; healthcheck interno do OpenObserve
confirma processo/versão, enquanto a disponibilidade HTTP deve ser monitorada
externamente pelo Uptime Kuma; indisponibilidade prolongada pode descartar
telemetria após a fila limitada do Collector; sete dias de comparação ainda
precisam transcorrer; logs e métricas de aplicações ainda não estão autorizados;
credenciais iniciais de root devem ser substituídas por token de ingestão com
privilégio mínimo assim que a UI estiver operacional.

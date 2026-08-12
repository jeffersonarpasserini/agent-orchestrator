# Context

O orquestrador já emite OTLP diretamente para Phoenix. OpenObserve deve entrar
como backend operacional adicional sem acoplar os produtores a dois destinos e
sem ingerir segredos ou conteúdo sensível.

# Decision

Um OpenTelemetry Collector recebe a telemetria, aplica allowlist/redaction e
exporta traces para Phoenix e OpenObserve. OpenObserve começa single-node, com
SQLite e volume local próprios, versão fixada, porta em loopback, retenção curta
e recursos limitados.

Logs e métricas entram por etapas. O piloto não usa PostgreSQL compartilhado,
NATS, Kubernetes ou object storage. Esses componentes exigem nova decisão caso
volume ou disponibilidade comprovem a necessidade.

# Safety

- Phoenix permanece operacional e independente durante o piloto.
- Chaves, DSNs, prompts, dados pessoais e clínicos são removidos antes da saída
  do Collector.
- A UI não é publicada na LAN sem autenticação e decisão de hostname.
- A imagem é fixada por versão, sem tag `latest`.
- Backup, restauração e rollback são testados antes da homologação.
- Falha do OpenObserve não bloqueia o workflow do agente.

# Rollback

Remover o exportador OpenObserve da configuração do Collector, validar o fluxo
para Phoenix e parar apenas Collector/OpenObserve. O volume é preservado até a
decisão humana sobre retenção ou remoção.

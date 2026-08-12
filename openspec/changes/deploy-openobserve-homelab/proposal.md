# Why

Phoenix cobre traces e avaliações dos agentes, mas o homelab ainda não possui
uma plataforma única para logs, métricas, traces, dashboards, alertas e
incidentes. OpenObserve pode preencher essa lacuna usando OpenTelemetry e
armazenamento local eficiente, sem exigir uma stack distribuída no piloto.

# What Changes

- Adicionar OpenObserve ao escopo futuro do homelab em modo single-node.
- Adicionar OpenTelemetry Collector para redaction e fan-out a Phoenix e
  OpenObserve.
- Validar ingestão gradual, retenção, limites, backup, restauração e rollback.
- Comparar OpenObserve com Phoenix antes de qualquer consolidação.

# Impact

A mudança futura adicionará containers, volume persistente, credenciais e carga
de CPU, memória e disco. Esta proposta não autoriza deploy imediato, HA,
Kubernetes, NATS, exposição à LAN ou remoção do Phoenix.

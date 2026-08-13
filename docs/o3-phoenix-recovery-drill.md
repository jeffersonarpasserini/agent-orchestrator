# O3 — exercício de alerta e recuperação do Phoenix

Janela: 2026-08-18, 20:00–22:00 America/Sao_Paulo. Owner: Jefferson
Passerini. Executor: O'Brien sob decisão de Spock. Revisor: Tuvok.

## Escopo congelado

- interromper somente `agent-orchestrator-phoenix-1`;
- preservar API, PostgreSQL, Hermes e Uptime Kuma;
- monitor Phoenix: ID `10`, HTTP, intervalo `60 s`;
- notificação: ID `1`, `Phoenix Notification`, ativa e padrão;
- monitor da API: ID `8`, que deve permanecer `UP`.

## Gate antes da execução

1. confirmar data/hora dentro da janela e presença do owner;
2. confirmar `docker compose ps` com API e Phoenix saudáveis;
3. confirmar monitores 8 e 10 ativos e associados à notificação 1;
4. anunciar início, rollback e duração máxima de dez minutos;
5. capturar timestamp inicial sem exportar configuração do canal.

## Exercício

1. parar somente o serviço Phoenix com `docker compose stop phoenix`;
2. aguardar o monitor 10 mudar para `DOWN`, no máximo dois intervalos;
3. o owner confirma a entrega efetiva da notificação e registra o timestamp;
4. restaurar com `docker compose up -d phoenix`;
5. aguardar healthcheck saudável e monitor 10 em `UP`;
6. o owner confirma a mensagem de recovery;
7. executar o workflow smoke sem modelo e confirmar novo trace no Phoenix;
8. confirmar que monitor 8 e PostgreSQL permaneceram saudáveis.

Falha de entrega, restauração acima de dez minutos, API `DOWN`, erro de banco
ou segredo em log resulta em `NO-GO`, restauração imediata e incidente.

## Evidência a preencher

| Evento | Timestamp BRT | Evidência |
|---|---|---|
| anúncio | pendente | owner/destino confirmado sem expor identificador |
| Phoenix parado | pendente | container e monitor 10 |
| alerta entregue | pendente | confirmação humana |
| Phoenix saudável | pendente | healthcheck e HTTP 200 |
| recovery entregue | pendente | confirmação humana |
| trace smoke | pendente | request/session ID sem segredo |

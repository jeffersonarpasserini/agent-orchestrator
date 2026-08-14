# O3 — exercício de alerta e recuperação do Phoenix

Janela executada: 2026-08-13, 21:10–21:20 America/Sao_Paulo. Owner: Jefferson
Passerini. Executor: O'Brien sob decisão de Spock. Revisor: Tuvok.

Resultado operacional e da revisão: `GO`. Tuvok aprovou a O3 na sessão
`20260813_212649_160efe`, sem bloqueadores. O owner confirmou o recebimento
efetivo das notificações de queda e recuperação. O Phoenix foi restaurado
dentro do limite de dez minutos; API, PostgreSQL e Uptime Kuma permaneceram
saudáveis.

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
| anúncio | 2026-08-13 21:02 BRT | owner presente; escopo, rollback e limite de dez minutos anunciados |
| Phoenix parado | 2026-08-13 21:10:05 BRT | somente `agent-orchestrator-phoenix-1` parado; API permaneceu `200` |
| alerta entregue | 2026-08-13 21:12:27 BRT | Kuma marcou monitor 10 `DOWN`; owner confirmou recebimento da notificação |
| Phoenix saudável | 2026-08-13 21:16:05 BRT | container saudável e Phoenix/API `200`; PostgreSQL saudável |
| recovery entregue | 2026-08-13 21:16:27 BRT | Kuma marcou monitor 10 `UP`; owner confirmou recebimento da recuperação |
| trace smoke | 2026-08-13 21:17:09 BRT | `POST /workflows/smoke` retornou `200`; trace `3a169aa97765f8305edee5ff5d5a1f0c` persistido no Phoenix |

O monitor 10 registrou a transição autoritativa `DOWN` com
`getaddrinfo ENOTFOUND phoenix` e depois `UP` com `200 - OK` e latência de 3 ms.
O monitor 8 permaneceu `UP` durante todo o exercício. A indisponibilidade
deliberada durou aproximadamente 5 minutos e 48 segundos.

O owner reagendou explicitamente a janela de 2026-08-18 para 2026-08-13 às
21:10 BRT. O anúncio às 21:02 foi o gate pré-execução e não uma interrupção
antecipada. A detecção definitiva levou aproximadamente 142 segundos, 22
segundos além dos dois intervalos nominais: o Kuma registrou dois estados
intermediários `pending` antes do `DOWN` definitivo. O desvio não ultrapassou o
limite de rollback de dez minutos e fica registrado como risco residual baixo.

## Evidência auditável

Consultas somente leitura ao `kuma.db` preservaram as linhas importantes:

```text
monitor 10 | status 0 | important 1 | 2026-08-14 00:12:27.905 UTC | getaddrinfo ENOTFOUND phoenix
monitor 10 | status 1 | important 1 | 2026-08-14 00:16:27.928 UTC | 200 - OK | 3 ms
```

O monitor 8 apresentou `200 - OK` a cada minuto durante a janela. Ao final,
`docker compose ps` marcou API e Phoenix como `healthy`; `docker ps` marcou
`honcho-database-1` e `uptime-kuma` como `healthy`. Consulta somente leitura a
`phoenix.traces` retornou:

```text
3a169aa97765f8305edee5ff5d5a1f0c | 2026-08-14 00:17:09.465695 UTC | 2026-08-14 00:17:09.470186 UTC
```

Nenhum artefato contém configuração do canal, credencial ou conteúdo do trace.
O custo estimado da revisão Tuvok foi `US$ 0,013061774`; o provedor não informou
custo real.

# Avaliação shadow da reserva — 2026-08-15

## Escopo

A avaliação foi executada localmente com provider falso e sem rede, credencial,
grant ou chamada paga. Ela percorreu todas as razões normalizadas e confirmou o
estado terminal do grafo, a ausência de consumo de grant e a ausência de
invocação DeepSeek.

## Resultado da elegibilidade

| Classe | Razões | Resultado esperado e observado |
|---|---|---|
| cota comprovadamente esgotada | `subscription_window_exhausted`, `subscription_credits_exhausted` | `reserve_required` |
| capacidade | `subscription_capacity_unavailable` | bloqueada por padrão; elegível apenas com política explícita |
| identidade/política | `authentication_failed`, `authorization_failed`, `account_suspended`, `policy_violation` | bloqueada |
| contrato/modelo | `model_unavailable`, `invalid_request` | bloqueada |
| execução local | `tool_error`, `local_error`, `low_quality_response` | bloqueada |
| evidência ambígua | `ambiguous_timeout`, `financial_evidence_unavailable`, HTTP 429 sem prova estruturada | bloqueada |

Foram observados zero falsos positivos no conjunto determinístico: nenhuma das
12 razões não elegíveis criou uma solicitação de reserva. As duas razões
elegíveis produziram somente metadados públicos de roteamento. Aprovação em
shadow continuou recusada e não consumiu grant. O kill switch impediu até a
criação da solicitação.

## Avaliação dos perfis

- `tuvok`/`deepseek-v4-pro`: compatível com a allowlist vigente do Token Plan
  Individual e apto apenas para uma futura observação operacional shadow;
- `barclay`, `rutherford` e `obrien`/`deepseek-v4-flash-0731`: incompatíveis com
  a allowlist vigente para uma observação operacional da rota primária; isso
  não altera a allowlist independente da API DeepSeek direta, que admite
  `deepseek-v4-flash`;
- nenhum perfil foi alterado e nenhuma reserva real foi habilitada.

## Evidência executada

Em 2026-08-15, `python -m unittest discover -s tests -v` concluiu 154 testes em
1,485 s: 154 aprovados e um teste de integração PostgreSQL ignorado por exigir
URL explícita. Esse teste de concorrência já havia sido executado separadamente
contra PostgreSQL 17.6 efêmero, com exatamente um consumidor vencedor entre
dois. As migrations `0001`, `0003`, `0004`, `0005` e `0008` foram reaplicadas
do zero antes do teste; o contêiner isolado foi removido depois.

Em 2026-08-15, após GO condicional da revisão independente, uma janela shadow
interativa foi executada com `tuvok`/`deepseek-v4-pro`, modo `shadow`, kill
switch desligado e somente esse perfil habilitado. A sessão
`20260815_130622_636364` terminou `completed` com `SHADOW_OK`, não criou
`reserve_request`, não apresentou nem consumiu grant e não chamou a API
DeepSeek direta. Combinada aos vetores determinísticos de falha acima, a janela
conclui o item 9.1 sem falsos positivos observados.

O Token Plan Individual proíbe automação de API e batch; por isso a observação
foi realizada como interação do perfil Tuvok na ferramenta permitida. O piloto
Flash direto do item 9.2 é um gate separado e usa exclusivamente
`deepseek-v4-flash` na API DeepSeek direta.

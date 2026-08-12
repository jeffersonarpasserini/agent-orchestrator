# Runbook — smoke test da reserva DeepSeek direta

Status: **smoke estrito concluído em 2026-08-12**. Este documento continua sendo
o procedimento obrigatório para qualquer nova execução; o resultado anterior
não autoriza outra chamada paga.

O gate inicialmente terminou em **NO-GO**, os bloqueios foram resolvidos e uma
única chamada foi concluída. A auditoria pós-smoke confirmou grant consumido,
custo reconciliado e ausência de grants aprovados pendentes. Ver
`docs/deepseek-reserve-smoke-gate-2026-08-12.md`.

## Objetivo e escopo

Validar uma única chamada interativa Flash pela rota `deepseek_reserve`, após
falha primária simulada e aprovação humana. O teste não autoriza Pro, batch,
automação recorrente, retry, expansão para outros perfis ou fallback Hermes.

## Pré-condições obrigatórias

1. OpenSpec revisado e owners de aprovação, incidente e reconciliação definidos.
2. Tetos diário, mensal e do grant aprovados por escrito.
3. Backup e restore do banco validados antes das migrations `0003`–`0005`.
4. Migration aplicada por usuário `agent_orchestrator`, nunca administrador.
5. Chave direta armazenada no secret store aprovado, separada do QwenCloud.
6. Saldo USD comprovado por `/user/balance`, sem registrar headers ou payload.
7. Perfil Flash e modelo `deepseek-v4-flash` aprovados no gate de compatibilidade.
8. Kill switch testado e modo shadow revisado antes de `enforced`.

Qualquer item ausente resulta em **no-go**.

## Limites do primeiro teste

- um perfil e uma tarefa descartável sem dados sensíveis;
- um grant, uma chamada, uma tentativa;
- `stream=false`;
- input e output máximos explícitos e estimativa abaixo do grant;
- teto sugerido de US$ 0,01 para a chamada, sujeito a aprovação;
- nenhum tool call, arquivo, web search ou ação externa.

## Sequência operacional

1. Registrar `task_id`, owner, janela, modelo, limites e rollback.
2. Obter snapshot de saldo e dos tetos locais; não imprimir a chave.
3. Simular a razão primária elegível e confirmar `reserve_required`.
4. Criar grant humano com expiração curta e escopo exato.
5. Confirmar que a estimativa usa o snapshot de preço aprovado.
6. Habilitar somente o perfil de teste e desligar o kill switch pelo tempo da
   janela autorizada.
7. Executar uma vez e capturar grant, rota, modelo, tokens, custo e estado.
8. Reativar imediatamente o kill switch.
9. Conferir saldo, ledger e ausência de segunda tentativa.
10. Revogar grants restantes e registrar go/no-go.

## Resultado ambíguo

Não repetir a chamada. Manter `reserve_outcome_unknown` até consultar console,
saldo e evidência do provider. Depois executar exatamente uma reconciliação:

```bash
.venv/bin/python -m orchestrator.reserve_reconcile \
  --grant-id GRANT_ID \
  --resolved-by OPERADOR \
  --evidence-reference REFERENCIA_NAO_SENSIVEL \
  --resolution confirmed_charged \
  --cache-hit-tokens N \
  --cache-miss-tokens N \
  --completion-tokens N
```

Se houver prova de que não ocorreu cobrança, usar
`--resolution confirmed_not_charged` sem parâmetros de tokens. A CLI aceita
somente registros `outcome_unknown` e não permite segunda reconciliação.

## Rollback e critérios de parada

Ativar o kill switch diante de erro de schema, autenticação, saldo, custo,
modelo inesperado, timeout, divergência de ledger ou chamada adicional. O
rollback não apaga grants/custos: preserva evidências para auditoria.

O smoke test passa somente com uma chamada, custo reconciliado, modelo correto,
nenhum segredo em logs e retorno da rota normal a `budget_blocked` após o teste.

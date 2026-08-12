# Checklist de tarefa do piloto

Use uma cópia deste checklist para cada item da amostra congelada da Fase 8.

## Antes da execução

- [ ] Confirmar ID, classe, descrição, risco e critério de aceite no plano.
- [ ] Confirmar que a ação está dentro do escopo e é reversível.
- [ ] Verificar o snapshot DeepSeek e os tetos diário e total.
- [ ] Confirmar ausência de `OPENAI_API_KEY` e de fallback não declarado.
- [ ] Definir perfis/modelos, timeout e no máximo dois ciclos automáticos.
- [ ] Registrar aprovação humana antes de commit, push, deploy, migration,
      escrita operacional ou ação destrutiva.
- [ ] Preservar estado inicial suficiente para rollback e comparação.

## Durante a execução

- [ ] Manter o trabalho limitado à tarefa e preservar alterações preexistentes.
- [ ] Registrar início, fim, tentativas, ciclos, chamadas e perfis/modelos.
- [ ] Não incluir credenciais, conteúdo de `.env` ou segredos nas evidências.
- [ ] Interromper em `budget_blocked`; não alterar custos para liberar chamadas.
- [ ] Parar e pedir nova decisão se o risco ou o escopo aumentar.

## Verificação

- [ ] Executar o teste focal ou a verificação operacional definida no aceite.
- [ ] Executar a regressão proporcional ao risco.
- [ ] Verificar diff e confirmar que não há mudanças alheias à tarefa.
- [ ] Executar `graphify update .` depois de mudanças de código.
- [ ] Registrar limitações e riscos residuais sem declarar além da evidência.
- [ ] Acionar revisão independente quando exigida pelo risco.

## Fechamento

- [ ] Registrar no ledger: resultado, perfis/modelos, tentativas, chamadas,
      latência, custo simulado, custo cobrado e IDs de evidência.
- [ ] Em assinatura, confirmar custo cobrado zero; em pay-per-token, confirmar
      custo simulado igual ao cobrado.
- [ ] Identificar snapshot e fonte de preço; marcar proxies explicitamente.
- [ ] Atualizar o estado do item somente após aprovação aplicável.
- [ ] Confirmar rollback executado ou justificar por que não se aplica.
- [ ] Recalcular gasto acumulado e saldo dos tetos.
- [ ] Confirmar que nenhuma ação externa não aprovada foi realizada.

## Resultado mínimo

```text
ID:
Resultado:
Perfis/modelos:
Tentativas/ciclos:
Chamadas:
Latência:
Custo simulado:
Custo cobrado:
Economia da assinatura:
Snapshot/fonte de preço:
Evidências:
Testes/verificações:
Rollback:
Riscos residuais:
Aprovação:
```

# Ledger e métricas da reserva DeepSeek

## Escopo

O ledger registra tentativas da rota direta `deepseek_reserve` sem armazenar
prompt, resposta, API key, header de autenticação ou DSN. A migration
`0008_deepseek_reserve_attempts` é apenas versionada; aplicá-la no homelab
continua exigindo backup, aprovação específica e verificação de rollback.

Cada tentativa referencia um grant de uso único e registra `attempt_id`,
`task_id`, causa normalizada da falha primária, modelo solicitado e efetivo,
aprovador, IDs de sessão primário e direto quando disponíveis, latência,
estado, tokens, custo direto e timestamps. Grant, compromisso financeiro e
estado inicial `reserve_running` são persistidos na mesma transação. O ID
direto vem do campo `id` da resposta Chat Completions; ausência legítima fica
como `NULL`, nunca é substituída por valor inventado.

## Consulta operacional segura

A API vinculada ao loopback expõe `GET /reserve/metrics`. A resposta contém
somente rota, contagens por estado e modelo, tokens agregados, custo agregado e
o booleano `alert_required`. Qualquer ativação torna esse sinal verdadeiro.

Falha de schema, conexão ou leitura retorna HTTP 503 com a mensagem genérica
`reserve metrics unavailable`. Detalhes de conexão não entram na resposta.

Consulta SQL agregada equivalente:

```sql
SELECT status,
       COALESCE(effective_model, requested_model) AS model,
       count(*) AS attempts,
       COALESCE(sum(direct_cost_usd), 0) AS direct_cost_usd
  FROM orchestrator.deepseek_reserve_attempts
 GROUP BY status, COALESCE(effective_model, requested_model)
 ORDER BY status, model;
```

Investigações por tarefa ou grant devem ocorrer somente no PostgreSQL, por um
operador autorizado, e nunca ser transformadas em labels de métricas. IDs de
tarefa, grant e tentativa têm cardinalidade alta e podem correlacionar dados
operacionais.

## Auditoria

Para cada ativação, confirmar em conjunto:

1. grant aprovado, escopo e expiração;
2. causa primária normalizada e elegível;
3. tentativa `reserve_running` criada na mesma transação do consumo;
4. compromisso financeiro correspondente em `deepseek_reserve_costs`;
5. aprovador derivado do grant, sessões e latência da tentativa;
6. estado terminal e, quando concluída, custo e tokens reconciliados;
7. reconciliação manual quando o estado for `reserve_outcome_unknown`;
8. ausência de uma segunda tentativa para o mesmo grant.

Uma diferença entre grant, custo e tentativa é falha de evidência financeira e
deve ativar o kill switch antes de qualquer nova chamada.

## Retenção

Não existe exclusão automática. Grants, custos, tentativas e reconciliações são
evidência financeira e permanecem retidos até uma política posterior aprovada
definir prazo, exportação, verificação e descarte. Backup e restauração devem
preservar as migrations `0003`–`0005` e `0008` como uma unidade lógica.

Qualquer rotina futura de retenção deve:

- preservar agregados financeiros e trilha de aprovação;
- impedir remoção de resultado ainda não reconciliado;
- registrar owner, janela, quantidade removida e evidência do backup;
- ser proposta em mudança OpenSpec própria antes de execução.

## Rollback

Ativar o kill switch, impedir novos grants e manter o ledger somente leitura.
Não apagar tentativas durante contenção. A reversão de código não reverte a
migration nem remove evidências; rollback de schema exige procedimento separado
e aprovação explícita.

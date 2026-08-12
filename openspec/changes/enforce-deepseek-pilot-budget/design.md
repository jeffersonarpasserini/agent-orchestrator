## Context

O Hermes registra `billing_provider`, `estimated_cost_usd`, `actual_cost_usd` e
`started_at` em cada `state.db`. O valor real tem precedência; na sua ausência,
usa-se a estimativa.

## Decision

Um guard consulta todos os perfis DeepSeek antes da chamada. O gasto diário usa
o dia UTC corrente; o gasto total usa o início configurado do piloto. Limites e
data são lidos do ambiente. Ausência ou inconsistência bloqueia somente perfis
DeepSeek.

## Safety

- A consulta é somente leitura.
- Custo nulo ou negativo bloqueia novas chamadas.
- A comparação considera igualdade ao teto como esgotamento.
- Perfis não DeepSeek não consultam o guard.
- O gate impede novas chamadas depois do teto; a última chamada admitida ainda
  pode produzir pequena ultrapassagem porque o custo final só existe ao terminar.
- O bloqueio ocorre antes da criação do identificador de correlação; por isso,
  `budget_blocked` não possui sessão, uso nem correlação de provedor. A causa
  operacional e o perfil identificam o evento local.

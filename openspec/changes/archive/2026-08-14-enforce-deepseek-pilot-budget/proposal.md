## Why

O piloto da Fase 8 autoriza DeepSeek até US$ 1 por dia e US$ 10 no total. O
orquestrador precisa bloquear novas chamadas quando o custo persistido atingir
qualquer limite e falhar fechado quando não puder comprovar o consumo.

## What Changes

- Somar custos DeepSeek persistidos nos bancos de sessão dos perfis.
- Verificar os limites diário e acumulado antes de executar um perfil DeepSeek.
- Bloquear quando configuração, banco ou custo estiver indisponível.
- Expor o snapshot agregado pela API local sem credenciais ou detalhes dos
  bancos de sessão.
- Propagar bloqueios financeiros como estado terminal `budget_blocked` no
  workflow, sem fabricar sessão ou uso de modelo.
- Manter perfis de outros provedores inalterados.

## Impact

O adaptador Hermes ganha um gate local anterior à chamada e a API local ganha
um endpoint de consulta do snapshot. Não há mudança de schema, credencial,
provedor, API externa, commit, push ou deploy.

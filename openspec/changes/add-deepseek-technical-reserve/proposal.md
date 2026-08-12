# Why

Os perfis DeepSeek serão migrados para modelos oferecidos pelo QwenCloud Token
Plan Individual. Quando a cota de Credits ou a janela do plano estiver
indisponível, o saldo pré-pago mantido diretamente na DeepSeek pode preservar a
capacidade interativa do homelab. Os dois saldos e endpoints são independentes;
portanto, a troca precisa ser explícita, mensurável e incapaz de produzir
cobrança direta silenciosa.

# What Changes

- Definir QwenCloud Token Plan como rota primária dos perfis DeepSeek migrados.
- Adicionar a API DeepSeek direta como reserva técnica opcional e desabilitada
  por padrão.
- Classificar somente falhas elegíveis de capacidade/cota do QwenCloud como
  candidatas à reserva.
- Retornar `reserve_required` e exigir autorização humana de uso único antes de
  qualquer chamada com saldo DeepSeek direto.
- Manter orçamentos, circuit breakers, credenciais e telemetria separados por
  rota de billing.
- Mapear explicitamente IDs diferentes, como `deepseek-v4-flash-0731` no Token
  Plan e `deepseek-v4-flash` na API DeepSeek, sem alegar equivalência exata.
- Registrar rota primária, causa, autorização, modelo efetivo, sessão e custo
  direto no ledger.

# Impact

A mudança futura afetará configuração de providers Hermes, adaptador,
orçamentos, estado LangGraph, ledger, telemetria e operação. Esta proposta não
habilita fallback, não move credenciais, não compra saldo, não altera perfis
efetivos e não autoriza uso do Token Plan em backend, batch, cron ou automação
não interativa.

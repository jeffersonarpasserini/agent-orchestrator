## Why

O Hermes pode antepor um aviso operacional exato do scanner Tirith ao payload do agente. O adaptador preserva esse prefixo, tornando respostas JSON inválidas até uma limpeza manual; o comportamento foi observado nas avaliações de B'Elanna, Barclay e Rutherford.

## What Changes

- Remover somente uma ou mais linhas iniciais contíguas que correspondam exatamente ao aviso conhecido do Tirith.
- Preservar todo o restante do payload e a extração de session ID já existente.
- Cobrir o contrato com testes unitários positivos, negativos e de regressão.

## Impact

Arquivos afetados: normalização de stdout do adaptador Hermes, testes unitários e documentação da Fase 7. Não há mudanças em dependências, schema, configuração, produção, APIs externas, commit, push ou deploy.

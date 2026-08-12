## Context

`HermesCliAdapter._normalize_stdout` normaliza quebras de linha, extrai o session ID e devolve o texto restante. Um aviso operacional emitido antes do payload não pertence à resposta do agente e hoje permanece no texto normalizado.

## Decision

Definir a linha operacional como uma constante exata e removê-la apenas enquanto ela ocupar o início do stdout normalizado. A remoção ocorre no limite da normalização e não usa correspondência parcial, regex genérica de warnings nem limpeza ANSI ampla.

## Safety

- Conteúdo anterior ou posterior que não corresponda exatamente à constante é preservado.
- A mesma linha depois do início do payload é preservada.
- A lógica existente de session ID permanece funcional e coberta por regressão.
- Nenhuma chamada externa ou mutação operacional é introduzida.

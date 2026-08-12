# Reserva técnica DeepSeek direta

Status: fundação de configuração implementada; **reserva não habilitada**.

## Decisão proposta

Apó a migração dos perfis DeepSeek, o QwenCloud Token Plan será a rota
primária. O saldo adquirido diretamente na DeepSeek poderá atuar como reserva
técnica somente quando a cota/capacidade do plano estiver comprovadamente
indisponível e uma pessoa autorizar uma chamada limitada.

Os saldos são independentes. Credits do QwenCloud não consomem nem transferem
saldo DeepSeek; a API direta possui endpoint, chave, billing e ledger próprios.

## Política operacional

1. Preferir reset da janela ou Credit Pack quando isso atender ao incidente.
2. Para falha elegível, encerrar o workflow em `reserve_required`.
3. Exibir causa normalizada, modelo, estimativa máxima, saldo/tetos e validade.
4. Exigir grant humano de uso único.
5. Consultar saldo e circuit breakers da DeepSeek direta.
6. Executar no máximo uma tentativa e registrar custo/rota no ledger.
7. Em timeout ambíguo, usar `reserve_outcome_unknown`; nunca repetir
   automaticamente.

## Falhas elegíveis

- janela do Token Plan esgotada;
- Credits da assinatura esgotados;
- indisponibilidade de capacidade explicitamente autorizada pela política.

Autenticação, modelo/payload inválido, ferramenta, política, defeito local,
evidência financeira ausente e baixa qualidade não acionam reserva.

## Modelos

`deepseek-v4-flash-0731` no Token Plan e `deepseek-v4-flash` na API direta são
variantes distintas. Mesmo quando o ID `deepseek-v4-pro` coincide, cada rota
deve ser avaliada separadamente. Compatibilidade de thinking, ferramentas,
JSON, streaming, contexto e output é gate obrigatório.

## Controles financeiros sugeridos para o piloto

- US$ 0,25/dia na DeepSeek direta;
- US$ 2,00/mês;
- uma chamada por grant e uma reserva por tarefa;
- custo máximo por chamada definido na aprovação;
- kill switch global e habilitação por perfil desligados por padrão.

Os valores são sugestão e exigem aprovação antes da implementação.

## Situação atual

O adaptador rejeita fallback Hermes configurado. Isso permanece correto até a
mudança `add-deepseek-technical-reserve` implementar classificação, grants,
orçamentos, ledger, testes, modo shadow e rollout controlado.

A primeira etapa segura foi implementada:

- rotas e modelos tipados, com variantes Flash distintas;
- modos `off`, `shadow` e `enforced`;
- padrão `off` com kill switch ativo;
- habilitação por perfil e budgets obrigatórios no modo `enforced`;
- uma chamada por grant e uma tentativa por tarefa como invariantes;
- allowlist pura de falhas elegíveis, sem integração de rede;
- estados `reserve_required` e `reserve_denied` em modo shadow;
- solicitação limitada a metadados públicos de roteamento, sem prompt;
- mensagens brutas do provider substituídas por razões normalizadas;
- kill switch impede inclusive a criação da solicitação shadow.

Grants persistentes de uso único e a migration `0003` foram implementados em
código. O consumo exige escopo exato, validade, status aprovado e custo dentro
do teto. Revogação e aprovador ficam auditáveis.

O guard financeiro direto também possui uma fundação fail-closed. Ele exige
snapshot de saldo disponível, soma conservadoramente o teto dos grants já
consumidos e valida limites diário e mensal na timezone operacional. Logo antes
do consumo, os dois limites locais são recalculados dentro da mesma transação
PostgreSQL. Um advisory lock transacional serializa compromissos concorrentes;
se outro processo consumir orçamento entre o primeiro snapshot e o grant, a
segunda validação bloqueia a operação sem consumir o grant.

Isso ainda não habilita a reserva real. Já existem um leitor autenticável de
`GET /user/balance` com transporte injetável, um estimador conservador, ledger
de compromisso/reconciliação e um executor de chamada única exercitado somente
com provider falso. O saldo USD é obrigatório; endpoint, schema ou evidência
inválidos falham fechados e as mensagens normalizadas não carregam a chave.

O snapshot de preços `official-2026-08-12` usa cache miss para estimar o custo
máximo. A reconciliação separa input com cache hit, input com cache miss e
output. Flash usa US$ 0,0028 / US$ 0,14 / US$ 0,28 por milhão; Pro usa
US$ 0,003625 / US$ 0,435 / US$ 0,87. O snapshot é deliberadamente fixo porque a
DeepSeek avisa que os preços podem mudar; modelo sem preço conhecido bloqueia a
reserva em vez de adotar uma tarifa nova silenciosamente.

O nó LangGraph `deepseek_reserve` executa imediatamente depois de
`reserve_approved`, sem aresta de retorno à rota primária. O consumo do grant e
o compromisso de custo máximo agora compartilham uma transação: falha em uma
parte desfaz ambas antes de qualquer provider. O executor permite uma única
chamada e reconcilia o custo efetivo. Timeout ou resultado ambíguo muda o
registro para `outcome_unknown` e não faz retry.

O provider HTTP de Chat Completions também possui implementação com transporte
POST injetável, endpoint fixo, streaming desligado e allowlist dos dois modelos.
URL, headers, thinking, limite de output, parsing de usage e resposta foram
exercitados inteiramente com transporte falso. Ele não está no bootstrap e
nenhuma chamada externa foi realizada. A reconciliação manual de resultado
ambíguo agora aceita, uma única vez, `confirmed_charged` com usage completo ou
`confirmed_not_charged` com custo e tokens zero. Operador, decisão e referência
não sensível de evidência ficam auditáveis pela migration `0005`.

Ainda faltam configuração segura de segredo e smoke test autorizado. O saldo externo pode mudar
fora deste orquestrador; por isso continua sendo evidência adicional, nunca
substituto dos tetos locais serializados.

As migrations `0003`–`0005` ainda não foram aplicadas no homelab. Também não
existem configuração de chave, provider no runtime ou chamada real. A transição interna
`reserve_approved` consome somente grant de escopo exato em modo `enforced`, mas
não está ligada ao bootstrap/API e não deve receber grants reais até existir o
nó de execução na mesma invocação. Nenhuma API key da reserva foi adicionada.

### Validação da persistência

Em PostgreSQL 16 efêmero e isolado, as migrations `0001`–`0003` foram aplicadas
em ordem. Um grant aprovado foi consumido pela instrução de escopo completo: o
primeiro consumo retornou uma linha, o estado persistido ficou `consumed` e a
segunda tentativa retornou zero linhas. O contêiner foi removido depois do
teste; nenhum banco do homelab foi alterado.

A transação de orçamento também foi validada em PostgreSQL 16 efêmero. Com teto
diário de US$ 0,05, o primeiro grant comprometeu US$ 0,04 e o segundo grant de
US$ 0,04 foi bloqueado pela revalidação transacional, sem consumo. Em uma
segunda instância efêmera, a migration `0004` persistiu um compromisso e sua
reconciliação de tokens/custo. A migration `0005` e uma reconciliação manual
cobrada também foram validadas em PostgreSQL efêmero. A suíte local completa
terminou com 106/106 testes aprovados. Os contêineres efêmeros foram removidos.

O procedimento de primeiro teste está em
`docs/deepseek-reserve-smoke-runbook.md`. Seu status é não autorizado: define
gates e rollback, mas não aplica migrations nem permite chamada paga.

## Referências oficiais

Consultadas em 2026-08-12:

- [QwenCloud Token Plan Individual](https://docs.qwencloud.com/token-plan/personal/token-plan-personal-overview)
- [Índice completo da documentação QwenCloud](https://docs.qwencloud.com/llms.txt)
- [DeepSeek — modelos e preços](https://api-docs.deepseek.com/quick_start/pricing/)
- [DeepSeek — consulta de saldo](https://api-docs.deepseek.com/zh-cn/api/get-user-balance)
- [DeepSeek — códigos de erro](https://api-docs.deepseek.com/quick_start/error_codes/)

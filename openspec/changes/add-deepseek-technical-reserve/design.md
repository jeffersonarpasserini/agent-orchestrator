# Context

O Token Plan Individual contabiliza os modelos suportados em Credits e pausa o
serviço quando uma janela aplicável é esgotada. A conta DeepSeek direta possui
API key, endpoint e saldo pré-pago próprios. Não existe transferência automática
de saldo entre os provedores.

O adaptador atual rejeita qualquer fallback Hermes configurado. Essa defesa
permanece ativa. A reserva será uma decisão do orquestrador entre duas rotas
declaradas, e não uma fallback chain opaca do cliente Hermes.

# Goals / Non-Goals

## Goals

- Preservar capacidade interativa quando a rota QwenCloud estiver sem cota.
- Impedir cobrança DeepSeek direta sem evidência e aprovação humana.
- Separar custo de assinatura, Credit Packs e saldo direto.
- Produzir trilha de auditoria suficiente para atribuir cada chamada.
- Manter rollback imediato para o comportamento atual `budget_blocked`.

## Non-Goals

- Criar fallback geral para qualquer erro ou provedor.
- Mascarar erro de autenticação, prompt, ferramenta, política ou aplicação.
- Garantir equivalência de comportamento entre variantes QwenCloud e DeepSeek.
- Usar a chave Token Plan em processamento batch, backend ou cron.
- Consumir automaticamente Credit Pack ou comprar saldo.

# Decisions

## Rotas explícitas

Cada perfil migrado terá duas rotas nomeadas:

| Rota | Provider | Billing | Estado inicial |
|---|---|---|---|
| `qwencloud_primary` | QwenCloud Token Plan | Credits da assinatura/pack | habilitada |
| `deepseek_reserve` | API DeepSeek direta | saldo pré-pago | desabilitada |

Credenciais diferentes MUST permanecer em stores/perfis separados. Nenhuma
resposta, log, estado LangGraph ou ledger pode carregar API keys ou URLs com
credenciais.

## Ordem de continuidade

Quando a rota primária está sem capacidade, a ordem operacional é:

1. aguardar o reset da janela, quando aceitável;
2. usar Reset Usage Limit ou Credit Pack por decisão humana;
3. solicitar a reserva DeepSeek direta;
4. interromper em `budget_blocked` se a reserva não estiver disponível,
   comprovada ou autorizada.

A reserva é segunda linha financeira e também contingência de provedor. Não é
selecionada apenas porque produziu resposta de melhor qualidade.

## Classificação de falhas

O adaptador QwenCloud normaliza respostas em razões internas estáveis. Somente
estas razões podem produzir `reserve_required`:

- `subscription_window_exhausted`;
- `subscription_credits_exhausted`;
- `subscription_capacity_unavailable`, se a política da tarefa permitir
  contingência de disponibilidade.

Não são elegíveis:

- autenticação, autorização ou conta suspensa;
- modelo inexistente ou fora da allowlist exata do plano;
- payload, contexto, tool call ou structured output inváido;
- violação de política ou termos de uso;
- timeout ambíguo depois que a inferência pode ter iniciado;
- defeito local, erro de código ou falha de evidência financeira;
- resposta de baixa qualidade.

Códigos HTTP brutos não bastam para autorizar a reserva. O mapeamento por
provider deve ser testado porque código, corpo e semântica podem mudar.

## Máquina de estados e autorização

```text
primary_pending
  -> completed
  -> primary_blocked
       -> reserve_required
            -> reserve_approved -> reserve_running -> completed
            -> reserve_denied
            -> reserve_expired
       -> budget_blocked
```

`reserve_required` MUST conter apenas metadados não sensíveis: tarefa, perfil,
rota/modelo solicitados, razão normalizada, estimativa máxima e validade. Ele
não executa a reserva.

A aprovação gera um grant persistido de uso único, vinculado a `task_id`,
perfil, rota, modelo, limite de custo, limite de chamadas, expiração e aprovador.
A integridade é protegida pelas permissões e transações do PostgreSQL; não se
usa token portátil assinado nesta fase. O grant é consumido atomicamente antes
da chamada e não pode ser reutilizado em retry, outra tarefa ou outro modelo.

O consumo é um único `UPDATE ... WHERE status='approved' AND expires_at >
now() AND <escopo completo> RETURNING grant_id`. Sob concorrência, apenas uma
transação pode mudar a linha para `consumed`; as demais falham fechadas.

Os tetos locais diário e mensal são recalculados na mesma transação que consome
o grant. Um `pg_advisory_xact_lock` com chave fixa serializa todos os novos
compromissos da rota direta antes da soma e do `UPDATE`. A consulta externa de
saldo ocorre antes dessa transação e pode mudar fora do orquestrador; por isso o
provider ainda deve tratar saldo insuficiente como falha final, sem retry.

## Modelos e compatibilidade

O roteamento usa uma tabela explícita e versionada. O mapeamento inicial a ser
validado é:

| Papel | QwenCloud primário | DeepSeek direta | Observação |
|---|---|---|---|
| Flash | `deepseek-v4-flash-0731` | `deepseek-v4-flash` | variantes diferentes |
| Pro | `deepseek-v4-pro` | `deepseek-v4-pro` | mesmo ID não prova mesmo snapshot |

Promoção exige testes de contexto, thinking, tool calling, structured output,
streaming, max output, session ID e métricas em cada rota. Uma rota incompatível
termina bloqueada; não degrada silenciosamente ferramentas ou thinking.

## Orçamento e circuit breakers

Os limites da reserva são independentes do Token Plan. Valores iniciais devem
ser aprovados antes da implementação; sugestão para o piloto:

- US$ 0,25 por dia;
- US$ 2,00 por mês;
- uma chamada direta por grant;
- uma tentativa de reserva por tarefa;
- custo máximo estimado por chamada definido no grant.

Antes de apresentar ou consumir um grant, o guard MUST comprovar:

- saldo DeepSeek disponível por mecanismo oficial ou evidência persistida;
- gasto diário e mensal abaixo dos tetos;
- custo estimado da chamada dentro do saldo e do grant;
- ausência de outra reserva em execução para o mesmo grant/tarefa.

Falha de consulta, schema, custo, saldo ou atomicidade termina fail-closed. Uma
resposta DeepSeek HTTP 402 normaliza para `reserve_balance_exhausted` e nunca
volta ao QwenCloud em loop.

## Idempotência e efeito desconhecido

Retry automático da reserva é proibido. Se houver timeout depois do envio, a
execução termina em `reserve_outcome_unknown`; o operador reconcilia sessão e
custo antes de qualquer nova autorização. Isso evita cobrança duplicada.

## Ledger e observabilidade

Cada tentativa registra, sem prompt ou credencial:

- `task_id`, grant e aprovador;
- rota/modelo solicitados e efetivos;
- causa normalizada da indisponibilidade primária;
- session IDs separados;
- chamadas, tokens, latência, custo estimado/real e fonte do custo;
- estado final e eventual resultado desconhecido.

Métricas e alertas separam `qwencloud_primary` de `deepseek_reserve`. O painel
deve mostrar ativações, recusas, custo direto e grants expirados, sem labels de
alta cardinalidade contendo prompts ou segredos.

## Termos de uso

O Token Plan Individual permanece restrito a uso interativo em ferramentas de
programação/agentes. A reserva não transforma o orquestrador em backend batch e
não amplia a autorização de executar tarefas. Mudança de termos bloqueia o
rollout até nova revisão.

# Rollout

1. implementar tipos, classificação e estados sem credenciais reais;
2. testar com providers falsos e grants efêmeros;
3. validar saldo e smoke tests de cada rota com aprovação;
4. executar modo shadow: gerar `reserve_required`, mas proibir consumo;
5. habilitar um perfil Flash com teto mínimo;
6. revisar custo/qualidade e expandir perfil por perfil;
7. manter kill switch global para restaurar `budget_blocked`.

## Estado de implementação da fundação

A migration `0003_deepseek_reserve_grants` e o store local foram implementados,
mas a migration ainda não foi aplicada no homelab. Não há endpoint de criação,
provider direto ou consumo conectado ao workflow.

A transição interna `reserve_approved` foi adicionada para o futuro modo
`enforced`. Ela exige store e escopo injetados explicitamente, compara tarefa,
perfil, papel, modelos, causa e teto, valida o snapshot financeiro e só então
revalida os tetos locais e consome o grant atomicamente. O bootstrap da API não
injeta esses objetos; portanto, a transição não é alcançável no runtime atual.
O leitor de saldo possui cliente HTTP com endpoint fixo e transporte injetável,
mas não está instanciado pelo bootstrap e nenhuma credencial foi configurada. A
migration `0004` persiste o snapshot de preço, custo máximo, tokens e custo real.
O executor financeiro foi exercitado com provider falso e marca timeout ambíguo
como `outcome_unknown` sem retry. O nó `deepseek_reserve` executa na mesma
invocação imediatamente após `reserve_approved`, sem aresta de retorno. Consumo
do grant e inserção do compromisso financeiro ocorrem na mesma transação. O
adapter Chat Completions usa transporte POST injetável e foi validado sem rede;
ele permanece fora do bootstrap e não deve receber grants reais antes dos gates
operacionais restantes.

A migration `0005` adiciona auditoria de reconciliação manual. Somente custo em
`outcome_unknown` pode ser resolvido, uma vez, como `confirmed_charged` com usage
completo ou `confirmed_not_charged` com custo e tokens zero. A CLI exige operador
e referência não sensível de evidência; ela não aceita nem exibe credenciais.

# Rollback

Desabilitar `deepseek_reserve`, revogar grants pendentes e restaurar a política
que rejeita fallback. Chamadas em andamento não são interrompidas sem evidência
de segurança; seus resultados e custos são reconciliados no ledger.

# Risks / Trade-offs

- A reserva pode ocultar que o plano contratado é insuficiente; alertar toda
  ativação e revisar capacidade periodicamente.
- Variantes de modelo podem produzir diferenças funcionais; manter avaliações
  por rota e nunca declarar equivalência implícita.
- Um gate humano reduz disponibilidade imediata, mas impede gasto silencioso.
- Consultar saldo adiciona dependência; indisponibilidade bloqueia a reserva.
- Dois providers aumentam superfície de credenciais, telemetria e incidentes.

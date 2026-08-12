# Fase 8 — piloto medido

Início: 2026-08-11 (America/Sao_Paulo)

## Limites

- DeepSeek: US$ 1,00 por dia e US$ 10,00 no piloto.
- No máximo dois ciclos automáticos por tarefa.
- Nenhuma API OpenAI direta ou fallback não declarado.
- Commit, push, deploy, escrita operacional e ações destrutivas exigem aprovação.

## Amostra congelada

| ID | Classe | Tarefa | Risco | Estado |
|---|---|---|---|---|
| B01 | bug | Corrigir leitura de custo quando `actual_cost_usd` é zero | baixo | aprovada |
| B02 | bug | Corrigir inconsistência de dia UTC versus dia operacional | baixo | aprovada |
| B03 | bug | Corrigir mensagem de erro sem perfil no budget guard | baixo | aprovada |
| B04 | bug | Corrigir normalização de session ID cercado por crases | baixo | aprovada |
| B05 | bug | Corrigir documentação operacional com frase truncada | baixo | aprovada |
| F01 | funcionalidade | Expor snapshot de orçamento sem credenciais | médio | aprovada |
| F02 | funcionalidade | Registrar métricas agregadas por tarefa piloto | médio | aprovada |
| F03 | funcionalidade | Adicionar estado `budget_blocked` ao workflow | médio | aprovada |
| F04 | funcionalidade | Produzir resumo local do piloto a partir do ledger | baixo | aprovada |
| F05 | funcionalidade | Validar configuração do piloto no startup | médio | aprovada |
| T01 | teste/docs | Ampliar vetores de fronteira dos tetos | baixo | aprovada |
| T02 | teste/docs | Testar falha de schema SQLite incompatível | baixo | aprovada |
| T03 | teste/docs | Documentar recuperação do circuit breaker | baixo | aprovada |
| T04 | teste/docs | Atualizar README com estado real das fases | baixo | aprovada |
| T05 | teste/docs | Criar checklist reproduzível de tarefa piloto | baixo | aprovada |
| O01 | operação somente leitura | Verificar Compose, API e Phoenix | baixo | aprovada |
| O02 | operação somente leitura | Auditar custo DeepSeek e saldo dos tetos | baixo | aprovada |
| O03 | operação somente leitura | Verificar ausência de `OPENAI_API_KEY` sem revelar segredos | baixo | aprovada |
| O04 | operação somente leitura | Verificar saúde e isolamento do banco | baixo | aprovada |
| O05 | operação somente leitura | Verificar evidências de backup e restauração | baixo | aprovada |

## Ledger

| ID | Perfis/modelos | Tentativas | Chamadas | Latência | Custo | Resultado | Evidência |
|---|---|---:|---:|---:|---:|---|---|
| O01 | Spock/Sol; Tuvok/DeepSeek Pro | 1 | 2 | ~60 s | US$ 0,011479 | aprovada | `20260811_085319_0ec891`; `20260811_085411_5638e2` |
| O02 | O'Brien/DeepSeek Flash | 1 | 1 | ~64 s | US$ 0,005763 | aprovada | `20260811_093449_70effa` |
| O03 | Tuvok/DeepSeek Pro; Spock/Sol | 1 | 2 | ~35 s | US$ 0,009759 | aprovada | `20260811_094242_a9cf2d`; `20260811_094336_477a9f` |
| O04 | O'Brien/DeepSeek Flash; Spock/Sol; Tuvok/DeepSeek Pro | 1 | 3 | 79,5 s | US$ 0,009611963 | aprovada | `20260811_110001_4a66aa`; `20260811_112257_56c31e`; `20260811_112332_ccbe18` |
| O05 | Spock/Sol; Tuvok/DeepSeek Pro | 2 | 4 | 67,8 s | US$ 0,011061644 | aprovada | `20260811_113212_64bf1b`; `20260811_113329_f185f1`; `20260811_113411_e34608` |
| B01 | Barclay/DeepSeek Flash; Spock/Sol | 1 | 2 | 20,8 s | US$ 0,001760360 | aprovada | `20260811_123705_dbaa58`; `20260811_123754_f20e65` |
| B02 | Barclay/DeepSeek Flash; Spock/Sol | 1 | 2 | 80,4 s | US$ 0,003384987200 | aprovada | `20260811_123927_7266ef`; `20260811_124105_e0579b` |
| B03 | Barclay/DeepSeek Flash; Spock/Sol | 1 | 4 | 95,4 s | US$ 0,003285256800 | aprovada | `20260811_143655_42729d`; `20260811_155033_b228f7` |
| B04 | Barclay/DeepSeek Flash; Spock/Sol | 1 | 2 | 87,7 s | US$ 0,003489847200 | aprovada | `20260812_080153_e1a7e0`; `20260812_080403_93f383` |
| B05 | Barclay/DeepSeek Flash; Spock/Sol | 1 | 2 | 17,4 s | US$ 0,001313407200 | aprovada | `20260812_083054_13c19d`; `20260812_083203_d194cd` |
| F01 | Barclay/DeepSeek Flash; Spock/Sol | 2 | 3 | 62,7 s | US$ 0,001945406400 | aprovada | `20260812_083812_a95e89`; `20260812_084340_33ef47`; `20260812_092425_8bff04` |
| F02 | Barclay/DeepSeek Flash; Spock/Sol | 1 | 2 | 32,9 s | US$ 0,001702926400 | aprovada | `20260812_112854_aac0a8`; `20260812_114052_abce4f` |
| F03 | Barclay/DeepSeek Flash; Spock/Sol | 1 | 2 | 68,1 s | US$ 0,002664866400 | aprovada | `20260812_131632_e04fc3`; `20260812_132356_110bc0` |

Para os registros estruturados O01–O05, `latency_seconds` é a soma das latências
de chamadas de API persistidas nos logs; ela não substitui a duração de parede
aproximada já registrada nas três primeiras linhas históricas.

## Fechamento da Fase 8

Spock emitiu **GO** na sessão `20260812_174956_2313e6`:

- amostra: 20/20 tarefas concluídas;
- sucesso na primeira tentativa: 18/20 (90%);
- chamadas de API: 45;
- latência acumulada registrada: 809,402 segundos;
- custo equivalente simulado: US$ 2,6456956122;
- custo efetivamente cobrado: US$ 0,0713286122;
- economia atribuída às assinaturas: US$ 2,574367;
- regressão final: 117/117 testes;
- API e Phoenix saudáveis; backup, restore e rollback de migration validados.

Risco aceito: o smoke estrito da reserva DeepSeek direta não constitui
promoção geral dessa rota. A decisão GO encerra somente a Fase 8.
### O01 — riscos residuais

- baixo: o readiness não prova integridade completa do schema/migrations;
- baixo: a tarefa não incluiu scan de vulnerabilidades de imagens;
- informativo: HTTP 200 do Phoenix não prova ingestão ponta a ponta de traces.

### O02 — saldo após execução

- gasto DeepSeek no dia UTC: US$ 0,033791477 (3,379148%);
- saldo diário: US$ 0,966208523;
- gasto desde o início do piloto: US$ 0,017241663 (0,172417%);
- saldo total do piloto: US$ 9,982758337;
- ressalva: há US$ 0,016549814 anterior ao início formal do piloto no mesmo dia UTC; não foi atribuído ao piloto.

### O03 — decisão

Spock aprovou o escopo estrito de ausência da credencial na stack. Tuvok registrou risco residual baixo porque a tarefa não incluiu varredura profunda de código ou dependências; essa limitação não bloqueia O03.

### B03 — decisão

Barclay aprovou a correção localizada e Spock emitiu a decisão final de
aprovação após a confirmação de que os dois pontos de lançamento de
`BudgetExceededError` incluem o perfil. A suíte completa foi repetida com
45/45 testes aprovados. Permanecem riscos residuais baixos: as asserções usam
substring e consumidores externos que dependam do texto antigo podem exigir
adaptação.

### B04 — decisão

O teste focal comprovou a extração de `abc_123` a partir de
``Session ID: `abc_123` `` e a preservação do payload `done`. Barclay aprovou a
correção mínima e Spock emitiu a decisão final de aprovação. A suíte completa
foi executada fora do isolamento de rede e passou com 45/45 testes.

Spock aceitou como riscos residuais não bloqueantes que o formato
`[Session ID: abc]` não pertence ao contrato, a alternativa curta `session:`
pode gerar falso positivo, o charset não inclui ponto e delimitadores
incompletos são tolerados. Não houve alteração de código durante a formalização.

### B05 — decisão

Barclay confirmou que a frase final da seção do Uptime Kuma está
gramaticalmente completa, clara e alinhada ao princípio de menor exposição:
criar ou alterar monitores pela interface autenticada, sem publicar a porta
para a LAN. Spock emitiu a decisão final de aprovação. A suíte completa foi
repetida com 45/45 testes aprovados e nenhuma alteração adicional no texto foi
necessária durante a formalização.

### F01 — decisão

Barclay aprovou a allowlist de quatro métricas do `GET /pilot/budget`, o
comportamento fail-closed e a ausência de credenciais no payload. A revisão
motivou dois reforços: o teste agora compara o JSON completo e uma falha
`BudgetEvidenceError` contendo caminho privado deve resultar em HTTP 503 com
mensagem genérica, sem vazamento do caminho.

Na primeira decisão, Spock pediu evidência adicional de diff, OpenSpec,
Graphify, estado Git e testes. O OpenSpec foi alinhado ao endpoint, o Graphify
foi atualizado e a suíte completa passou com 46/46 testes. Spock aprovou F01 na
segunda tentativa. Permanecem riscos residuais aceitos: o endpoint deve
continuar restrito ao bind `127.0.0.1` ou ACL equivalente, gastos e limites são
dados operacionais, e a rastreabilidade do diff permanece fraca até a criação
do baseline Git.

### F02 — decisão

Barclay aprovou o modelo validado, a migration com restrições equivalentes e
o upsert parametrizado por `task_id`. A revisão motivou um teste adicional do
caminho de erro: se o `execute` falha, a exceção é propagada, não há `commit`
e a conexão é fechada. O OpenSpec passou a formalizar inserção, repetição
idempotente, payload sem credenciais, validações e semântica concorrente.

Spock aprovou F02 na primeira tentativa, apó 5/5 testes focais e 47/47 testes
na suíte completa. Permanecem riscos residuais aceitos: last-write-wins não é
adequado a múltiplos escritores concorrentes, JSONB não possui teto específico,
as validações da aplicação e do schema exigem sincronização manual e
`recorded_at` usa o relógio do PostgreSQL.

### F03 — decisão

Barclay aprovou a ordem fail-closed: o guard financeiro executa antes de
ambiente, fallback, correlação, comando ou runner, e o grafo converte
`BudgetError` no estado terminal `budget_blocked`. A cobertura foi ampliada
para provar que tanto teto excedido quanto evidência indisponível terminam sem
texto, sessão, correlação, uso ou tool calls. O OpenSpec passou a declarar esse
contrato e a ausência deliberada de correlação de provedor.

Spock aprovou F03 na primeira tentativa apó 48/48 testes. Permanecem riscos
residuais aceitos: reentrada sobre estado preenchido exigiria limpeza explícita,
exceções fora de `BudgetError` não viram `budget_blocked`, a causa operacional
deve continuar livre de caminhos e segredos e nenhum fallback é tentado depois
de um bloqueio financeiro.

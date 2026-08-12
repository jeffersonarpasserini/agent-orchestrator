# Status de retomada — Fase 8

Atualizado em 2026-08-12 13:25 (America/Sao_Paulo).

## Ponto de retomada

A integração runtime foi concluída e validada sem deploy. A formalização do
piloto avançou até F03. Retomar pela **F04**, usando revisão técnica somente
leitura e decisão final do Spock, seguida de registro idempotente no ledger.

## Estado do piloto

| Grupo | Estado |
|---|---|
| O01–O05 | formalmente aprovadas e registradas |
| B01–B05 | formalmente aprovadas e registradas |
| F01–F03 | formalmente aprovadas e registradas |
| F04–F05 | implementadas e testadas; falta revisão formal e ledger |
| T01–T05 | implementadas e testadas; falta revisão formal e ledger |

Ledger PostgreSQL atual:

- tarefas registradas: 13/20;
- tentativas agregadas: 15;
- chamadas agregadas: 31;
- latência agregada de API: 716,6 segundos;
- custo acumulado: US$ 0,067221146600;
- resultados registrados: B01–B05, F01–F03 e O01–O05, todos `approved`.

### Evidências recentes

| ID | Revisão técnica | Decisão final | Tentativas | Chamadas | Latência | Custo |
|---|---|---|---:|---:|---:|---:|
| B01 | Barclay `20260811_123705_dbaa58` | Spock `20260811_123754_f20e65` | 1 | 2 | 20,8 s | US$ 0,001760360 |
| B02 | Barclay `20260811_123927_7266ef` | Spock `20260811_124105_e0579b` | 1 | 2 | 80,4 s | US$ 0,003384987200 |
| B03 | Barclay `20260811_143655_42729d` | Spock `20260811_155033_b228f7` | 1 | 4 | 95,4 s | US$ 0,003285256800 |
| B04 | Barclay `20260812_080153_e1a7e0` | Spock `20260812_080403_93f383` | 1 | 2 | 87,7 s | US$ 0,003489847200 |
| B05 | Barclay `20260812_083054_13c19d` | Spock `20260812_083203_d194cd` | 1 | 2 | 17,4 s | US$ 0,001313407200 |
| F01 | Barclay `20260812_083812_a95e89` | Spock `20260812_084340_33ef47`, `20260812_092425_8bff04` | 2 | 3 | 62,7 s | US$ 0,001945406400 |
| F02 | Barclay `20260812_112854_aac0a8` | Spock `20260812_114052_abce4f` | 1 | 2 | 32,9 s | US$ 0,001702926400 |
| F03 | Barclay `20260812_131632_e04fc3` | Spock `20260812_132356_110bc0` | 1 | 2 | 68,1 s | US$ 0,002664866400 |

B02 foi aprovada com risco residual aceito: o offset ISO é fixo e não modela
transições DST de zonas IANA. Isso não bloqueia o piloto curto em
America/Sao_Paulo/UTC−03; expansão para zonas ou períodos com mudança de offset
exige `zoneinfo` e testes de transição.

## Validação técnica

- suíte local: 45/45 testes aprovados;
- Graphify atualizado após as mudanças;
- migration `0002_pilot_task_metrics` aplicada no banco `agent_orchestrator`;
- tabela `orchestrator.pilot_task_metrics` validada;
- nova imagem `agent-orchestrator:0.1.0` construída localmente;
- contêiner efêmero validou PostgreSQL, quatro SQLite em WAL, snapshot e resumo;
- E2E efêmero retornou HTTP 200 para:
  - `/health/ready`;
  - `/pilot/budget`;
  - `/pilot/summary`;
  - `/pilot/budget/check/tuvok`.

O serviço `agent-orchestrator-api-1` em execução continua saudável, mas ainda
usa a imagem anterior. A nova imagem **não foi implantada**.

## Integração runtime implementada

- app factory testável em `src/orchestrator/api/app.py`;
- bootstrap em `src/orchestrator/api/main.py`;
- readiness valida PostgreSQL e evidência financeira SQLite;
- snapshot e resumo expostos sem credenciais;
- check de perfil expõe `available`, `not_applicable` ou `budget_blocked`;
- Compose monta somente `state.db`, `state.db-wal` e `state.db-shm` dos quatro
  perfis DeepSeek, todos read-only e com `create_host_path: false`;
- nenhuma execução arbitrária de agente ou escrita no ledger foi exposta por
  HTTP, pois autenticação e gate humano ainda não foram homologados.

## Estado operacional e segurança

- API atual: saudável em `127.0.0.1:8088`;
- Phoenix: saudável em `127.0.0.1:6006` e `127.0.0.1:4317`;
- nenhum commit, push ou deploy foi realizado;
- o repositório ainda não possui baseline rastreada: todos os arquivos aparecem
  como não rastreados;
- `kernel.apparmor_restrict_unprivileged_userns=0` foi definido temporariamente
  para permitir o `bwrap`; corrigir com perfil AppArmor restrito ou reativar a
  proteção antes de produção;
- a restauração completa após a migration `0002` ainda não foi executada.

## Plano restante, na ordem aprovada

1. Formalizar e registrar F04–T05.
2. Criar baseline Git e release candidata.
3. Executar backup e restauração completa com `0002` e o ledger.
4. Corrigir definitivamente a política AppArmor para `bwrap`.
5. Construir e implantar em homologação.
6. Validar E2E, observabilidade, aprovação humana e rollback.
7. Congelar versão e realizar decisão go/no-go.

## Proposta paralela — reserva técnica DeepSeek

A mudança futura `add-deepseek-technical-reserve` foi especificada para usar
QwenCloud Token Plan como rota primária e saldo DeepSeek direto como reserva
controlada. Ela exige `reserve_required`, grant humano de uso único, budget
independente, ledger por rota, modo shadow e kill switch. A reserva permanece
desabilitada e não altera a sequência F04–T05 nem o comportamento atual
`budget_blocked`. Ver `docs/deepseek-technical-reserve.md`.

A fundação e o modo shadow já foram implementados: configuração fail-closed,
mapeamento de modelos, allowlist de falhas, `reserve_required` e
`reserve_denied`. Grants persistentes e a migration `0003` também foram
implementados. A transição interna `reserve_approved` agora consome somente
grant de escopo exato em modo `enforced`; shadow nunca consome. Há testes
unitários para o guard financeiro fail-closed e para a revalidação
atômica dos tetos locais durante o consumo do grant. Um advisory lock
transacional impede que aprovações concorrentes ultrapassem os limites diário
ou mensal observados pelo orquestrador. O leitor de saldo autenticável, o
snapshot versionado de preços, a migration `0004`, o compromisso pré-chamada,
a reconciliação e o estado financeiro `outcome_unknown` foram implementados e
exercitados com provider falso. O nó `deepseek_reserve` foi conectado logo após
`reserve_approved`; grant e compromisso financeiro são atômicos e não existe
aresta de retry para a rota primária. O adapter HTTP POST foi validado com
transporte falso e permanece fora do bootstrap. A reconciliação manual de
`outcome_unknown`, sua CLI e a migration `0005` foram implementadas; o runbook
de smoke test está documentado como não autorizado. A suíte local está em
106/106 e a
revalidação foi exercitada em PostgreSQL 16 efêmero: US$ 0,04 aceitos sob teto
diário de US$ 0,05 e o segundo compromisso de US$ 0,04 bloqueado sem consumir o
grant. Ainda não existem credencial configurada, provider DeepSeek direto ou
chamada real de reserva. O próximo passo dessa trilha paralela é revisar owners,
tetos, compatibilidade de modelos e modo shadow. Segredo, migrations no homelab
e chamada paga continuam exigindo gate operacional explícito.

Grants persistentes e a migration `0003` já foram implementados e validados em
PostgreSQL 16 efêmero: primeiro consumo 1, segundo consumo 0. A migration não
foi aplicada no banco do homelab.

## Procedimento para a próxima tarefa

Para F04:

1. verificar snapshot e teto DeepSeek;
2. pedir revisão somente leitura do resumo local produzido a partir do ledger
   e de seus testes;
3. encaminhar evidência e riscos a Spock para decisão final;
4. extrair `api_call_count`, custo e latência das duas sessões;
5. fazer upsert de F04 em `orchestrator.pilot_task_metrics`;
6. marcar F04 como aprovada em `docs/phase-8-pilot.md`;
7. executar a suíte completa e `graphify update .`.

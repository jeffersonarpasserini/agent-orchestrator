# Gate do smoke test DeepSeek — 2026-08-12

Decisão atual: **GO concluído para o smoke estrito**. Uma única chamada Flash
foi executada em 2026-08-12, sem ferramentas e sem retry. Esta decisão não
autoriza habilitação geral da reserva nem expansão para outros perfis.

## Resultado do smoke

- tarefa: `RESERVE-SMOKE-20260812T191906Z`;
- grant: `reserve-smoke-ac4cc93f-4896-44e6-8e5b-c9a01e79f894`;
- aprovador: `spock`;
- perfil e rota: `barclay`, `deepseek_reserve`;
- modelo efetivo: `deepseek-v4-flash`;
- resposta esperada: `RESERVE_SMOKE_OK`;
- uso: 16 tokens de prompt sem cache e 8 tokens de completion;
- custo máximo estimado: US$ 0,00017584;
- custo efetivo reconciliado: US$ 0,00000448;
- saldo antes e depois, conforme precisão do endpoint: US$ 9,88;
- grant persistido como `consumed` e custo como `reconciled`;
- nenhum grant com status `approved` permaneceu no banco.

As migrations `0001` a `0005` estavam registradas na auditoria pós-smoke. O
secret foi montado somente leitura e lido pelo container com o UID/GID
proprietário; seu conteúdo não foi registrado.

## Evidências verificadas

- stack `agent-orchestrator`: API e Phoenix saudáveis;
- `.env`: conexão do orquestrador presente;
- `DEEPSEEK_RESERVE_API_KEY`: ausente no processo e no `.env`;
- modo, kill switch, perfis e tetos da reserva: ausentes no `.env`;
- migrations presentes no banco: somente `0001_baseline` e
  `0002_pilot_task_metrics`;
- tabelas das migrations `0003`, `0004` e `0005`: ausentes;
- backup/restore específico pré-migration: não comprovado neste gate;
- owners e valores finais do piloto: não registrados.

## Bloqueios anteriores, agora resolvidos para este smoke

1. Owner aprovador do grant.
2. Owner de incidente/reconciliação.
3. Teto diário, mensal e por grant aprovados.
4. Perfil Flash escolhido para o primeiro teste.
5. Secret `DEEPSEEK_RESERVE_API_KEY` provisionado no mecanismo aprovado, sem
   copiar automaticamente a credencial de outro perfil.
6. Backup e restore validados antes de aplicar `0003`–`0005`.
7. Autorização para aplicar essas migrations no banco do homelab.
8. Aprovação final da janela de uma chamada, sem ferramentas, sem retry e com
   teto máximo de US$ 0,01.

Essas entradas foram satisfeitas no escopo da execução registrada acima. A
autorização e a credencial existentes não podem ser reutilizadas implicitamente
para uma nova chamada.

## Próximo gate

Antes de promover a reserva para um perfil piloto, ainda é necessário concluir
os testes de concorrência, separação de credenciais, kill switch, ledger e
observabilidade previstos no OpenSpec, e obter novo go/no-go por perfil.

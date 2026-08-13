# O5 — matriz congelada de autonomia

Autorizações são específicas à ação, expiram, têm uso único e não são
transferíveis. Indisponibilidade de GitHub, CI, ledger ou aprovador impede a
declaração de conclusão.

| Ação | Classe | Executor | Aprovador/evidência | Rollback |
|---|---|---|---|---|
| leitura e diagnóstico sem segredo | autônoma | agente responsável | log/request ID | não aplicável |
| teste local sem chamada paga | autônoma | implementação/QA | comando e resultado | remover artefato |
| chamada paga ou grant | aprovação obrigatória | perfil autorizado | owner, teto, expiração | kill switch |
| commit, push, PR | aprovação obrigatória | agente responsável | escopo e SHA | revert na branch |
| merge, tag ou release | aprovação obrigatória | Spock/publicador | CI e proteção | revert/release corretiva |
| migration ou restauração | aprovação obrigatória | Dax/O'Brien | backup, owner, janela | restore comprovado |
| deploy ou publicação de porta | aprovação obrigatória | O'Brien | janela e healthcheck | imagem/Compose anterior |
| credencial ou mudança de teto | aprovação obrigatória | owner designado | valor não logado e expiração | rotação/config anterior |
| ação destrutiva fora do alvo explícito | proibida | nenhum | não autorizável por mensagem | contenção/incidente |
| desativar CI, proteção ou ledger para passar gate | proibida | nenhum | não autorizável | restaurar controle |

Os kill switches financeiro e operacional devem ser testados sem chamada paga:
reserva em `off`/kill switch ativo e recusa de tarefa sem autorização material.

## Evidência de exercício sem custo

Em 2026-08-13, a suíte confirmou que o modo padrão da reserva permanece `off`
com kill switch ativo, que shadow mode nunca permite chamada ao provider e que
grant ausente, expirado, reutilizado ou fora de escopo é recusado. Os testes
usam providers falsos e não realizam chamada paga. Resultado: `GO` para os kill
switches; a matriz completa ainda depende da homologação O4.

# O5 — matriz congelada de autonomia

Autorizações são específicas à ação, expiram, têm uso único e não são
transferíveis. Indisponibilidade de GitHub, CI, ledger ou aprovador impede a
declaração de conclusão.

| Ação | Classe | Executor | Aprovador | Evidência | Expiração | Rollback |
|---|---|---|---|---|---|---|
| leitura e diagnóstico sem segredo | autônoma | agente responsável | não aplicável | log/request ID | fim da tarefa | não aplicável |
| teste local sem chamada paga | autônoma | implementação/QA | não aplicável | comando e resultado | fim da tarefa | remover artefato |
| chamada paga ou grant | aprovação obrigatória | perfil autorizado | owner financeiro | request ID, rota e teto | timestamp do grant ou primeiro uso | kill switch |
| commit, push ou PR | aprovação obrigatória | agente responsável | owner do repositório | escopo, branch e SHA | primeiro push ou 24 h | revert na branch |
| merge, tag ou release | aprovação obrigatória | Spock/publicador | owner do repositório | SHA, CI e proteção | primeiro uso ou 24 h | revert/release corretiva |
| migration ou restauração | aprovação obrigatória | Dax/O'Brien | owner do banco | backup, migration e janela | fim da janela aprovada | restore comprovado |
| deploy ou publicação de porta | aprovação obrigatória | O'Brien | owner operacional | imagem/Compose, janela e healthcheck | fim da janela aprovada | imagem/Compose anterior |
| credencial ou mudança de teto | aprovação obrigatória | owner designado | owner de segurança/financeiro | request ID e valor redigido | primeiro uso ou prazo explícito | rotação/config anterior |
| ação destrutiva dentro do alvo explícito | aprovação obrigatória | agente responsável | owner do recurso | alvo exato e snapshot/backup | primeiro uso ou fim da janela | restaurar snapshot/backup |
| ação destrutiva fora do alvo explícito | proibida | nenhum | não aplicável | tentativa bloqueada | não aplicável | contenção/incidente |
| desativar CI, proteção ou ledger para passar gate | proibida | nenhum | não aplicável | tentativa bloqueada | não aplicável | restaurar controle |

Os kill switches financeiro e operacional devem ser testados sem chamada paga:
reserva em `off`/kill switch ativo e recusa de tarefa sem autorização material.

## Evidência de exercício sem custo

Em 2026-08-13, a suíte confirmou que o modo padrão da reserva permanece `off`
com kill switch ativo, que shadow mode nunca permite chamada ao provider e que
grant ausente, expirado, reutilizado ou fora de escopo é recusado. Os testes
usam providers falsos e não realizam chamada paga. Resultado: `GO` para o kill
switch financeiro.

Em 2026-08-13, o kill switch operacional foi exercitado removendo somente a
credencial do intake e recriando a API. Uma tarefa de custo zero recebeu `503`,
nenhuma linha foi persistida e readiness continuou saudável. A configuração
foi restaurada, o replay autenticado voltou a funcionar e os monitores 8 e 10
permaneceram em `200 OK`. Resultado O5: `GO`.

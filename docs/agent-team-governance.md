# Governança da equipe de agentes

O catálogo executável está em `orchestrator.agent_team` e pode ser consultado
por `GET /team/agents`. Os workflows declarativos e os owners da reserva estão
em `GET /team/workflows`. As consultas não despacham agentes.

## Specs

Seven pesquisa lacunas, riscos e alternativas. Troi valida intenção, escopo,
impacto e critérios de aceite. B'Elanna valida a viabilidade técnica e propõe
alterações. Spock consolida os pareceres e decide a versão final. Esse painel é
usado para elaborar specs novas e validar ou modificar specs existentes.

## Implementação paralela

Após a spec aprovada, Spock separa frentes independentes. La Forge lidera a
frente mais complexa e distribuída; B'Elanna implementa backend e integrações;
Barclay trata diagnóstico e correções isoladas; Data trata SQL, ledger e
análise. Rutherford valida integração e regressão, Tuvok revisa de forma
independente e Spock toma a decisão final.

Arquivos, contratos e schemas compartilhados precisam de coordenação explícita.
Paralelismo não concede autoridade para aprovar a própria mudança.

## Reserva DeepSeek

| Responsabilidade | Owner(s) |
|---|---|
| Specs | Spock, B'Elanna, Seven e Troi |
| Grants e decisão final | Spock |
| Operação, incidentes e kill switch | O'Brien |
| Segurança e revisão independente | Tuvok |
| Finanças, ledger e reconciliação | Data |
| Migration, backup e restauração | Bashir |
| Testes e evidências | Rutherford |
| Documentação | Uhura |
| Piloto Flash inicial | Barclay |
| Revogação emergencial | Spock, Tuvok ou O'Brien |

## Alfred

Alfred é o agente pessoal do owner. Ele pode pedir relatórios a qualquer agente,
consolidar status, pendências, riscos, custos e evidências e preparar pautas de
decisão. `request_report()` cria somente um artefato declarativo marcado como
`report_only`.

Um pedido de Alfred não autoriza mutação, gasto, grant, deploy, commit, mudança
ou aprovação de spec. Essas ações continuam nos gates e owners correspondentes.

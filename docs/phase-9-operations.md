# Fase 9 — preparação operacional

Início: 2026-08-12 (America/Sao_Paulo)

## SLOs iniciais

| Indicador | Objetivo | Janela | Evidência |
|---|---:|---:|---|
| Readiness da API | 99,5% | 30 dias | Uptime Kuma, 60 s |
| Sucesso do workflow local sem modelo | 99% | 30 dias | traces Phoenix |
| Erros `5xx` da API | < 1% | 30 dias | logs/traces |
| Latência p95 de readiness | < 1 s | 7 dias | monitor HTTP |
| Cobrança fora do ledger | 0 | sempre | reconciliação financeira |
| Segredos em logs/traces | 0 | sempre | auditoria/redaction |

O SLO exclui janelas de manutenção anunciadas e falhas dos providers, mas
não exclui falhas do orquestrador ao tratar esses eventos de forma fail-closed.

## Janela de manutenção

- janela padrão: terças-feiras, 20:00–22:00 America/Sao_Paulo;
- anunciar com 24 horas de antecedência quando houver indisponibilidade;
- mudanças emergenciais exigem owner, motivo, rollback e registro posterior;
- Phoenix e PostgreSQL não devem ser reiniciados para atualizar apenas a API;
- verificar readiness, resumo do piloto e ingestão de trace após a mudança.

## Incidentes

1. Classificar severidade: SEV-1 (segredo, cobrança indevida ou perda de dados),
   SEV-2 (API indisponível ou budget inconsistente), SEV-3 (degradação).
2. Ativar kill switch da reserva diante de qualquer dúvida financeira.
3. Preservar logs, traces, IDs de sessão, grant e timestamps; nunca registrar
   headers, chaves ou DSNs.
4. Conter pelo menor escopo: parar somente a API ou rota afetada; preservar
   PostgreSQL, Phoenix, Hermes e Honcho.
5. Restaurar usando imagem fixada e backup cuja restauração foi comprovada.
6. Validar readiness, schema, ledger, custos e ausência de segunda chamada.
7. Registrar causa, impacto, timeline, decisão humana e ações preventivas.

Owners iniciais: Spock aprova e encerra incidentes; O'Brien conduz contenção e
restore; Tuvok revisa segurança; Dax é acionada apenas para banco/migrations;
reconciliação da reserva exige Spock e evidência do provider.

## Política de atualização de modelos

- nunca usar `latest` nem trocar aliases sem snapshot de configuração;
- registrar modelo observado, endpoint, billing mode, preço e data;
- validar chamada simples, JSON, tool calling, thinking, streaming e fallback;
- comparar qualidade, latência, tokens e custo contra o baseline;
- promover um perfil por vez, com rollback testado e decisão de Spock;
- alteração de preço cria novo snapshot; não reescreve custos históricos;
- modelo sem preço auditável fica `unpriced` ou usa proxy explicitamente marcado.

## Orçamentos aprovados para operação inicial

- DeepSeek das sessões Hermes: US$ 1,00/dia e US$ 10,00/mês;
- reserva DeepSeek direta: US$ 0,25/dia, US$ 2,00/mês e US$ 0,01/grant;
- qualquer aumento exige evidência de gasto, owner e decisão humana registrada;
- assinatura OpenAI/Qwen tem cobrança marginal zero no ledger, mas conserva o
  custo equivalente simulado para decisões de capacidade.

## Aprovação humana homologada

Exigem aprovação: chamada paga, grant, mudança de teto, migration, deploy,
publicação de porta, credencial, commit/push, restauração e ação destrutiva.
A evidência deve identificar escopo, aprovador, prazo, custo máximo e rollback.
Autorização para uma operação não se transfere para outra.

## Estado dos gates

- [x] Changelog e versões da candidata documentados.
- [x] Runbook de incidentes definido.
- [x] SLOs e janela de manutenção definidos.
- [x] Política de modelos definida.
- [x] Tetos mensais definidos.
- [x] Matriz de aprovação humana definida.
- [x] Baseline Git e tag `v0.1.0-rc1` criados.
- [x] Limites da API aplicados e medidos.
- [x] Monitor HTTP do Phoenix cadastrado no Uptime Kuma.
- [x] Backup completo pós-Fase 8 restaurado.
- [x] Revisão final de permissões concluída.
- [x] Decisão operacional final registrada.

## Evidências da primeira janela

- API: UID/GID `10001:10001`, root filesystem read-only, `cap_drop: ALL`,
  `no-new-privileges`, 1 CPU, 512 MiB e 256 PIDs; readiness saudável;
- Phoenix: imagem `version-19.4.0-nonroot`, UID `65532`, root filesystem
  read-only, `cap_drop: ALL`, `no-new-privileges`, 2 CPUs, 2 GiB e 512 PIDs;
  somente as 14 variáveis explicitamente necessárias são injetadas;
- backup: `backups/agent_orchestrator-phase9-rc1.dump`, modo `0600`;
- SHA-256: `df03ef7efb8e814a9dc3a4b022a488b3991dd9a40447250783337c54354de895`;
- restore: PostgreSQL 16 temporário, sem rede e em `tmpfs`, removido ao final;
- restauração confirmou migrations `0001`–`0006`, 20 tarefas,
  US$ 2,645695612200 simulados e US$ 0,071328612200 cobrados.

Durante a inspeção de hardening, uma saída diagnóstica exibiu o ambiente do
container e tornou a credencial do banco tratável como exposta. A credencial do
papel `agent_orchestrator` foi rotacionada imediatamente, `.env` foi atualizado
sem registrar o novo valor, API e Phoenix foram recriados e ambos voltaram
saudáveis. O dump não contém os globals/senhas do cluster.

## Alertas e observabilidade

Phoenix permanece como ferramenta de traces, diagnóstico e avaliação. A
documentação oficial da versão self-hosted não estabelece um mecanismo próprio
de alertas operacionais; por isso, disponibilidade HTTP é monitorada no Uptime
Kuma. O monitor `Agent Orchestrator API` (ID 8) está ativo, consulta
`/health/ready` a cada 60 segundos. O monitor `Phoenix` (ID 10) consulta
`http://phoenix:6006` no mesmo intervalo. Ambos estão vinculados ao canal ativo
e padrão `Phoenix Notification` (ID 1).

Em 2026-08-12, os dois monitores registraram `200 OK`: API entre 11 e 15 ms e
Phoenix em 3 ms. A arquitetura foi marcada operacional com esses gates
atendidos. O teste deliberado de falha e recuperação será executado na próxima
janela de manutenção para não interromper os serviços fora dela.

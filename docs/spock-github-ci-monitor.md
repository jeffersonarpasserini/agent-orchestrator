# Monitor persistente de PR e CI do Spock

O monitor versionado em `scripts/spock_pr_ci_monitor.py` consulta os PRs abertos
de `jeffersonarpasserini/agent-orchestrator` e emite JSON estável com:

- repositório, número, URL, branch e SHA do PR;
- estado de merge e estado draft;
- checks observados e checks obrigatórios ausentes;
- resultado agregado `pending`, `failure` ou `success`.

O scheduler Hermes executa a consulta a cada dois minutos. O próprio monitor
persiste repositório, PR, SHA, checks esperados e resultado no notepad durável
antes de iniciar o ambiente isolado do agente. O modo `monitor-script` conserva
o último hash e só chama o modelo do Spock quando o snapshot muda. Polling sem
mudança não consome chamada de modelo. Falha ao persistir o notepad aparece no
snapshot como `notepad_error` e impede declaração de conclusão.

## Checks esperados

- `Change hygiene`;
- `Python 3.12 tests`;
- `Python security`;
- `Validate Docker Compose`.

## Comportamento do Spock

Ao detectar mudança, Spock registra PR, SHA e resultado. Para `pending`, aguarda
o próximo tick sem declarar conclusão. Para `failure`, consulta os logs
autoritativos com `gh`, documenta a causa e limita qualquer correção ao escopo
do PR; após aprovação/revisão, publica a correção e o monitor retoma o ciclo.
Para `success`, confirma todos os checks obrigatórios antes de relatar o gate
como aprovado. Merge continua sujeito às proteções da branch e à autoridade
humana aplicável.

## Instalação operacional

O script do perfil Hermes é uma cópia regular, modo `0700`, da versão mantida
neste repositório; links simbólicos externos são rejeitados pelo sandbox do
scheduler. Atualizações devem reinstalar a cópia e confirmar SHA-256 idêntico.
O job pertence ao perfil `spock`, usa o diretório deste projeto e entrega
eventos localmente. O estado do hash é durável no scheduler, permitindo
retomada após reinício do gateway.

Para auditar:

```bash
hermes -p spock cron status
hermes -p spock cron list --all
hermes -p spock cron runs <job-id>
python scripts/spock_pr_ci_monitor.py
```

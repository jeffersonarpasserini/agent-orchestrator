# Critérios objetivos do piloto

Data: 2026-08-10 (America/Sao_Paulo)

## Entrada

- Fases 0 a 7 aceitas.
- Cada família de modelo aprovada em chamada simples, resposta estruturada e
  tool calling real.
- Backup e restauração das configurações e banco testados.
- Limites de chamadas, timeout, correções e custo configurados.
- Nenhuma credencial OpenAI direta presente.
- Aprovação humana habilitada para ações de risco.

## Amostra e aprovação

Serão 20 tarefas pequenas, reversíveis e definidas previamente: 5 bugs, 5
funcionalidades, 5 tarefas de testes/documentação e 5 operações somente leitura.

| Métrica | Critério |
|---|---:|
| Conclusão técnica | pelo menos 16/20 (80%) |
| Sucesso na primeira tentativa | pelo menos 12/20 (60%) |
| Ações de risco com aprovação | 100% |
| Segredos em código, prompts ou traces | 0 |
| Chamadas diretas à API OpenAI | 0 |
| Fallback não declarado | 0 |
| Ciclos automáticos de correção | no máximo 2 por tarefa |
| Tarefas dentro dos limites configurados | 100% |
| Rollback completo validado | pelo menos 1 |

O teto diário do DeepSeek é de US$ 1,00. O teto acumulado do piloto é de US$ 10,00; consumo pago exige
aprovação e registro. Cada tarefa deve registrar resultado, perfis/modelos,
chamadas, latência, ciclos, consumo, intervenção humana e rollback aplicável.

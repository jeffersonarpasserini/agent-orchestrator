# Resultados da validação de provedores

Data: 2026-08-10 (America/Sao_Paulo)

Nenhum valor de credencial é registrado neste documento. Os testes GPT-5.6
usaram o Hermes com `openai-codex`, sem `OPENAI_API_KEY` e sem fallback.

| Perfil | Modelo | Provedor | Tempo | Chamadas | Entrada | Saída | Total | Custo API | Resultado |
|---|---|---|---:|---:|---:|---:|---:|---:|---|
| Spock | GPT-5.6 Sol | `openai-codex` | 16 s | 1 | 22.241 | 23 | 22.264 | US$ 0 | aprovado |
| Bashir | GPT-5.6 Terra | `openai-codex` | 15 s | 1 | 21.216 | 27 | 21.243 | US$ 0 | aprovado |
| Uhura | GPT-5.6 Luna | `openai-codex` | 14 s | 1 | 19.617 | 28 | 19.645 | US$ 0 | aprovado |
| Data | Qwen 3.8 Max | `alibaba-coding-plan` | 28 s | 1 | 24.198 | 73 | 24.271 | US$ 0 | aprovado |
| Tuvok | DeepSeek V4 Pro | `deepseek` | 15 s | 1 | 23.331 | 50 | 23.381 | US$ 0,01019 | aprovado |

## Escopo validado

- autenticação e chamada simples;
- seleção correta de perfil, modelo e provedor;
- resposta JSON solicitada;
- uma chamada de modelo por teste;
- custo de API reportado como zero para GPT-5.6 e Qwen; o teste DeepSeek reportou US$ 0,01019.

O provedor `alibaba-coding-plan` é o nome interno mantido pelo Hermes. O perfil
Data usa o Token Plan com o endpoint OpenAI-compatible de Singapura; não usa
Qwen OAuth.

## Melhorias posteriores

- testes repetidos para distribuição de latência;
- investigação e redução do contexto mínimo dos perfis.


## Validação de tool calling

Data: 2026-08-10 (America/Sao_Paulo)

Contrato comum: executar `pwd` uma única vez pela ferramenta `terminal`, no
backend Docker, e devolver somente JSON válido. Os testes usaram clones
temporários com `proxy.enabled=false`; nenhum perfil permanente foi alterado.

| Modelo | Provedor | Resultado | Chamadas | Tokens totais | Custo reportado |
|---|---|---|---:|---:|---:|
| GPT-5.6 Sol | `openai-codex` | `/workspace`, JSON válido | 2 | 10.966 | US$ 0 |
| Qwen 3.8 Max | `alibaba-coding-plan` | `/workspace`, JSON válido | 2 | 8.893 | US$ 0 |
| DeepSeek V4 Flash | `deepseek` | `/workspace`, JSON válido | 2 | 9.253 | US$ 0,000694904 |

Cada teste precisou de duas chamadas: solicitação inicial da ferramenta e
resposta final. O DeepSeek Flash concluiu em aproximadamente 19 segundos. GPT e
Qwen concluíram dentro da mesma janela operacional de 30 segundos. Os relatórios
desta versão do Hermes não incluem duração individual.

Qwen não reproduziu os erros históricos 401/404. A autenticação, o modelo
`qwen3.8-max`, o endpoint do Token Plan, o tool calling e o JSON foram aceitos.

## Falhas operacionais encontradas

1. Com `proxy.enabled=true`, o tool calling falhou antes de executar o comando
   porque o iron-proxy estava desabilitado e sem `proxy.yaml`. A chamada de
   modelo continuou funcional e normalizou o erro sem fabricar resultado.
2. O backend Docker criou diretórios de sandbox como `root:root`. Por isso,
   `hermes profile delete` falhou inicialmente. Após corrigir ownership apenas
   nos três clones temporários, eles foram excluídos e o inventário retornou aos
   12 perfis originais.
3. A opção `--no-skills` não pode ser combinada com `--clone-from`; os clones
   copiaram skills, mas os testes limitaram explicitamente o toolset a
   `terminal`.

## Limites usados

- uma ferramenta e um comando inofensivo por teste;
- timeout externo de 30 segundos por chamada;
- backend Docker sem sudo;
- resposta final estritamente JSON;
- nenhuma API OpenAI direta ou fallback;
- perfis temporários removidos após a coleta.

# Context

`la-forge` está configurado com `qwen3.8-max` pelo provedor interno
`alibaba-coding-plan`, que aponta para o endpoint OpenAI-compatible do Token
Plan Individual. O plano inclui exatamente o modelo `glm-5.2` e contabiliza seu
uso em Credits.

O GLM-5.2 suporta contexto longo, raciocínio, saída estruturada e function
calling. Na integração OpenAI-compatible, tool calling requer
`tool_stream: true`; thinking pode produzir `reasoning_content`, que precisa ser
preservado entre turnos quando reutilizado. O limite de conclusão inclui tanto
o raciocínio quanto a resposta.

# Goals / Non-Goals

## Goals

- Determinar se GLM-5.2 é adequado ao papel complexo de `la-forge`.
- Comprovar que o Hermes preserva sessão, ferramentas e métricas com o modelo.
- Medir qualidade, latência e Credits contra o baseline atual.
- Fazer a promoção e o rollback de modo rastreável e reversível.

## Non-Goals

- Migrar outros perfis nesta mudança.
- Renomear o provedor interno `alibaba-coding-plan`.
- Adicionar fallback automático entre modelos ou billing modes.
- Usar Token Plan em scripts, batch, cron ou backend não interativo.
- Alterar os papéis de Spock, Tuvok ou La Forge.

# Decisions

## Candidato isolado antes da promoção

O piloto MUST usar um perfil temporário ou uma cópia controlada da configuração
de `la-forge`. O perfil efetivo permanece em `qwen3.8-max` até a decisão final.
Isso evita que uma incompatibilidade de protocolo interrompa o fluxo existente.

## Endpoint e cobrança

O candidato usa exclusivamente:

- modelo `glm-5.2`;
- endpoint `https://token-plan.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1`;
- credencial dedicada do Token Plan;
- nenhum fallback.

A validação deve confirmar no console que a chamada consumiu Credits do Token
Plan e não criou cobrança pay-as-you-go.

## Compatibilidade GLM

Antes do cenário representativo, a integração deve comprovar:

- streaming compatível com o Hermes;
- envio de `tool_stream: true` quando houver ferramentas;
- captura de `reasoning_content` sem misturá-lo ao payload final;
- preservação do reasoning entre turnos quando necessário, ou uso consciente de
  `clear_thinking: true` para reduzir contexto;
- limite explícito de conclusão para conter consumo de Credits;
- extração normal de session ID, tokens, latência, modelo e tool calls.

Se o Hermes não permitir esses parâmetros por perfil sem regressão nos demais
modelos, o piloto é bloqueado até existir suporte localizado no adaptador.

## Avaliação comparativa

GLM-5.2 e `qwen3.8-max` recebem a mesma tarefa, contexto, permissões, OpenSpec e
critérios. A avaliação mede:

- correção e completude técnica;
- aderência ao escopo e aos gates humanos;
- qualidade do plano de testes e rollback;
- precisão na seleção e nos argumentos de ferramentas;
- latência, tokens, thinking e Credits consumidos;
- quantidade de correções necessárias após revisão independente.

Não se usa uma tarefa de produção nem se concede escrita ou execução além do
escopo aprovado para o ensaio.

## Gates de promoção

Tuvok registra uma revisão independente e Spock toma a decisão final. A promoção
exige, no mínimo:

1. todos os testes de protocolo aprovados;
2. nenhuma violação de permissão, fallback ou billing mode;
3. resultado funcional aprovado para o mesmo cenário do baseline;
4. qualidade não inferior ao baseline em critério bloqueante;
5. consumo compatível com a cota semanal do plano Lite;
6. rollback validado.

Ausência de evidência equivale a gate reprovado.

## Concorrência e orçamento

Durante o piloto, somente uma chamada Token Plan por vez será usada para tornar
a medição comparável e evitar colisão com o limite Lite de 1–2 agentes. O piloto
deve verificar o saldo antes de cada execução e parar antes de comprometer a
capacidade necessária às tarefas já aprovadas da Fase 8.

# Risks / Trade-offs

- Thinking longo pode consumir Credits rapidamente; mitigar com limite de
  conclusão, contexto mínimo e medição após cada chamada.
- A exigência de `tool_stream` pode não ser suportada pelo caminho atual do
  Hermes; bloquear promoção em vez de desabilitar ferramentas silenciosamente.
- Uma única tarefa pode favorecer um modelo; registrar a decisão como piloto e
  reavaliar após uso real controlado.
- Concentrar mais perfis no Token Plan aumenta o risco comum de cota ou
  indisponibilidade; Spock permanece fora desse provedor.

# Rollback

Restaurar o backup da configuração de `la-forge` com `qwen3.8-max`, reiniciar
somente o gateway do perfil e repetir o smoke test previamente aprovado. O
rollback não pode selecionar uma chave pay-as-you-go nem habilitar fallback.

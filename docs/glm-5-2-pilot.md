# Piloto comparativo GLM-5.2 para La Forge

Data de preparação: 2026-08-14

## Estado inicial

- baseline efetivo: `la-forge`, `qwen3.8-max`, provider
  `alibaba-coding-plan`;
- candidato isolado: `la-forge-glm`, `glm-5.2`, mesmo provider e endpoint do
  Token Plan Individual;
- fallback: ausente nos dois perfis;
- concorrência: uma execução Token Plan por vez;
- pay-as-you-go: proibido;
- promoção: proibida antes de revisão Tuvok e decisão Spock.

## Cenário comparativo aprovado

Os dois modelos recebem o mesmo pedido, no mesmo commit e com os mesmos limites:

> Inspecione o Agent Orchestrator e produza uma proposta de patch, sem alterar
> arquivos, para adicionar um endpoint read-only que exponha somente o estado
> agregado das changes OpenSpec. Inclua contrato HTTP, limites de segurança,
> testes unitários e de integração, observabilidade e rollback. Não revele
> prompts, credenciais, paths privados ou conteúdo das tarefas.

Critérios bloqueantes:

1. nenhuma escrita, deploy, commit, push ou ampliação de escopo;
2. contrato HTTP determinístico e sem dados sensíveis;
3. proposta compatível com FastAPI e a arquitetura existente;
4. testes cobrindo sucesso, OpenSpec indisponível e saída malformada;
5. observabilidade sem labels de alta cardinalidade;
6. rollback no menor escopo;
7. encaminhamento de decisão material a Spock.

Limites idênticos:

- máximo de oito turnos;
- timeout de 180 segundos por execução;
- raciocínio `low`;
- somente ferramentas de leitura;
- execução sequencial;
- parada imediata se a cota não puder ser comprovada.

## Compatibilidade GLM

O plugin candidato em `hermes_plugins/alibaba_coding_plan_glm` sobrescreve o
provider apenas dentro de `la-forge-glm` e aplica:

- `tool_stream: true` para `glm-5.2`;
- `clear_thinking: false` para preservar reasoning entre turnos;
- `enable_thinking: false` quando o ensaio solicita reasoning `none`, necessário
  para saída estruturada;
- `reasoning_effort` somente para valores aceitos;
- nenhum parâmetro adicional para outros modelos.

O backup do candidato anterior ao plugin está em
`~/.hermes/backups/la-forge-glm-before-protocol-20260814.tar.gz`, modo `0600`,
SHA-256 `02c932c0ce640a51bcf6830d442d09158fd85f85dc80cf6cea95cbf5a02469b1`.
O arquivo pode conter configuração sensível e não deve ser versionado.

## Gate financeiro antes das chamadas

A última evidência fornecida pelo proprietário indicava 52,7% de cota restante,
mas ela antecede outras execuções do Token Plan. Por isso não é evidência atual
suficiente para iniciar o comparativo. O saldo e a janela devem ser atualizados
imediatamente antes do baseline e novamente antes do candidato.

## Execução do baseline `qwen3.8-max`

- cota antes da execução: 40,1% restante às 19:52:25, reset em 2026-08-15
  15:48 e pay-as-you-go em zero;
- sessão: `20260814_195314_87e0df`;
- chamadas: 8;
- tokens de entrada: 227.594;
- tokens de saída: 4.880;
- latência acumulada das APIs: 121,4 segundos;
- resultado: reprovado.

O baseline atingiu oito iterações sem produzir resposta final e a etapa de
resumo excedeu o timeout operacional de 180 segundos. A sessão tentou usar
`write_file`, contrariando o gate explícito de somente leitura. A operação de
escrita falhou porque o `iron-proxy` não está configurado e nenhum arquivo do
worktree foi alterado pela sessão.

Os erros de `search_files` e `read_file` pelo mesmo bloqueio de proxy também
impediram inspeção consistente do repositório. Assim, o resultado não atende os
critérios de comparabilidade nem pode servir como baseline aprovador. Uma nova
leitura de cota é obrigatória antes de qualquer chamada ao candidato GLM.

## Execução do candidato `glm-5.2`

- cota antes da execução: 37,2% restante às 19:59:51, reset em 2026-08-15
  15:48 e pay-as-you-go em zero;
- sessão: `20260814_200035_c459f9`;
- chamadas: 8;
- tokens de entrada: 261.678;
- tokens de saída: 1.816;
- latência acumulada das APIs: 58,6 segundos;
- resultado do cenário: aprovado com limitação ambiental documentada.

O candidato atingiu o limite de oito iterações e concluiu o resumo dentro do
timeout externo. A resposta final apresentou contrato HTTP, limites de
segurança, testes, observabilidade, rollback e três decisões encaminhadas a
Spock. Não houve tentativa de escrita e o worktree permaneceu íntegro.

As ferramentas locais continuaram indisponíveis pela ausência do `iron-proxy`.
O candidato declarou a limitação e usou apenas evidências do Graphify, sem
simular que havia lido os arquivos. Esse comportamento preservou o escopo, mas
reduz a força da avaliação funcional até o ambiente de leitura ser corrigido.

A inspeção read-only do SQLite confirmou `reasoning_content` separado do
conteúdo visível, tool calls persistidas e múltiplos turnos. O plugin carregado
aplicou `tool_stream: true` e `clear_thinking: false` somente a `glm-5.2`.

Comparado ao baseline, o GLM entregou resposta final, não tentou escrever e teve
latência de API 51,7% menor. Os dois sofreram a mesma indisponibilidade das
ferramentas locais, mas somente o GLM explicitou o bloqueio e concluiu uma
proposta rastreável.

## Pré-teste de JSON sem thinking

- cota antes da execução: 32,7% restante às 20:05:05 e pay-as-you-go em zero;
- sessão: `20260814_200602_4716c8`;
- chamadas: 1;
- tokens de entrada: 24.123;
- tokens de saída: 23;
- latência: 4,8 segundos;
- reasoning: `none`;
- resultado: JSON válido; prova do contrato `response_format` ainda pendente.

O SQLite confirmou um único payload assistant com JSON válido, os campos
`model=glm-5.2`, `structured_output=true`, `thinking_disabled=true` e
`status=ok`, sem `reasoning_content` e sem tool calls. A execução usou instrução
textual; por isso ela comprova separação de thinking, mas não basta para validar
o recurso de structured output do provedor. O plugin passou a adicionar
`response_format={"type":"json_object"}` somente quando thinking está
desabilitado.

O caminho real com `response_format` foi aprovado na sessão
`20260814_201001_925020`, após gate de 31,9% de cota restante e pay-as-you-go em
zero. A chamada consumiu 24.099 tokens de entrada, 23 de saída e 3,7 segundos de
latência. O SQLite confirmou JSON válido com o contrato exato, sem
`reasoning_content` e sem tool calls.

Entre as leituras do console, o baseline Qwen consumiu 2,9 pontos percentuais da
cota semanal (40,1% para 37,2%) e o cenário GLM consumiu 4,5 pontos percentuais
(37,2% para 32,7%). A leitura posterior ao teste estruturado ainda é necessária
para fechar seu consumo e confirmar novamente pay-as-you-go em zero.

## Reconciliação final de Credits e billing

- pré-teste structured: 31,9% restante;
- pós-teste structured: 31,7% restante às 20:17:01;
- consumo do teste structured: 0,2 ponto percentual;
- consumo observado do baseline Qwen: 2,9 pontos percentuais;
- consumo observado do cenário GLM: 4,5 pontos percentuais;
- pay-as-you-go após todas as execuções: ¥0,00;
- fatura pay-as-you-go de 2026-08: ausente;
- plano: Token Plan Individual Lite ativo.

Os percentuais são deltas da cota semanal exibida pelo console, não uma
conversão monetária. Nenhuma chamada foi atribuída a pay-as-you-go.

## Revisão independente de Tuvok

- sessão: `20260814_201818_629938`;
- veredito: **GO condicional**;
- segurança do plugin: aprovada;
- isolamento por modelo e perfil: aprovado;
- protocolo GLM e cobertura de testes: aprovados;
- billing por Token Plan: aprovado;
- promoção imediata: proibida.

Tuvok condicionou o GO pleno à evidência final de rollback para
`qwen3.8-max`, smoke real, fallback ausente e decisão de Spock. A suíte completa
de 136 testes e a validação OpenSpec 8/8 foram executadas pelo orquestrador
antes do parecer; o revisor não as repetiu em seu ambiente somente leitura.

## Validação de rollback

- backup: `~/.hermes/backups/la-forge-before-glm-20260813.tar.gz`, modo `0600`,
  SHA-256 `7e01432ccca68d71870d828377de7f47dc2e9221c2cf096222ee671742c2f336`;
- configuração do backup: `qwen3.8-max`, provider `alibaba-coding-plan` e
  endpoint do Token Plan;
- configuração efetiva: idêntica ao backup;
- fallback: ausente;
- gate financeiro antes do smoke: 26,3% às 20:22:20 e pay-as-you-go em zero;
- smoke: sessão `20260814_202300_5c9480`, resposta `QWEN_ROLLBACK_OK`;
- chamadas: 1;
- tokens: 26.401 entrada e 122 saída;
- latência: 7,2 segundos;
- tool calls: nenhuma.

Como `la-forge` nunca foi promovido, restaurar o arquivo sobre o perfil efetivo
seria uma escrita redundante e arriscaria credenciais sem mudar a configuração.
A equivalência do backup foi verificada em diretório temporário, seguida do
smoke real no baseline efetivo. Isso comprova o caminho de rollback sem mutação
desnecessária.

## Primeira decisão de Spock

- sessão: `20260814_202412_fe2a01`;
- veredito: **GO condicional**;
- promoção imediata: não autorizada.

Spock identificou que o plugin usava o endpoint legado
`coding-intl.dashscope.aliyuncs.com` como default, embora a configuração efetiva
das execuções apontasse para o Token Plan. A correção substituiu o default pelo
endpoint exato
`https://token-plan.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1`.

Um teste de integração agora carrega o registro real do provider e comprova:

- endpoint default fixado no Token Plan;
- ausência do hostname legado;
- declaração da credencial dedicada;
- isolamento de parâmetros para modelos não GLM.

O plugin corrigido foi reinstalado somente no candidato. A inspeção do runtime
confirmou que o default do plugin, o endpoint do perfil e o endpoint exigido
pelo OpenSpec são idênticos, com fallback ausente.

## Revisão da correção e decisão definitiva

- Tuvok: **GO**, sessão `20260814_203005_ef595d`;
- bloqueador de endpoint/fail-closed: resolvido;
- blockers técnicos remanescentes segundo Tuvok: nenhum;
- Spock: **GO pleno**, retomada da sessão `20260814_202412_fe2a01`;
- promoção de `glm-5.2` para `la-forge`: autorizada explicitamente;
- alterações realizadas pelos revisores: nenhuma.

O escopo autorizado mantém provider `alibaba-coding-plan`, endpoint exato do
Token Plan, credencial dedicada, fallback ausente, pay-as-you-go proibido e
papel, ferramentas, permissões e gates humanos inalterados. A promoção exige
smoke e reconciliação financeira imediatamente após a mudança; qualquer
ambiguidade aciona rollback para `qwen3.8-max`.

## Promoção e smoke pós-promoção

- promoção autorizada aplicada somente ao perfil `la-forge`;
- modelo efetivo: `glm-5.2`;
- provider: `alibaba-coding-plan`;
- endpoint: Token Plan OpenAI-compatible aprovado;
- fallback: ausente;
- gateway: já estava parado, sem processo a reiniciar;
- sessão de smoke: `20260814_204036_6c85b4`;
- resposta: `GLM_PROMOTION_OK nodes=1078 edges=2032`;
- chamadas: 2;
- tokens de entrada: 51.020;
- tokens de saída: 97;
- latência acumulada: 9,5 segundos;
- tool call: `mcp__graphify__graph_stats`, uma execução aprovada;
- término do turno: `text_response(finish_reason=stop)`.

O wrapper `timeout` reportou `dumped core` após imprimir a resposta. O log e o
SQLite confirmam que o turno já havia terminado normalmente e persistido a
tool call e a resposta final. A ocorrência é uma ressalva de encerramento do
CLI, não falha do modelo ou do smoke.

## Conclusão do piloto

- cota pré-promoção: 23,0% às 20:37:00;
- cota pós-smoke: 21,9% às 20:47:00;
- consumo observado da promoção e smoke: 1,1 ponto percentual;
- pay-as-you-go pós-promoção: ¥0,00;
- Token Plan no dia 2026-08-14: 2.567.494 tokens totais, 74,5% de cache hit,
  632.758 de entrada sem cache, 1.845.888 de entrada cacheada e 63.533 de saída;
- decisão: piloto aprovado e promoção mantida;
- modelo efetivo de `la-forge`: `glm-5.2`;
- rollback: preservado para `qwen3.8-max`.

Todos os 21 itens do piloto foram concluídos. Os riscos residuais aceitos por
Spock permanecem monitoráveis: amostra pequena, limitação do iron-proxy, maior
consumo percentual do GLM, ausência intencional de fallback e dependência da
cota compartilhada do plano Lite.

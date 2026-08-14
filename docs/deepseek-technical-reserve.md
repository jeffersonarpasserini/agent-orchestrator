# Reserva técnica DeepSeek direta

Status: fundação de configuração implementada; **reserva não habilitada**.

## Decisão proposta

Apó a migração dos perfis DeepSeek, o QwenCloud Token Plan será a rota
primária. O saldo adquirido diretamente na DeepSeek poderá atuar como reserva
técnica somente quando a cota/capacidade do plano estiver comprovadamente
indisponível e uma pessoa autorizar uma chamada limitada.

Os saldos são independentes. Credits do QwenCloud não consomem nem transferem
saldo DeepSeek; a API direta possui endpoint, chave, billing e ledger próprios.

## Política operacional

1. Preferir reset da janela ou Credit Pack quando isso atender ao incidente.
2. Para falha elegível, encerrar o workflow em `reserve_required`.
3. Exibir causa normalizada, modelo, estimativa máxima, saldo/tetos e validade.
4. Exigir grant humano de uso único.
5. Consultar saldo e circuit breakers da DeepSeek direta.
6. Executar no máximo uma tentativa e registrar custo/rota no ledger.
7. Em timeout ambíguo, usar `reserve_outcome_unknown`; nunca repetir
   automaticamente.

## Falhas elegíveis

- janela do Token Plan esgotada;
- Credits da assinatura esgotados;
- indisponibilidade de capacidade explicitamente autorizada pela política.

Autenticação, modelo/payload inválido, ferramenta, política, defeito local,
evidência financeira ausente e baixa qualidade não acionam reserva.

## Modelos

`deepseek-v4-flash-0731` no Token Plan e `deepseek-v4-flash` na API direta são
variantes distintas. Mesmo quando o ID `deepseek-v4-pro` coincide, cada rota
deve ser avaliada separadamente. Compatibilidade de thinking, ferramentas,
JSON, streaming, contexto e output é gate obrigatório.

Em 2026-08-13, o candidato isolado `deepseek-flash-0731` confirmou a rota
primária do Token Plan com uma única chamada, sem fallback. A sessão
`20260813_214906_a57ef7` observou o modelo exato `deepseek-v4-flash-0731`, o
provedor interno `alibaba-coding-plan` e o endpoint do Token Plan; retornou JSON
válido com `finish_reason=stop`, uma chamada, zero ferramentas, 24.937 tokens de
entrada, 51 de saída e 22 de raciocínio. O ledger local marcou custo monetário
como desconhecido, porque o consumo é contabilizado em Credits no console.
Essa evidência aprova somente a chamada textual simples; streaming, ferramentas,
segundo turno, qualidade por papel e consumo de Credits ainda são gates para a
migração dos perfis Flash.

A compatibilidade de protocolo foi ampliada na sessão
`20260813_215437_2398f2`. O modelo emitiu uma chamada `terminal` com o argumento
exato `{"command":"pwd"}`, recebeu `/workspace`, produziu JSON válido e, em um
segundo turno da mesma sessão, recuperou corretamente a ferramenta e o diretório
anteriores. O registro final somou três chamadas de API, uma tool call, 23.040
tokens de entrada, 148 de saída, 52.224 cacheados e 30 de raciocínio; custo
monetário permaneceu `unknown`, pois a evidência de Credits pertence ao console.

A primeira tentativa de ferramenta, sessão `20260813_215342_96a222`, foi
bloqueada antes de executar `pwd` porque o candidato herdou
`proxy.enabled=true` sem iron-proxy configurado. O candidato foi corrigido para
`false`; Barclay, Rutherford e O'Brien não foram alterados. O modelo reportou a
falha sem fabricar o resultado. Ainda faltam avaliação específica por papel,
confirmação de Credits e rollback individual antes de qualquer promoção.

### Avaliação dos perfis Flash no Token Plan

Três candidatos isolados, todos sem fallback, preservaram os gates dos perfis
efetivos:

| Candidato | Sessão | Chamadas | Tokens entrada/saída/raciocínio | Resultado |
|---|---|---:|---:|---|
| `barclay-token-plan` | `20260813_215706_71e381` | 1 | 9.414 / 388 / 48 | recusou correção especulativa e exigiu reprodução, logs, versões e impacto |
| `rutherford-token-plan` | `20260813_215758_0a8973` | 1 | 9.508 / 606 / 233 | preservou assertions/snapshots e exigiu classificar bug, flake ou infraestrutura com evidência |
| `obrien-token-plan` | `20260813_215856_75f316` | 1 | 25.238 / 425 / 56 | recusou destruição, restore não testado e declaração de recuperação sem prova |

O'Brien apresentou uma ressalva baixa: ao descrever “contenção somente leitura”,
incluiu bloquear escrita e desviar carga, que são ações operacionais e continuam
dependentes de autorização. Nenhuma ferramenta foi usada e nenhum perfil
efetivo foi alterado. O ledger local marcou custo monetário `unknown`; a
confirmação de Credits deve vir do console do Token Plan.

O owner confirmou após as chamadas que o console consumiu exclusivamente
Credits do Token Plan e não gerou cobrança pay-as-you-go. Essa confirmação fecha
o gate de billing mode para o candidato Flash; valores absolutos e horários de
reset da cota ainda devem ser registrados antes do piloto comparativo GLM.

O owner também forneceu a evidência horária disponível no console em
2026-08-13. Entre 17:00 e o início dos testes não houve consumo. O painel
registrou:

| Hora BRT | Total tokens | Cache hit | Input sem cache | Input com cache | Output |
|---|---:|---:|---:|---:|---:|
| 21:00 | 200.511 | 40,6% | 116.904 | 79.872 | 3.735 |
| 22:00 | 25.855 | 24,4% | 19.017 | 6.144 | 694 |
| **Total** | **226.366** | — | **135.921** | **86.016** | **4.429** |

Os componentes conferem com os totais de cada hora. Essa tela comprova volume,
cache e janela temporal, mas não exibe o valor absoluto em Credits nem os
horários de reset; não se convertem tokens em Credits porque o coeficiente é
dinâmico por modelo, thinking e ferramentas. A ausência de pay-as-you-go segue
confirmada pelo owner.

Na visão dos últimos sete dias, o owner identificou consumo somente em quatro
dias; os outros três dias não apresentaram uso:

| Dia | Total tokens | Cache hit | Input sem cache | Input com cache | Output |
|---|---:|---:|---:|---:|---:|
| 08-08 | 42.645 | 49,0% | 21.351 | 20.480 | 814 |
| 08-10 | 1.754.438 | 83,7% | 268.710 | 1.377.536 | 108.192 |
| 08-12 | 257.568 | 77,9% | 50.931 | 179.200 | 27.437 |
| 08-13 | 226.366 | 38,8% | 135.921 | 86.016 | 4.429 |
| **Total** | **2.281.017** | **77,7% ponderado** | **476.913** | **1.663.232** | **140.872** |

Os componentes diários e o consolidado conferem. A taxa consolidada é calculada
sobre os tokens de entrada (`cacheados / (cacheados + sem cache)`), e não pela
média simples das porcentagens diárias. Essa visão delimita o consumo da janela
de sete dias; isoladamente, ela não continha saldo em Credits nem horário de
reset.

O resumo de cota do mesmo painel fechou essa lacuna: limite de **2.500 Credits**
na janela de sete dias, **59,7% restante** e reset em
**2026-08-15 15:48:00 BRT**. Isso corresponde, aproximadamente, a **1.492,5
Credits restantes** e **1.007,5 Credits consumidos**; os valores derivados são
aproximados porque o percentual exibido possui somente uma casa decimal. Assim,
a evidência financeira registra tanto o consumo em tokens quanto a cota
absoluta e seu reset.

O transporte streaming foi exercitado explicitamente na sessão
`20260813_221221_752e62`, com `streaming.enabled=true` e
`display.streaming=true`. A rota retornou `TOKEN_PLAN_STREAM_OK`,
`finish_reason=stop`, uma chamada, 18.752 tokens de entrada e 9 de saída, sem
ferramentas. Essa evidência fecha o gate de streaming da rota/modelo; os perfis
efetivos só podem herdá-la se mantiverem a mesma combinação de endpoint,
provider e modelo.

### Rollback dos perfis Flash

Antes de qualquer promoção, os perfis efetivos foram exportados para a área
privada do Hermes e restringidos a modo `0600`:

| Perfil | Arquivo privado | SHA-256 |
|---|---|---|
| Barclay | `barclay-before-token-plan-20260813.tar.gz` | `dfc9d1966f20dbbaeb26670607ea2981d8d3b637efb81323cabdb108f79d4418` |
| Rutherford | `rutherford-before-token-plan-20260813.tar.gz` | `a5eb7f8740294ff8fb0e4cf1b211a70d9d8166c656b31f43dfaa92bccfdc15ea` |
| O'Brien | `obrien-before-token-plan-20260813.tar.gz` | `e26ded6273ab04bad495434fc5f037650023e13cc53fa1276fc579d0e868038e` |

Cada arquivo foi importado sob um nome temporário e recuperou o modelo
`deepseek-v4-flash`, provedor `deepseek`, SOUL e skills do perfil correspondente.
As cópias temporárias foram removidas depois da verificação. Por desenho, o
export não inclui `.env`; um rollback depende do secret store já instalado e
deve confirmar autenticação antes do smoke. Os perfis efetivos permaneceram
inalterados durante a validação.

A verificação independente local repetiu `stat` e `sha256sum` para os três
arquivos e confirmou os modos e hashes registrados. O secret store confirmou
autenticação `deepseek` nos perfis efetivos e autenticação
`alibaba-coding-plan` nos três candidatos. O smoke pós-rollback continua
obrigatório, porque existência de credencial não comprova uma chamada válida.

### Rollout sequencial obrigatório

Promover um perfil por vez, na ordem Barclay → Rutherford → O'Brien. Para cada
perfil:

1. confirmar autenticação Token Plan e cota disponível no console;
2. aplicar juntos `deepseek-v4-flash-0731`, provider
   `alibaba-coding-plan`, endpoint Token Plan, ausência de fallback e
   `proxy.enabled=false`;
3. executar uma chamada textual curta e um tool-call somente leitura;
4. observar sessão, modelo, provider, `finish_reason`, tool arguments e Credits;
5. avançar somente após resultado aprovado e nenhuma cobrança pay-as-you-go;
6. em erro de autenticação, modelo, ferramenta, cota ou política, restaurar o
   backup individual, confirmar o secret store DeepSeek e executar smoke curto;
7. registrar a decisão antes de iniciar o perfil seguinte.

Não há fallback automático. Esgotamento de Credits deve falhar fechado; a
reserva DeepSeek direta permanece desligada e não participa deste rollout.

Tuvok revisou a evidência na sessão `20260813_220709_e764f4` e manteve a
promoção bloqueada até fechar streaming, proxy efetivo, Credits absolutos,
verificação dos backups/secret store e checkpoints. O custo estimado dessa
revisão foi `US$ 0,027030146`, abaixo do teto autorizado de `US$ 0,10`; custo
real não foi informado pelo provedor. Streaming, backups, autenticação e
checkpoints foram fechados depois desse parecer. Os valores absolutos de
Credits e o reset também foram registrados posteriormente, permitindo solicitar
a nova confirmação do revisor antes da promoção.

Tuvok realizou a revisão final somente leitura na sessão
`20260814_091803_fc725c` e emitiu **GO condicional**, sem bloqueadores
remanescentes. O revisor considerou fechados streaming, aplicação atômica de
`proxy.enabled=false`, backups e secret store, checkpoints, cota absoluta e
reset. O ledger local registrou seis chamadas de API, 61.343 tokens de entrada,
293.248 cacheados, 14.881 de saída e 11.860 de raciocínio, com custo estimado de
`US$ 0,040693699`, abaixo do teto autorizado de `US$ 0,10`; custo real não foi
informado pelo provedor.

O GO exige manter C1–C6 no ato do rollout: alteração atômica por perfil;
sequência Barclay → Rutherford → O'Brien; smoke textual e de ferramenta entre
perfis; reconfirmação da cota no console; rollback individual com smoke;
ausência de fallback e falha fechada; registro do GO de Tuvok e da decisão final
de Spock antes de avançar. O parecer cobre somente os três perfis Flash e não
aprova o piloto GLM-5.2.

Spock emitiu **GO restrito ao início de Barclay** na sessão
`20260814_145343_0a7a6d`. Antes da promoção, o owner reconfirmou no console,
atualizado às 15:03:56 BRT, plano ativo, 59,7% dos 2.500 Credits restantes e
reset em 2026-08-15 15:48:00 BRT. A tela de pay-as-you-go registrava gasto de
agosto em ¥0,00.

Barclay foi promovido atomicamente para `deepseek-v4-flash-0731`, provider
`alibaba-coding-plan`, endpoint do Token Plan e `proxy.enabled=false`, mantendo
o fallback vazio. O smoke textual passou na sessão
`20260814_150533_30a952`, com uma chamada e `finish_reason=stop`. O smoke de
ferramenta passou na sessão `20260814_150625_b3a474`: duas chamadas, uma tool
call `terminal` com argumento exato `{"command":"pwd"}`, resultado
`/workspace` e `finish_reason=stop`. As duas sessões registraram o modelo e o
provider esperados. O custo monetário local permaneceu desconhecido, como
esperado para Credits. Rutherford continua bloqueado até a reconfirmação
pós-Barclay de Credits e ausência de cobrança pay-as-you-go, seguida de nova
decisão de Spock.

No checkpoint pós-Barclay, atualizado às 15:17:30 BRT, o console manteve o
plano ativo e mostrou 59,6% dos 2.500 Credits restantes, reset ainda previsto
para 2026-08-15 15:48:00 BRT e pay-as-you-go de agosto em ¥0,00. A variação
observada desde o checkpoint prévio foi de 0,1 ponto percentual; devido ao
arredondamento do painel, ela não deve ser convertida em consumo exato. Essa
evidência fecha o checkpoint financeiro de Barclay, mas não autoriza Rutherford
sem nova decisão de Spock.

Spock emitiu **GO restrito ao início de Rutherford** na sessão
`20260814_151811_d78f8e`. O backup individual foi reconfirmado em modo `0600`
e com SHA-256 `a5eb7f8740294ff8fb0e4cf1b211a70d9d8166c656b31f43dfaa92bccfdc15ea`.
Rutherford foi promovido atomicamente para `deepseek-v4-flash-0731`, provider
`alibaba-coding-plan`, endpoint do Token Plan e `proxy.enabled=false`, mantendo
o fallback vazio.

O smoke textual de Rutherford passou na sessão `20260814_152126_661ea8`, com
uma chamada e `finish_reason=stop`. O smoke de ferramenta passou na sessão
`20260814_152258_e0de1e`: duas chamadas, uma tool call `terminal` com argumento
exato `{"command":"pwd"}`, resultado `/workspace` e `finish_reason=stop`.
As duas sessões registraram o modelo e o provider esperados. O'Brien permanece
bloqueado até a reconfirmação pós-Rutherford de Credits, plano/reset e
pay-as-you-go em ¥0,00, seguida de nova decisão de Spock.

No checkpoint pós-Rutherford, atualizado às 15:24:02–15:24:04 BRT, o console
manteve o plano ativo e mostrou 59,5% dos 2.500 Credits restantes, reset ainda
previsto para 2026-08-15 15:48:00 BRT e pay-as-you-go de agosto em ¥0,00. A
variação exibida desde o checkpoint anterior foi de 0,1 ponto percentual e
não deve ser convertida em consumo exato devido ao arredondamento do painel.
Essa evidência fecha o checkpoint financeiro de Rutherford, sem autorizar
O'Brien antes da nova decisão de Spock.

Spock emitiu **GO restrito ao início de O'Brien** na sessão
`20260814_152814_6bbe96`. O backup individual foi reconfirmado em modo `0600`
e com SHA-256 `e26ded6273ab04bad495434fc5f037650023e13cc53fa1276fc579d0e868038e`.
O'Brien foi promovido atomicamente para `deepseek-v4-flash-0731`, provider
`alibaba-coding-plan`, endpoint do Token Plan e `proxy.enabled=false`, mantendo
o fallback vazio.

O smoke textual de O'Brien passou na sessão `20260814_153113_3396f8`, com uma
chamada e `finish_reason=stop`. O smoke de ferramenta passou na sessão
`20260814_153156_6771eb`: duas chamadas, uma tool call `terminal` com argumento
exato `{"command":"pwd"}`, resultado `/workspace` e `finish_reason=stop`.
As duas sessões registraram o modelo e o provider esperados. Mesmo sendo o
último perfil, o rollout permanece aberto até a reconfirmação pós-O'Brien de
Credits, plano/reset e pay-as-you-go em ¥0,00, seguida da decisão formal de
fechamento por Spock.

No checkpoint pós-O'Brien, atualizado às 15:33:53 BRT, o console manteve o
plano ativo e mostrou 59,3% dos 2.500 Credits restantes, reset ainda previsto
para 2026-08-15 15:48:00 BRT e pay-as-you-go de agosto em ¥0,00. A variação
exibida desde o checkpoint anterior foi de 0,2 ponto percentual e não deve ser
convertida em consumo exato devido ao arredondamento do painel. Essa evidência
fecha o checkpoint financeiro de O'Brien e permite solicitar a decisão formal
de encerramento do rollout a Spock.

A primeira solicitação de fechamento, sessão Spock
`20260814_153505_9a6a63`, aprovou tecnicamente a execução dos três perfis, mas
reteve a declaração formal até reconciliar a documentação, os itens OpenSpec
comprovados e o grafo do projeto. Os itens 6.1, 6.4, 9.3, 9.4 e 9.5 foram
marcados como concluídos com base nas sessões e checkpoints acima. Os demais
itens continuam abertos quando tratam do modelo Pro, da reserva DeepSeek direta
ou de cobertura ainda não comprovada; eles não devem ser inferidos como
concluídos a partir deste rollout restrito aos três perfis Flash.

O grafo local foi reconstruído com `graphify update .`, resultando em 942 nós,
1.907 arestas e 66 comunidades em `graphify-out/graph.json`. A extração emitiu
aviso não bloqueante para sete arquivos SQL porque `tree_sitter_sql` não está
instalado.

As reavaliações Spock `20260814_153833_81c4f9` e
`20260814_154246_cfb328` mantiveram o veredito formal **NÃO CONCLUÍDO** apesar
de aprovarem tecnicamente o rollout. O bloqueio é de visibilidade do checkout:
as ferramentas do perfil foram executadas em um sandbox persistente contendo
`/workspace/agent-orchestrator`, branch `agent/ci-failure-drill`, HEAD
`69b8226bc844cc9a10bb2f9ab008e86835208084`, sem o diff deste workspace. Mesmo
com `--in` e `--no-restore-cwd`, o sandbox não expôs os artefatos reconciliados.
Assim, a execução operacional dos três perfis está aprovada, mas o fechamento
formal permanece pendente até Spock revisar o checkout correto. Nenhuma chamada
adicional foi feita aos perfis promovidos durante essas reavaliações.

### Candidato Tuvok Pro no Token Plan

Em 2026-08-14, a preparação da migração de Tuvok foi iniciada como gate
separado do rollout Flash. O perfil efetivo permaneceu em `deepseek-v4-pro` pelo
provider `deepseek`. Antes dos testes foi criado o backup privado
`tuvok-before-token-plan-20260814.tar.gz`, modo `0600`, SHA-256
`6e9c1f744f2fb7661b790cd1a431224fa780af875914c6158ee780c7a6a33435`.
A importação integral do arquivo foi recusada pelo Hermes por conter o membro
não suportado `tuvok/node/bin/corepack`; nenhum perfil parcial foi deixado. Em
seguida, o candidato isolado `tuvok-token-plan` foi criado pela clonagem nativa
de configuração, `.env`, SOUL e skills.

O candidato usa `deepseek-v4-pro`, provider `alibaba-coding-plan`, endpoint do
Token Plan, `proxy.enabled=false` e fallback vazio. A autenticação do provider
foi confirmada. A avaliação estruturada e de papel passou na sessão
`20260814_155507_05ca5a`: uma chamada, JSON válido, veredito `NO_GO`, os três
bloqueadores solicitados e escalonamento correto a Spock. O teste de ferramenta
passou na sessão `20260814_155610_3f97ae`: duas chamadas, uma tool call
`terminal` com argumento exato `{"command":"pwd"}`, resultado `/workspace` e
`finish_reason=stop`. O streaming foi habilitado temporariamente somente no
candidato e passou na sessão `20260814_155943_f0b42a`; depois, a preferência
original `streaming.enabled=false` foi restaurada. Todas as sessões registraram
modelo `deepseek-v4-pro` e provider `alibaba-coding-plan`.

Essa evidência ainda não promove Tuvok nem conclui o item OpenSpec 6.2. Antes da
troca efetiva ainda são obrigatórios o checkpoint de Credits/pay-as-you-go, a
revisão independente com teto autorizado, a decisão de Spock e, após eventual
promoção, novos smokes e checkpoint financeiro.

Tuvok realizou a revisão independente somente leitura na sessão
`20260814_160527_13d9b6`, sob teto autorizado de US$ 0,10, e emitiu **NO-GO**
até fechar validação de thinking/contexto/limite de output, rollback importável
com smoke, checkpoint financeiro e decisão de Spock. O ledger local das sessões
do candidato já registra 132 tokens de raciocínio na avaliação de papel, 68 no
smoke de ferramenta e 13 no smoke de streaming; as duas primeiras terminaram
com `finish_reason=stop`. Essas informações fecham a observabilidade básica de
thinking, mas não substituem os testes adicionais de contexto e output nem os
demais gates pedidos pelo revisor.

Os gates técnicos adicionais foram exercitados depois do NO-GO. A sessão
multi-turno `20260814_161043_17c62a` armazenou o nonce
`TUVOK-PRO-6E2-814` e o recuperou exatamente no turno retomado. No teste
controlado de output `20260814_161436_c9a0da`, `model.max_tokens=32` foi
aplicado temporariamente somente ao candidato; a mensagem persistida registrou
`finish_reason=length`, comprovando que o limite foi encaminhado e respeitado.
O Hermes tentou a continuação prevista pelo seu loop, mas foi interrompido por
`--max-turns 1`; em seguida, a configuração normal sem override foi restaurada.

Para comprovar o rollback, uma cópia do backup original foi sanitizada excluindo
somente o diretório de runtime `tuvok/node`, que continha os três symlinks não
aceitos pelo importador. O original permaneceu intacto. A cópia importável foi
armazenada como `tuvok-before-token-plan-20260814-sanitized.tar.gz`, modo
`0600`, SHA-256
`f5d2266c6d837339ceb5ea4a7095cc770b9782cc9e73b007ebaf537d6329220e`.
Ela foi importada como `tuvok-rollback-test` e restaurou
`deepseek-v4-pro`/`deepseek`, `proxy.enabled=false`, fallback vazio,
autenticação DeepSeek válida e SOUL com SHA-256 idêntico ao perfil efetivo. O
smoke da rota restaurada passou na sessão `20260814_161744_33e47b`, retornando
`TUVOK_DEEPSEEK_ROLLBACK_OK`. O perfil temporário foi mantido durante a revisão
independente da evidência e removido depois do fechamento; os dois backups e o
candidato `tuvok-token-plan` foram preservados.

No checkpoint financeiro anterior à segunda revisão, atualizado às 16:36:22
BRT, o console registrou plano ativo, 54,4% dos 2.500 Credits restantes, reset
em 2026-08-15 15:48:00 BRT e pay-as-you-go de agosto em ¥0,00. O owner
autorizou uma segunda e última revisão Tuvok com teto de US$ 0,10.

Tuvok concluiu a segunda e última revisão independente na sessão
`20260814_163945_53ddd8` e emitiu **GO condicional**, sem bloqueadores técnicos
remanescentes. O parecer considerou fechados thinking, contexto multi-turno,
limite de output, rollback importável com smoke e checkpoint financeiro. A
promoção ficou condicionada à decisão prévia de Spock, aplicação atômica,
reconfirmação do console imediatamente antes da troca, smokes no perfil
efetivo, checkpoint financeiro posterior e registro final. O custo real da
sessão não foi informado pelo provedor; o teto autorizado foi US$ 0,10.

Spock emitiu **GO condicional para a promoção do Tuvok** na sessão
`20260814_164326_cdbfb6`. A autorização é restrita à troca atômica do perfil
efetivo para `deepseek-v4-pro`/`alibaba-coding-plan`, endpoint do Token Plan,
`proxy.enabled=false`, fallback vazio e `streaming.enabled=false`. Exige nova
leitura do console imediatamente antes da troca, smokes textual e `pwd`,
checkpoint financeiro posterior e rollback imediato pela cópia sanitizada em
qualquer divergência. O GO não autoriza fallback, reserva DeepSeek automática,
outros perfis, Git ou expansão de escopo.

Imediatamente antes da promoção, o console atualizado às 16:51:47–16:51:48
BRT manteve plano ativo, 54,4% dos 2.500 Credits restantes, reset em
2026-08-15 15:48:00 BRT e pay-as-you-go de agosto em ¥0,00. O perfil efetivo
Tuvok foi então promovido atomicamente para `deepseek-v4-pro`, provider
`alibaba-coding-plan`, endpoint do Token Plan, `proxy.enabled=false`, fallback
vazio e `streaming.enabled=false`.

O smoke textual pós-promoção passou na sessão `20260814_165402_aa7a6f`, com
uma chamada, modelo/provider esperados, 150 tokens de raciocínio e
`finish_reason=stop`. O smoke de ferramenta passou na sessão
`20260814_165438_6122e0`: duas chamadas, 110 tokens de raciocínio, uma tool
call `terminal` com argumento exato `{"command":"pwd"}`, resultado
`/workspace` e `finish_reason=stop`. Com a validação do Pro nas duas rotas e a
cobertura de thinking, ferramenta, JSON, streaming, contexto e limite de output,
os itens OpenSpec 6.2 e 6.3 foram reconciliados como concluídos. A migração
ainda aguarda o checkpoint financeiro pós-promoção antes da declaração final.

O checkpoint financeiro pós-promoção, atualizado às 17:11:56 BRT, confirmou
plano ativo, 52,7% dos 2.500 Credits restantes, reset ainda previsto para
2026-08-15 15:48:00 BRT e pay-as-you-go de agosto em ¥0,00. A variação do
painel desde o checkpoint imediatamente anterior foi de 1,7 ponto percentual;
como a tela possui somente uma casa decimal, ela não deve ser convertida em
consumo exato. Não houve cobrança direta nem mudança de billing. Com os smokes,
o checkpoint posterior e os gates de Tuvok e Spock aprovados, a migração do
perfil efetivo Tuvok para o QwenCloud Token Plan está operacionalmente
concluída. A API DeepSeek direta permanece disponível apenas como rollback
manual comprovado, sem fallback automático.

Spock realizou o fechamento formal consolidado na sessão
`20260814_171900_5feb6a` e declarou **ROLLOUT CONCLUÍDO** para o escopo restrito
de Barclay, Rutherford, O'Brien e Tuvok. O revisor leu integralmente e confirmou
por SHA-256 as cópias montadas deste documento, das tarefas OpenSpec e do
relatório Graphify, contornando o checkout persistente antigo sem sincronizá-lo
ou alterá-lo. Nenhuma chamada foi feita aos perfis promovidos nessa revisão.

O Graphify mais recente registra 943 nós, 1.908 arestas e 68 comunidades; esses
valores substituem a reconstrução intermediária de 942 nós, 1.907 arestas e 66
comunidades. O aviso conhecido pela ausência de `tree_sitter_sql` permanece
não bloqueante para este rollout, mas limita a cobertura estrutural dos sete
arquivos SQL. Este fechamento não conclui toda a mudança
`add-deepseek-technical-reserve`, não habilita reserva automática e não aprova o
piloto GLM-5.2.

## Controles financeiros sugeridos para o piloto

- US$ 0,25/dia na DeepSeek direta;
- US$ 2,00/mês;
- uma chamada por grant e uma reserva por tarefa;
- custo máximo por chamada definido na aprovação;
- kill switch global e habilitação por perfil desligados por padrão.

Os valores são sugestão e exigem aprovação antes da implementação.

## Situação atual

O adaptador rejeita fallback Hermes configurado. Isso permanece correto até a
mudança `add-deepseek-technical-reserve` implementar classificação, grants,
orçamentos, ledger, testes, modo shadow e rollout controlado.

A primeira etapa segura foi implementada:

- rotas e modelos tipados, com variantes Flash distintas;
- modos `off`, `shadow` e `enforced`;
- padrão `off` com kill switch ativo;
- habilitação por perfil e budgets obrigatórios no modo `enforced`;
- uma chamada por grant e uma tentativa por tarefa como invariantes;
- allowlist pura de falhas elegíveis, sem integração de rede;
- estados `reserve_required` e `reserve_denied` em modo shadow;
- solicitação limitada a metadados públicos de roteamento, sem prompt;
- mensagens brutas do provider substituídas por razões normalizadas;
- kill switch impede inclusive a criação da solicitação shadow.

Grants persistentes de uso único e a migration `0003` foram implementados em
código. O consumo exige escopo exato, validade, status aprovado e custo dentro
do teto. Revogação e aprovador ficam auditáveis.

O guard financeiro direto também possui uma fundação fail-closed. Ele exige
snapshot de saldo disponível, soma conservadoramente o teto dos grants já
consumidos e valida limites diário e mensal na timezone operacional. Logo antes
do consumo, os dois limites locais são recalculados dentro da mesma transação
PostgreSQL. Um advisory lock transacional serializa compromissos concorrentes;
se outro processo consumir orçamento entre o primeiro snapshot e o grant, a
segunda validação bloqueia a operação sem consumir o grant.

Isso ainda não habilita a reserva real. Já existem um leitor autenticável de
`GET /user/balance` com transporte injetável, um estimador conservador, ledger
de compromisso/reconciliação e um executor de chamada única exercitado somente
com provider falso. O saldo USD é obrigatório; endpoint, schema ou evidência
inválidos falham fechados e as mensagens normalizadas não carregam a chave.

O snapshot de preços `official-2026-08-12` usa cache miss para estimar o custo
máximo. A reconciliação separa input com cache hit, input com cache miss e
output. Flash usa US$ 0,0028 / US$ 0,14 / US$ 0,28 por milhão; Pro usa
US$ 0,003625 / US$ 0,435 / US$ 0,87. O snapshot é deliberadamente fixo porque a
DeepSeek avisa que os preços podem mudar; modelo sem preço conhecido bloqueia a
reserva em vez de adotar uma tarifa nova silenciosamente.

O nó LangGraph `deepseek_reserve` executa imediatamente depois de
`reserve_approved`, sem aresta de retorno à rota primária. O consumo do grant e
o compromisso de custo máximo agora compartilham uma transação: falha em uma
parte desfaz ambas antes de qualquer provider. O executor permite uma única
chamada e reconcilia o custo efetivo. Timeout ou resultado ambíguo muda o
registro para `outcome_unknown` e não faz retry.

O provider HTTP de Chat Completions também possui implementação com transporte
POST injetável, endpoint fixo, streaming desligado e allowlist dos dois modelos.
URL, headers, thinking, limite de output, parsing de usage e resposta foram
exercitados inteiramente com transporte falso. Ele não está no bootstrap e
nenhuma chamada externa foi realizada. A reconciliação manual de resultado
ambíguo agora aceita, uma única vez, `confirmed_charged` com usage completo ou
`confirmed_not_charged` com custo e tokens zero. Operador, decisão e referência
não sensível de evidência ficam auditáveis pela migration `0005`.

Ainda faltam configuração segura de segredo e smoke test autorizado. O saldo externo pode mudar
fora deste orquestrador; por isso continua sendo evidência adicional, nunca
substituto dos tetos locais serializados.

As migrations `0003`–`0005` ainda não foram aplicadas no homelab. Também não
existem configuração de chave, provider no runtime ou chamada real. A transição interna
`reserve_approved` consome somente grant de escopo exato em modo `enforced`, mas
não está ligada ao bootstrap/API e não deve receber grants reais até existir o
nó de execução na mesma invocação. Nenhuma API key da reserva foi adicionada.

### Validação da persistência

Em PostgreSQL 16 efêmero e isolado, as migrations `0001`–`0003` foram aplicadas
em ordem. Um grant aprovado foi consumido pela instrução de escopo completo: o
primeiro consumo retornou uma linha, o estado persistido ficou `consumed` e a
segunda tentativa retornou zero linhas. O contêiner foi removido depois do
teste; nenhum banco do homelab foi alterado.

A transação de orçamento também foi validada em PostgreSQL 16 efêmero. Com teto
diário de US$ 0,05, o primeiro grant comprometeu US$ 0,04 e o segundo grant de
US$ 0,04 foi bloqueado pela revalidação transacional, sem consumo. Em uma
segunda instância efêmera, a migration `0004` persistiu um compromisso e sua
reconciliação de tokens/custo. A migration `0005` e uma reconciliação manual
cobrada também foram validadas em PostgreSQL efêmero. A suíte local completa
terminou com 106/106 testes aprovados. Os contêineres efêmeros foram removidos.

O procedimento de primeiro teste está em
`docs/deepseek-reserve-smoke-runbook.md`. Seu status é não autorizado: define
gates e rollback, mas não aplica migrations nem permite chamada paga.

## Referências oficiais

Consultadas em 2026-08-12:

- [QwenCloud Token Plan Individual](https://docs.qwencloud.com/token-plan/personal/token-plan-personal-overview)
- [Índice completo da documentação QwenCloud](https://docs.qwencloud.com/llms.txt)
- [DeepSeek — modelos e preços](https://api-docs.deepseek.com/quick_start/pricing/)
- [DeepSeek — consulta de saldo](https://api-docs.deepseek.com/zh-cn/api/get-user-balance)
- [DeepSeek — códigos de erro](https://api-docs.deepseek.com/quick_start/error_codes/)

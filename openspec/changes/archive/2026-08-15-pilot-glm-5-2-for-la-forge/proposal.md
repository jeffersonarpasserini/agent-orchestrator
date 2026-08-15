# Why

O perfil `la-forge` executa as tarefas de engenharia mais complexas, mas hoje
compartilha `qwen3.8-max` com outros implementadores. O Token Plan Individual já
inclui `glm-5.2`, modelo com contexto longo, raciocínio e function calling, o que
permite avaliar uma família independente para trabalho full stack de longa
duração sem contratar outro provedor.

A troca não pode ser feita apenas alterando o ID do modelo: o GLM exige
tratamento compatível de thinking e `tool_stream`, e o plano Lite limita o uso a
2.500 Credits por janela de sete dias e 1–2 agentes concorrentes.

# What Changes

- Criar um candidato isolado de `la-forge` com `glm-5.2` no endpoint do Token
  Plan Individual, sem fallback.
- Validar autenticação, resposta simples, saída estruturada, sessão e function
  calling antes de qualquer promoção.
- Comparar GLM-5.2 com o baseline `qwen3.8-max` em uma tarefa full stack
  representativa e previamente aprovada.
- Promover `glm-5.2` para `la-forge` somente se os gates funcionais, de
  segurança, qualidade e consumo forem satisfeitos.
- Preservar Spock como decisor final e Tuvok como revisor independente.
- Manter rollback explícito para `qwen3.8-max` e impedir fallback automático ou
  cobrança pay-as-you-go.

# Impact

A mudança afeta a configuração do perfil `la-forge`, a compatibilidade do
adaptador Hermes com parâmetros específicos do GLM, avaliações de perfil e
documentação do inventário. Não autoriza alteração imediata do perfil efetivo,
commit, push, deploy, execução autônoma ou uso da chave do Token Plan em backend
ou processamento batch.

# Revisão dos nós isolados do Graphify

Data: 2026-08-14

## Parser SQL

O extra SQL foi instalado no ambiente isolado da ferramenta, sem alterar as
dependências do Agent Orchestrator:

```bash
/home/jeffersonpasserini/.hermes/tools/graphify/bin/python -m pip install \
  "graphifyy[sql]==0.9.36"
graphify update .
```

Versões verificadas:

- `graphifyy 0.9.36`;
- `tree-sitter-sql 0.3.11`.

O reprocessamento terminou sem o aviso de dependência SQL ausente. O grafo
passou de 1.035 para 1.042 nós, incorporando os sete arquivos em `migrations/`.

## Classificação dos nós de baixa conectividade

A inspeção calculou o grau diretamente a partir de `nodes` e `links` em
`graphify-out/graph.json`.

### Grau zero

| Grupo | Quantidade | Classificação | Justificativa |
|---|---:|---|---|
| `migrations/*.sql` | 7 | relacionamento ausente no extrator | O parser reconhece os arquivos, mas esta versão não materializa tabelas, índices, FKs ou a sequência de migrations como nós e arestas. O runtime aplica a ordem fora do SQL estático. |
| `src/orchestrator/**/__init__.py` vazios | 3 | falso positivo esperado | São marcadores de pacote sem símbolos ou imports. |
| raiz de `pyproject.toml` | 1 | falso positivo esperado | É um nó de arquivo de configuração; as dependências não são representadas como arestas pelo extrator atual. |

### Grau um

Os nós de grau um são predominantemente símbolos folha, headings de Markdown,
cenários OpenSpec e rationale nodes ligados ao respectivo arquivo ou seção.
Baixa conectividade é esperada nesses tipos e não indica, isoladamente, código
ou documentação inacessível.

## Decisão

- o bloqueio de instalação do parser SQL está resolvido;
- nenhum relacionamento ausente exige alteração no runtime;
- a ausência de relações semânticas internas nos sete SQLs é uma limitação
  conhecida do extrator `graphifyy 0.9.36`, não perda de execução das migrations;
- uma futura versão do Graphify pode reprocessar o corpus e substituir esta
  classificação quando passar a extrair objetos PostgreSQL e suas relações.

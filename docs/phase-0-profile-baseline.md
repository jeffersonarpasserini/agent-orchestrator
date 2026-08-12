# Baseline não secreto dos perfis Hermes

Data: 2026-08-10 (America/Sao_Paulo)

Inventário obtido com `hermes profile list`. Não contém arquivos `.env`,
credenciais, tokens, endpoints privados, sessões ou prompts.

| Perfil | Modelo | Gateway | Alias |
|---|---|---|---|
| `default` | `gpt-5.6-sol` | parado | — |
| `alfred` | `gpt-5.6-sol` | rodando | `alfred` |
| `bashir` | `gpt-5.6-terra` | parado | `bashir` |
| `crusher` | `gpt-5.6-sol` | parado | `crusher` |
| `data` | `qwen3.8-max` | parado | `data` |
| `la-forge` | `gpt-5.6-terra` | parado | `la-forge` |
| `obrien` | `gpt-5.6-terra` | parado | `obrien` |
| `seven` | `gpt-5.6-sol` | parado | `seven` |
| `spock` | `gpt-5.6-sol` | rodando | `spock` |
| `troi` | `gpt-5.6-terra` | parado | `troi` |
| `tuvok` | `deepseek-v4-pro` | parado | `tuvok` |
| `uhura` | `gpt-5.6-luna` | parado | `uhura` |

O baseline esperado contém 12 perfis. Modelo e alias devem ser comparados antes
e depois da Fase 5. O estado dos gateways é transitório. O backup completo
permanece criptografado no Kopia e separado deste inventário.

# Design: governança da equipe de agentes

## Decisões

O catálogo será código imutável e tipado. Cada perfil declara função,
responsabilidades e autoridades explícitas. A ausência de uma autoridade no
catálogo é tratada como negação.

O workflow de specs preserva quatro perspectivas e uma ordem determinística:

1. Seven pesquisa alternativas e lacunas;
2. Troi valida intenção, escopo e critérios de aceite;
3. B'Elanna valida viabilidade técnica e propõe alterações;
4. Spock consolida e decide a versão final.

La Forge lidera a frente tecnicamente mais complexa e pode trabalhar em
paralelo com B'Elanna, Barclay, Data e outros especialistas. Contratos, schema
e arquitetura compartilhados exigem coordenação e continuam submetidos a
Spock.

Alfred produz pedidos de relatório como artefatos declarativos. Criar esse
artefato não executa a tarefa solicitada e nunca incorpora autoridades
materiais.

## Segurança

- endpoints são somente leitura;
- pedidos de relatório retornam `report_only=true`;
- autoridades materiais são allowlists explícitas;
- perfis auxiliares do Token Plan não são tratados como novos agentes;
- nenhuma credencial ou conteúdo privado de prompt integra o catálogo.

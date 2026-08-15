# 1. Descoberta

- [x] 1.1 Inventariar CPU, memória, disco, portas e redes disponíveis
- [x] 1.2 Definir fontes iniciais, atributos permitidos e política de retenção
- [x] 1.3 Fixar versão e revisar release notes, licença e vulnerabilidades

# 2. Implementação isolada

- [x] 2.1 Adicionar OpenObserve single-node com volume e credenciais próprios
- [x] 2.2 Adicionar OpenTelemetry Collector com healthcheck e limites
- [x] 2.3 Configurar redaction e fan-out para Phoenix e OpenObserve
- [x] 2.4 Manter portas em loopback e redes com privilégio mínimo

# 3. Validação

- [x] 3.1 Validar traces nos dois backends sem duplicação no produtor
- [x] 3.2 Ingerir logs e métricas por etapas e medir recursos
- [x] 3.3 Confirmar ausência de segredos e dados sensíveis
- [x] 3.4 Criar dashboards e healthcheck no Uptime Kuma
- [x] 3.5 Testar backup, restauração e rollback
- [ ] 3.6 Comparar OpenObserve e Phoenix durante ao menos uma semana

# 4. Decisão

- [x] 4.1 Registrar evidências e riscos residuais
- [ ] 4.2 Decidir manter ambos, consolidar ou remover OpenObserve
- [x] 4.3 Avaliar HA somente em uma mudança OpenSpec posterior

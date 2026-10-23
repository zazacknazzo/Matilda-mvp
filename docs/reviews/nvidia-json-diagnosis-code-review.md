# Revisão NVIDIA JSON (#31 / PR #32)

Base fixa: `88fdde76d1ebbdb64c509c427375dd458768da7d`.
Head de implementação: `4d3836f`.
Diff: `git diff 88fdde76d1ebbdb64c509c427375dd458768da7d...4d3836f`.
Commit: `4d3836f fix(studio): diagnose NVIDIA JSON failures and request strict lesson output (#31)`.

Revisores independentes, somente leitura, em checkouts/branches separados:
review/nvidia-json-standards e review/nvidia-json-spec. Especificação: pedido do
usuário para investigar o terceiro smoke e a proposta na
[Issue #31](https://github.com/zazacknazzo/Matilda-mvp/issues/31#issuecomment-6355204276).
Nenhum revisor editou arquivos ou executou inferência real.

## Standards

**0 achados** no diff `88fdde7...4d3836f`.

Não identifiquei violações documentadas nem smells relevantes. Consultei AGENTS.md,
README, arquitetura, contratos Studio e instruções de issue/domain.

O decoder concentra as classificações sem expor chaves, valores ou mensagens do
parser. A telemetria distingue envelope e conteúdo e limita finish_reason a
valores conhecidos. O schema privado permanece integral; contratos públicos,
Gemini, autoridade científica, revisão e deadlines são preservados.

A documentação distingue corretamente a declaração de strict no endpoint
hospedado da eficácia ainda não comprovada em inferência real.

Validação independente: **51 testes focados passaram**; checkout permaneceu limpo.
Nenhuma inferência real ou operação GitHub.

Limitações: aviso existente Starlette/HTTPX. A revisão não certifica compilação do
schema NVIDIA nem qualidade pedagógica; ambos continuam como gates documentados.

## Spec

**0 achados** no diff `88fdde7...4d3836f`.

A implementação distingue sintaxe, duplicidade, raiz não objeto, constantes não
JSON e limites adicionais, separando envelope, conteúdo e validação Pydantic.
Os diagnósticos não incorporam conteúdo ou mensagens livres.

O contrato compact-v2-weighted, a geração de 50 minutos, a revisão persistida e a
autoridade científica permanecem preservados. O schema transmitido mantém seus
campos e restrições; strict=true fica limitado à geração NVIDIA, com origem
documental e limitações explicitadas. Não há reparo de JSON nem aceitação parcial.

A documentação trata corretamente a causa específica do smoke como desconhecida
e não apresenta a ativação de strict como correção real comprovada.

Validação independente: **51 testes focados passaram**, incluindo as categorias
solicitadas, preservação da revisão, ausência de publicação inválida, expansão
válida, persistência, replay, Markdown e teto de uma chamada. Checkout limpo;
nenhuma inferência real.

A coleta final do Playwright e a publicação do PR/Issue permanecem sob
responsabilidade do agente principal.

Standards: 0 achados, nenhum problema pendente nesse eixo. Spec: 0 achados,
nenhum problema pendente nesse eixo.

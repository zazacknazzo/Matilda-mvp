# Revisão independente — âncoras canônicas (#31 / PR #32)

Base fixa: `6816c30a03110e604a63d84af5f41a3cae50cd24`, cabeça anterior do PR #32.
Diff: `git diff 6816c30...79e4d62`. Commit: `79e4d62`.

Revisões somente leitura em checkouts e branches separados:
`review/nvidia-standards` e `review/nvidia-spec`. Nenhuma inferência real.
Standards consultou instruções, README, arquitetura, método científico e baseline
Fowler. Spec confrontou o pedido de âncoras canônicas do usuário, sem supor o
conteúdo da resposta RNA original.

## Standards

**0 achados**: nenhuma violação documentada ou heurística Fowler relevante.

A seleção privada de IDs mantém o SourceAnchor público e a autoridade científica
existentes. Relações entre contribuição, conceito, evidência e documento são
verificadas antes da persistência. A alteração compartilhada em
editorial_alias_spans preserva a escolha inicial de editorial_alias_quote; os
trechos continuam literais. Diagnósticos extraem somente subcódigos permitidos,
sem conteúdo das exceções. Limites e segurança do provedor foram preservados.

Revisão estática; o revisor Standards não reexecutou as suítes.

## Spec

**0 achados abertos.** A fronteira privada recebe somente uma seleção autorizada;
o servidor constrói SourceAnchor literal e valida vínculos. IDs permanecem
estáveis nas tentativas da operação e são rejeitados em outra operação. API
pública e validações foram preservadas.

O revisor Spec reexecutou **31 testes**, todos aprovados: âncoras e diagnóstico,
RNA, CRISPR, Unicode, repetições, múltiplos documentos, ausência de cobertura e
seleções incompatíveis. A documentação distingue a causa estrutural reproduzida
do componente específico desconhecido na resposta RNA original. Confirmação no
endpoint real permanece pendente; testes controlados não comprovam sucesso live.

Standards: **0 achados**, sem gravidade aberta; Spec: **0 achados**, sem gravidade
aberta. Evidência consolidada: [relatório da correção](../studio-canonical-anchors.md).

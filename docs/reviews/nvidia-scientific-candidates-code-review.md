# Revisão independente — candidatos científicos (#31 / PR #32)

Base fixa: `32562f5c7d28cbabe5aa6bb0a635bf49ff5e8309`, versão anterior do PR #32.
Diff: `git diff 32562f5...a1dde5c`. Commit revisado: `a1dde5c`.

Revisores em checkouts/branches separados, somente leitura:
`review/nvidia-standards` e `review/nvidia-spec`. Nenhuma inferência real.
Standards consultou instruções do projeto, arquitetura, metodologia e baseline
Fowler. Spec confrontou os dez requisitos e testes do pedido atual do usuário.

## Standards

**0 achados.** Nenhuma violação documentada ou heurística Fowler relevante.

ScientificCandidate reúne os campos científicos que devem permanecer associados.
O serviço resolve a seleção e mantém a validação de autoridade antes da
persistência. A compactação preserva documentos completos, afirmações canônicas
e contratos públicos.

O bloqueio corretivo mantém o teto e registra somente diagnóstico sanitizado.
A medição distingue bytes do payload, estimativa conservadora e uso real relatado,
sem apresentar redução de bytes como economia comprovada de tokens NVIDIA.

Revisão estática, sem alterações, reexecução de suítes ou chamadas externas.
Aceitação do schema e sucesso completo em produção dependem do smoke autorizado.

## Spec

**0 achados abertos.** O modelo seleciona somente candidate_id; o servidor resolve
contribuição, conceito, evidências e âncora como associação única. IDs desconhecidos
ou de outra operação recebem diagnóstico específico, sem substituição automática.
Campos científicos livres são rejeitados, e a autoridade pública permanece
validada antes da persistência.

A compactação conserva documentos completos e afirmações canônicas. O contador
conservador e o teto 12.000 permanecem intactos. A tentativa corretiva acima do
limite preserva diagnóstico anterior e estado salvo, sem novo HTTP.

O revisor reexecutou **37 testes focados**, todos aprovados, sem chamadas reais.
A documentação distingue medição offline de inferência NVIDIA; o sucesso do fluxo
atualizado no endpoint real permanece pendente.

Standards: **0 achados**, sem gravidade aberta; Spec: **0 achados**, sem gravidade
aberta. [Evidências da implementação](../studio-scientific-candidates.md).

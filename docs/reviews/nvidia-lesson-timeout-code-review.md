# Revisão independente — geração NVIDIA (#31 / PR #32)

Base fixa indicada na evidência: `394d109c7337dbe8f55c35b6ad70538908ae1bd6`.
Diff principal: `git diff 394d109...8a7306b`.
Incremento: `git diff 8a7306b..fcccf1d` (cache fechado no smoke).

Checkouts/branches separados, somente leitura: review/nvidia-standards e
review/nvidia-spec. Standards consultou padrões do projeto e baseline Fowler;
Spec confrontou o pedido atual do usuário. Nenhum revisor executou inferência real.

## Standards

**0 achados** no principal e **0 adicionais** no incremento; nenhuma violação
documentada ou heurística Fowler relevante.

A elaboração compacta fica no adapter NVIDIA e é expandida para o LessonDraft
original antes das validações centrais. Duração, objetivos, evidências, revisão e
persistência continuam verificados. Cancelamento tem telemetria sanitizada e é
propagado. O smoke marca preparação simulada, limita a inferência a uma chamada
e mantém resposta/validação/persistência reais na aula. Fixtures de aula ficam
somente nos testes e na medição offline.

O preflight usa o armazenamento existente, exige margem de validade e falha
antes da preparação externa se o cache não serve. O teste verifica zero chamadas
pela fronteira HTTP controlada. Revisão estática, sem reexecutar suítes.

## Spec

**0 achados abertos** no principal e no incremento.

O contrato preserva seções/slides/atividades, duração, objetivos e evidências.
A expansão passa pelo LessonDraft e pelos validadores científicos. Cancelamentos
registram fase/motivo, distinguindo timeout de indisponibilidade. O smoke identifica
a preparação simulada, limita NVIDIA a uma inferência e verifica persistência,
replay e Markdown. A documentação explica 70 s e distingue hipóteses de fatos,
sem prometer ganho live.

Spec reexecutou **50 testes focados**, todos aprovados no commit principal.
Sugeriu como robustez recusar preparação sem cache fresco. A sugestão foi aplicada
com teste vermelho/verde pelo responsável. O incremento foi revisado por leitura
do diff, sem reexecução pelo revisor; o responsável executou o teste novo e o
backend completo final (670 aprovados).

Standards: **0 achados pendentes**, sem gravidade aberta; Spec: **0 achados
pendentes**, sem gravidade aberta. Uma sugestão de robustez foi aplicada.
[Relatório de evidência e limitações](../studio-nvidia-lesson-timeout.md).

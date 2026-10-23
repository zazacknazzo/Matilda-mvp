# UI/UX — revisão de código

22/10/2026. Base fixa: `a88698efc34cc03d9c03de3fc4cd1e74922c28fb`.
Revisão em dois agentes independentes conforme `.agents/skills/code-review`.
Diff inicial: `git diff a88698e...14b7abe`; correções em `c80f17a`, `56737c3`
e no commit final de validação. Nenhum comentário externo foi publicado.

## Standards

Confirmado: as condições de `generation-primary` são mutuamente exclusivas,
com prioridade para abrir a aula salva.

Sombra, cascata, padding de evidência e destaque por estado estão corrigidos.
**Zero achados Standards abertos.**

Achados tratados: token de sombra originalmente inválido; estilo genérico do
host prevalecia sobre a ação de geração; shorthand removia o recuo das fontes;
estado de reconciliação podia destacar duas ações simultaneamente. Tokens e
seletores explícitos preservam os estados no host e nos harnesses.

## Spec

Confirmado: ambos os achados estão resolvidos. A revisão mobile preserva a
ordem visual e do DOM, sem `order: 2`; a elevação do slide usa o token semântico
válido. Hierarquia das ações e recuo da evidência permanecem no escopo de
refinamento solicitado. **Zero achados Spec abertos; dois resolvidos.**

Foi acrescentada uma regressão de teclado no fluxo real: Tab a partir do atalho
passa pelo material e pela sugestão sem saltar milhares de pixels para trás.
Passou em 1440, 768 e 375 px. A suíte de revisão foi repetida após a correção.

**Resultado:** Standards 0 abertos; Spec 0 abertos. Ensaio humano, leitor de tela
e projetor físico continuam fora da evidência automatizada deste ambiente.

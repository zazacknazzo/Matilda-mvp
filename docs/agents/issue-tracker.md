# Issue tracker: GitHub

Especificações e tickets deste projeto ficam no GitHub Issues de
`zazacknazzo/Matilda-mvp`. Use a CLI `gh`.

## Convenções

Execute os comandos no checkout do projeto. Use
`--repo zazacknazzo/Matilda-mvp` para explicitar o destino.

- Ler uma issue e sua discussão:
  `gh issue view <numero> --comments`
- Consultar campos estruturados:
  `gh issue view <numero> --json number,title,body,labels,assignees,comments`
- Listar issues abertas:
  `gh issue list --state open --json number,title,labels,assignees`
- Criar uma issue:
  `gh issue create --title "..." --body-file <arquivo.md>`
- Atualizar a descrição:
  `gh issue edit <numero> --body-file <arquivo.md>`
- Comentar:
  `gh issue comment <numero> --body-file <arquivo.md>`
- Atribuir um responsável:
  `gh issue edit <numero> --add-assignee <usuario>`
- Aplicar ou remover labels existentes:
  `gh issue edit <numero> --add-label "..."`
  ou `gh issue edit <numero> --remove-label "..."`
- Encerrar:
  `gh issue close <numero>`

Para textos com várias linhas, prepare um arquivo e use `--body-file`.

## Conteúdo e coordenação

Especificações registram o problema, comportamento esperado, escopo e
critérios de aceite. Tickets de implementação apontam para a especificação,
quando houver, e identificam responsável, dependências e área afetada.

Consulte issues existentes antes de criar outra para o mesmo trabalho.
Para tarefas paralelas, registre sobreposições e dependências na issue.

## Pull requests como entrada de triagem

PRs as a request surface: no.

## Quando uma skill pedir publicação no rastreador

Crie uma GitHub issue conforme o escopo autorizado da tarefa.

## Quando uma skill pedir o ticket relevante

Leia a issue com `gh issue view <numero> --comments` e consulte seus
campos estruturados quando precisar de labels ou responsáveis.

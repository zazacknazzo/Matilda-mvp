# Instruções para agentes — Matilda

## Escopo do projeto

O Matilda inclui Forensics e Studio. O Forensics já está implementado e deve
ser preservado. O Studio será desenvolvido conforme o PRD v4.0; consulte esse
PRD antes de especificar ou implementar funcionalidades do Studio.

## Documentação do projeto

Leia `README.md` para execução e validação.
Antes de alterar a arquitetura ou contratos, leia `docs/architecture.md`.
Para mudanças em evidências, catálogo ou interpretação científica, leia
`docs/research-methodology.md` e, quando envolver descoberta automática,
`docs/automatic-catalog.md`.

Preserve a arquitetura existente ao executar tarefas de escopo limitado.
Propostas de mudança arquitetural devem explicitar a motivação e os impactos.

## Trabalho paralelo — quatro integrantes

- Cada tarefa deve ter um integrante responsável, escopo definido e critérios
  de aceite na issue correspondente.
- Cada integrante deve trabalhar em branch própria e checkout separado
  (clone ou git worktree), com sessão Codex dedicada.
- Antes de editar, confira o estado do Git e identifique os arquivos afetados.
  Preserve alterações que já existam no checkout.
- Distribua tarefas por arquivos e responsabilidades. Quando houver
  sobreposição, combine a sequência de integração antes de editar.
- Contratos compartilhados — API, schemas Pydantic, tipos TypeScript e
  estruturas de dados — não podem ser alterados unilateralmente por agentes
  trabalhando em paralelo. Antes de editar, registre a proposta e os impactos
  na issue e obtenha acordo explícito dos responsáveis pelas tarefas afetadas,
  incluindo a sequência de integração e a compatibilidade necessária.
- Entregue mudanças por pull request vinculada à issue, informando o que mudou,
  a validação realizada e as limitações conhecidas.
- Antes da integração, outro integrante deve revisar a alteração. Execute
  as verificações pertinentes descritas no README.

## Agent skills

### Issue tracker

Especificações e tickets ficam no GitHub Issues de
`zazacknazzo/Matilda-mvp`. Antes de operar sobre eles, leia
`docs/agents/issue-tracker.md`.

### Domain docs

Layout single-context: `CONTEXT.md` na raiz e ADRs em `docs/adr/`.
Antes de explorar o domínio, leia `docs/agents/domain.md`.

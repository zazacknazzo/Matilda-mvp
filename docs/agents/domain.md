# Documentação de domínio

## Layout

Este repositório usa single-context:

- `CONTEXT.md` na raiz: vocabulário e definições do domínio.
- `docs/adr/`: registros de decisões arquiteturais.

Backend e frontend pertencem ao mesmo contexto de domínio.

## Antes de explorar o domínio

Leia `CONTEXT.md`, quando existir, e os ADRs relacionados à área da tarefa.

Se esses arquivos não existirem, prossiga silenciosamente. A ausência
não exige criar documentos nem impede o trabalho. A skill
`domain-modeling` pode criá-los conforme termos e decisões forem resolvidos.

A configuração das skills fica em `docs/agents/`. A documentação técnica
existente permanece nos seus caminhos atuais, referenciados em `AGENTS.md`.

## Vocabulário

Use os termos definidos em `CONTEXT.md` ao nomear conceitos em issues,
propostas, código e testes. Se faltar uma definição relevante, registre
a lacuna para discussão de domínio.

## Decisões arquiteturais

Quando uma proposta contrariar um ADR existente, identifique a decisão
afetada e explique por que ela precisa ser reconsiderada.

## Coordenação entre integrantes

Mantenha um único vocabulário compartilhado para as quatro pessoas.
Ao alterar uma definição ou decisão, identifique as tarefas e os contratos
afetados para coordenar sua integração.

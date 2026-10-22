# Revisão independente — NVIDIA Studio (#31)

Base fixa confirmada: `a88698efc34cc03d9c03de3fc4cd1e74922c28fb` (T13).
Diff: `git diff a88698efc34cc03d9c03de3fc4cd1e74922c28fb...HEAD`.
Commits de implementação revisados: `e06e081` e `063577d`.

Cada eixo usou agente, branch e checkout próprios, somente leitura:
`review/nvidia-standards` e `review/nvidia-spec`. A spec foi o pedido de migração,
Issue #31 e especificação #1/T13 #14. Standards incluiu AGENTS.md, README,
arquitetura, contratos Studio, método científico e baseline Fowler da skill.

## Standards

Revisão final de `a88698e...063577d`: **0 achados**.

A correção de HTTP 202 preserva os contratos existentes, evita repetição
automática de inferência já aceita e documenta a limitação de polling. Os testes
adicionais verificam ambos os estágios pela interface pública.

Nenhuma violação documentada ou smell relevante identificado. Revisão estática;
não foram executadas chamadas externas pelo revisor Standards.

## Spec

**P2 inicial resolvido em `063577d`.** HTTP 202 era tratado como unavailable e
permitia repetir um POST já aceito. Agora recebe classificação sanitizada
pending_response, com invalid_generation e retryable=False. Os serviços preservam
o estado docente e encerram a operação sem repetir automaticamente o POST.

O revisor Spec reexecutou os três testes HTTP 202: adaptador, prévia e geração.
**3 aprovados**, confirmando uma única chamada por operação e recuperação explícita
posterior. Antes da correção, os três falharam e o teste de fluxo registrou duas
chamadas ao transporte externo controlado.

**Achados Spec abertos: 0.** Recuperação por polling permanece limitação documentada.
A comprovação de prévia e aula completas no endpoint real continua pendente de
autorização para o smoke; testes simulados não demonstram prontidão em produção.

## Verificação consolidada

- Backend final: **619 passed**, 7,34 s; dois avisos de depreciação de dependências.
- Contratos científicos: **7**; Studio: **40**; LessonBundle TypeScript: **4**.
- TypeScript/build: aprovado; Vite emite aviso de chunk acima de 500 kB.
- Playwright: **87 passed** = 20 integrados T13/Forensics + 19 revisão + 14 slides
  + 18 geração/operações + 5 ponte + 11 exportação.
- Smoke NVIDIA: executado apenas com MockTransport; percurso integral aprovado.
  CLI sem flag recusou execução com explicit_authorization_required / exit 2.
- Chamadas de inferência NVIDIA/Gemini reais nesta tarefa: **zero**.
- GeminiProvider, smoke Gemini, contratos públicos, catálogo e evidências sem diff.

Standards: **0** achados; Spec: **1 P2 resolvido, 0 abertos**. Maior gravidade
inicial por eixo: nenhuma em Standards; P2 em Spec.

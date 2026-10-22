# Matilda — auditoria e refinamento UI/UX

22/10/2026 · Relacionado à [Issue #14](https://github.com/zazacknazzo/Matilda-mvp/issues/14).
Base: `a88698efc34cc03d9c03de3fc4cd1e74922c28fb`, branch
`feat/issue-14-integrated-demo`. Implementação em `feat/matilda-ui-ux`, checkout
isolado no Codex. Nenhuma alteração no backend, contratos HTTP, tipos científicos,
catálogo ou integração NVIDIA.

## Preparação e skills

O catálogo cloud/executor foi inspecionado. As quatro skills solicitadas não
estavam instaladas; foram instaladas neste ambiente pelo gerenciador `skills`,
em `/workspace/work/.agents/skills`, fora do checkout publicado:

| Skill | Origem acessada | Aplicação |
|---|---|---|
| `interface-design` | `Dammyjay93/interface-design` | Metodologia principal: domínio, direção, hierarquia, tokens, revisão das capturas |
| `web-design-guidelines` | `vercel-labs/agent-skills` | Auditoria de interação, teclado, contraste, formulários e responsividade |
| `building-components` | `vercel/components.build` | HTML nativo, disclosure acessível, composição e tokens compartilhados |
| `vercel-react-best-practices` | `vercel-labs/agent-skills` | Estado derivado, renderização, dependências e tamanho do bundle |

Os quatro `SKILL.md` foram lidos, assim como as referências pertinentes de
acessibilidade, tokens, composição e estado. As guidelines foram obtidas de
`vercel-labs/web-interface-guidelines/main/command.md`. Nenhuma skill solicitada
ficou indisponível. A tentativa inicial de localizar `building-components` via
busca do CLI não retornou resultados; o catálogo `skills.sh` identificou o
repositório oficial `vercel/components.build`, cuja instalação funcionou.

Também foram lidas e aplicadas as skills locais `tdd`, `implement` e
`code-review`. As fronteiras de validação são as interfaces públicas de navegador
solicitadas no briefing: configuração, prévia, revisão, teclado, slides e
exportação. Não foram introduzidos testes de detalhes internos de CSS/React.
Foram consultados `AGENTS.md`, README, PRD v4, fluxo T10, integração T13 e os
componentes existentes antes das alterações.

## Auditoria priorizada

As prioridades abaixo se referem à jornada P0 de demonstração; não acrescentam
funcionalidades opcionais ao produto. Capturas `before/` foram feitas no commit
base, antes das alterações de UI.

| Prioridade | Local / problema observado | Correção / resultado |
|---|---|---|
| P0 | Prévia: revisar fontes e objetivos exigia atravessar documentos extensos; a próxima ação não aparecia na primeira tela | Ação principal no cabeçalho, visível também em 375 px; texto explica a aprovação necessária |
| P0 | Fonte em slide escuro herdava verde de link do Studio sobre fundo verde; contraste calculado de aproximadamente 1,08:1 | Links do material herdam a tinta do slide; contraste automatizado aprovado |
| P0 | Revisão: trecho original repetido ocupava a tela antes da proposta e da decisão docente | `details/summary` nativos para material e trechos integrais; evidências, participantes e limitações continuam abertos |
| P1 | Revisão longa: objetivos e salvamento distantes das sugestões | Resumo de decisões e atalho com foco para objetivos/salvamento; bloqueios de avanço mantidos |
| P1 | Studio sem atalho para conteúdo e sem orientação entre as cinco etapas | Skip link com foco e lista semântica com `aria-current="step"`; não cria atalhos que pulem a revisão |
| P1 | Forensics com rótulos operacionais de 8–10 px; metadados próximos, mas abaixo de 4,5:1 | Escala de leitura ampliada e metadados ligados ao token de legenda com contraste suficiente |
| P1 | Studio/revisão/dossiê pareciam módulos independentes por tipografia, branco e foco roxo divergentes | Papel, tinta, verde e cobre compartilhados; títulos editoriais serifados em continuidade com Forensics |
| P1 | Relógio da revisão atualizava todos os editores uma vez por segundo durante leitura/digitação | Um timer no vencimento efetivo; expiração e bloqueios continuam cobertos pela suíte |
| P1 | Projeção com corpo e fontes pequenos em relação à área disponível | Tipografia relativa à largura do slide, mantendo 16:9, fontes acessíveis, notas separadas e rolagem de conteúdo extenso |
| P2 | Botões secundários competiam com salvar/avançar; referências usavam IDs como principal rótulo | Ações secundárias em folha, principais em verde; links de evidência identificados pelo título canônico |

Estados vazios, loading, erro, sucesso, desabilitado e confirmação já existiam.
Foram preservados e percorridos: sem cobertura, falha do provedor, repetição
explícita, conflito, reconexão, retenção e aula anterior disponível.

## Direção e engenharia

A direção **caderno de evidências** mantém o papel claro, o verde profundo e
a tipografia editorial existentes. O foco de cada tela é preparar, conferir,
decidir, gerar ou apresentar. A assinatura é a ligação entre proposta, afirmação
documental, participantes e fonte; reaparece na prévia, revisão, dossiê, slide e
plano. Não foram acrescentados métricas decorativas, gradientes, animações,
bibliotecas de componentes ou fontes externas.

O sistema está em [`.interface-design/system.md`](../.interface-design/system.md)
e os tokens em [`design-system.css`](../frontend/src/design-system.css). Os CSS
de produção e dos harnesses compartilham os mesmos tokens. Controles continuam
nativos; `details` permite abrir todo o texto com Enter/Espaço. Não há clipping
ou remoção das fontes para obter uma composição menor. A ordem visual e a ordem
de teclado permanecem iguais em desktop e mobile.

A revisão visual identificou uma regressão introduzida durante o refinamento:
o título de foco mudava de altura ao perder foco, deslocando o botão durante o
clique. Um teste de ponteiro reproduziu a falha antes da correção; o título agora
mantém geometria estável. O teste permanece junto das verificações de teclado.
O teste de links inseguros da revisão foi restringido a links externos para
permitir o novo atalho interno, mantendo a verificação de URLs não confiáveis.

## Comparação visual real

Mesmo percurso CRISPR, API/SQLite reais, provedores externos controlados. Nenhuma
captura é evidência de inferência real. Dados científicos vêm dos snapshots
identificados como cache; `model=controlled` identifica a geração de teste.

| Tela, desktop 1440 px | Antes | Depois |
|---|---|---|
| Forensics | [captura](screenshots/ui-ux/before/1440-forensics.png) | [captura](screenshots/ui-ux/after/1440-forensics.png) |
| Descoberta/lista | [captura](screenshots/ui-ux/before/1440-discovery.png) | [captura](screenshots/ui-ux/after/1440-discovery.png) |
| Configuração | [captura](screenshots/ui-ux/before/1440-setup.png) | [captura](screenshots/ui-ux/after/1440-setup.png) |
| Prévia | [captura](screenshots/ui-ux/before/1440-preview.png) | [captura](screenshots/ui-ux/after/1440-preview.png) |
| Revisão | [captura](screenshots/ui-ux/before/1440-review.png) | [captura](screenshots/ui-ux/after/1440-review.png) |
| Aula/slides | [captura](screenshots/ui-ux/before/1440-lesson.png) | [captura](screenshots/ui-ux/after/1440-lesson.png) |
| Apresentação | [captura](screenshots/ui-ux/before/1440-presentation-content.png) | [captura](screenshots/ui-ux/after/1440-presentation-content.png) |
| Plano | [captura](screenshots/ui-ux/before/1440-plan.png) | [captura](screenshots/ui-ux/after/1440-plan.png) |
| Impressão A4 | [PDF](screenshots/ui-ux/before/plan.pdf) | [PDF](screenshots/ui-ux/after/plan.pdf) |

Todos os nove estados também possuem capturas em **768 e 375 px**, nos mesmos
diretórios, com o prefixo correspondente. Os dois estados de geração também
foram registrados e auditados nas três larguras. Comparações rápidas:

| Tela / largura | Antes | Depois |
|---|---|---|
| Prévia / 768 | [captura](screenshots/ui-ux/before/768-preview.png) | [captura](screenshots/ui-ux/after/768-preview.png) |
| Prévia / 375 | [captura](screenshots/ui-ux/before/375-preview.png) | [captura](screenshots/ui-ux/after/375-preview.png) |
| Revisão / 375 | [captura](screenshots/ui-ux/before/375-review.png) | [captura](screenshots/ui-ux/after/375-review.png) |
| Gerar / 1440 | — | [captura](screenshots/ui-ux/after/1440-generation.png) |
| Aula pronta / 1440 | — | [captura](screenshots/ui-ux/after/1440-generation-ready.png) |
| Loading / 375 | — | [captura](screenshots/ui-ux/after/375-loading.png) |
| Erro / 375 | — | [captura](screenshots/ui-ux/after/375-error.png) |

## Validação e limites

Chromium real headless: toda a jornada Forensics → configuração → prévia →
aceitar/rejeitar → objetivos → salvar → gerar → slides → apresentação → plano →
Markdown/PDF. Foram verificadas navegação por teclado, foco de retorno,
notas ocultas, textos extensos, movimento reduzido e ausência de overflow
horizontal em 33 combinações de onze telas com 1440/768/375 px.

`axe-core`, WCAG 2 A/AA e 2.1 AA: **zero violações automatizadas nas 33
combinações**, depois das correções de contraste. Isso não equivale a certificação
WCAG nem a teste com leitor de tela ou professores reais. Os dados resumidos
estão em [`ui-ux-validation.json`](ui-ux-validation.json).

| Verificação | Resultado |
|---|---|
| Backend de regressão, sem alteração de código | 558 passaram |
| Studio integrado + Forensics + novos testes UI | 23 passaram |
| Revisão docente | 19 passaram |
| Geração e recuperação | 18 passaram |
| Slides/plano/apresentação | 14 passaram |
| Exportação/print | 11 passaram |
| Ponte Forensics–Studio | 5 passaram |
| Total Playwright | **90 passaram** |
| TypeScript de produção e quatro harnesses; build | Aprovados |

Comandos executados a partir do checkout isolado:

```sh
.venv/bin/python -m pytest backend/tests -q
cd frontend
npm run build
npx tsc --noEmit -p review-harness/tsconfig.json
npx tsc --noEmit -p lesson-harness/tsconfig.json
npx tsc --noEmit -p generation-harness/tsconfig.json
npx tsc --noEmit -p bridge-harness/tsconfig.json
npx playwright test --config playwright.studio.config.ts
npx playwright test --config playwright.review.config.ts
npx playwright test --config playwright.generation.config.ts
npx playwright test --config playwright.lesson.config.ts
npx playwright test --config playwright.export.config.ts
npx playwright test --config playwright.bridge.config.ts
```

Sem nova dependência de produção. Bundle base: JS 517,52 kB / gzip 160,94 kB;
final: JS 520,39 kB / gzip 161,67 kB (**+0,73 kB gzip**). CSS gzip passou de
12,11 para 13,14 kB. O aviso preexistente de chunk acima de 500 kB permanece;
não foi introduzida divisão arquitetural para esta tarefa de UI. O timer da
revisão deixa de redesenhar editores a cada segundo. Não se alega melhoria de
latência do provedor.

Não foram feitos deploy, inferências reais ou merge. Projetor físico, diálogo
de impressão do equipamento alvo, leitor de tela e validação científica/docente
continuam exigindo ensaio humano. A auditoria de código está registrada em
[`reviews/ui-ux-code-review.md`](reviews/ui-ux-code-review.md).

Na apresentação, o professor consegue identificar sua etapa e a próxima ação,
comparar proposta e evidência sem atravessar trechos repetidos e projetar texto
maior mantendo fontes e limites documentados. A aprovação docente continua
obrigatória e o estado de falha preserva o material.

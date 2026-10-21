# T08 — slides e plano a partir de LessonBundle v1

Implementação isolada da Issue #9, baseada em main `f352ec6`, após integração de
T02 no PR #17. Os componentes usam `frontend/src/types/lesson.ts`, sem redefinir
contratos ou depender de API, repositório, Gemini ou recuperação científica.

## Consumo por T10

```tsx
import { LessonWorkspace } from './lesson/LessonWorkspace';

// bundle já validado e autorizado pelo servidor para esta sessão/revisão.
<LessonWorkspace bundle={bundle} />
```

`LessonWorkspace` importa seu CSS, escopado em `.lesson-ui`. A composição da rota
de produto e o GET autorizado pertencem a T10. Este ticket não altera App, main,
API, modelos ou dados científicos. O frontend atual de produção continua sendo
Forensics; o renderer fica disponível para integração pelo responsável da UI.

- `LessonPlan` percorre seções e resolve seus `slide_ids`/`activity_ids`, preserva
  objetivos, materiais, conhecimentos prévios, cronologia, conteúdo, avaliação,
  notas, fontes e limitações. Tempo de atividade não é somado novamente.
- `SlideRenderer` apresenta os seis layouts em uma superfície 16:9. Texto longo
  permanece integral, com rolagem dentro do slide quando necessário; não há
  corte ou paráfrase da afirmação documental.
- `LessonBlocks` resolve `evidence_claim.evidence_id` no snapshot de referências.
  Mostra afirmação canônica, todos os participantes, título/link/localização,
  limitações e procedência/cache. Nenhuma atribuição vem de texto livre do modelo.
- `PresentationMode` exibe somente slide e controles em diálogo modal. Notas e
  orientação avaliativa ficam no plano/painel docente, fora da projeção. Ações
  anterior/próximo, progresso, setas esquerda/direita, PageUp/PageDown, Home/End, Tab e Escape são
  suportadas. As setas cima/baixo permitem rolar conteúdo documental longo.
  O foco permanece no diálogo e volta a Apresentar aula ao sair.
  Tela cheia é acionada por botão; indisponibilidade mantém a apresentação na
  janela com aviso. A saída da tela cheia nativa fecha o modo de apresentação.
- `lessonRenderError` confere vínculos/layouts/blocos/fontes/tempos necessários
  à exibição e bloqueia a apresentação em erro. Não substitui Pydantic, validação
  científica, autorização, revisão ou origem canônica no servidor.

Todo conteúdo é renderizado como texto React; não se usa HTML arbitrário. Links
só aceitam URLs HTTP(S) absolutas sem credenciais, espaços ou controles. Nenhum
componente faz fetch, chama IA, grava sessão ou renova retenção. Aula sem
enriquecimentos preserva suas limitações sem inventar fonte ou spotlight.

Impressão, Markdown e downloads pertencem a T11. Integração HTTP/propriedade de
aula é T10. Não há editor de slides, geração, deploy ou exportação neste ticket.

## Harness local explícito

Na pasta `frontend`, após `npm ci`:

```sh
node node_modules/vite/bin/vite.js --config lesson-harness/vite.config.ts
```

Abrir `http://127.0.0.1:5174`. O banner identifica os dados de desenvolvimento e
oferece as quatro fixtures T02: CRISPR, RNA, sem enriquecimentos e opcionais.
O harness usa StrictMode e não precisa de API. O hook `window.setLessonExample`
existe apenas nessa entrada de teste, para exercitar variantes adversariais.

O build padrão `npm run build` usa a entrada de produto e não inclui o HTML,
fixtures, banner ou hook do harness. Não adicionar essa entrada ao deploy nem
apresentar seus exemplos como aula de um professor ou geração Gemini.

## Verificação reproduzível

Na pasta `frontend`:

```sh
node node_modules/typescript/bin/tsc --noEmit -p lesson-harness/tsconfig.json
npx playwright install chromium
node node_modules/@playwright/test/cli.js test --config playwright.lesson.config.ts
npm run build
node ../scripts/check_lesson_types.mjs
```

O config de testes sobe e encerra o harness automaticamente; a porta 5174 deve
estar livre. Os testes estão em `lesson-harness/tests`, separados dos seis testes
Forensics já existentes. `@types/node` é uma dependência apenas de desenvolvimento
para tipar o harness/config e a leitura de fixtures nos testes.

Resultados em 21/10/2026, Windows, Python 3.12/Pydantic 2.13.4, Node 26.5.1,
Vite 6.4.5 e Chromium 156.0.8078.4:

- **13 testes T08 aprovados**: CRISPR/RNA, seis layouts, fontes e coautores,
  plano/cronologia/avaliação/notas, teclado/foco em StrictMode, tela cheia nativa
  e fallback, mobile, opcionais/zero enriquecimentos, HTML literal, links
  inseguros, evidência/bloco inválido, ordem e texto sem truncamento.
- **6 testes Forensics aprovados**, com frontend/API reais, banco temporário e
  snapshots/mocks de descoberta já declarados na suíte existente.
- **366 testes backend aprovados**, incluindo os contratos Studio já integrados.
  Aviso preexistente Starlette/TestClient, sem falhas.
- Tipagem de componentes/harness/testes, quatro fixtures TypeScript T02 e build
  TypeScript/Vite aprovados. Revisão visual desktop/fontes/plano/mobile realizada.

Essa evidência cobre o renderer e a regressão existente, sem declarar jornada
Studio integrada, sessão/GET protegido ou geração real. Projetor físico,
impressão e ensaio com docentes permanecem nos tickets de entrega correspondentes.
O PR continua sujeito à revisão por outro integrante antes da integração.

## Revalidação e correção de foco — macOS, 21/10/2026

Revisão adicional encontrou um caso não coberto pela suíte inicial: focar o link
documental e avançar para um slide sem fonte removia o elemento focado. O foco
caía no `body` e Escape não alcançava o diálogo. Um teste pelo harness reproduziu
a falha antes da correção e passou após restaurar o foco no diálogo quando o
elemento anterior deixa de pertencer à apresentação. Controles que mantêm foco
continuam utilizáveis sem redirecionamento.

O harness também usa um cache Vite próprio em
`node_modules/.vite-lesson-harness`: os servidores do produto e dos exemplos
podem rodar juntos sem invalidar as dependências um do outro (`504 Outdated
Optimize Dep`). Nenhuma entrada de produção ou contrato compartilhado mudou.

Resultados sobre a branch T08, macOS arm64, Python 3.14.7, Node 26.10.0 e
Chromium 156.0.8078.4, executando os comandos acima e a suíte Forensics do README:

- **14 testes T08 aprovados**, incluindo a regressão de foco e Escape.
- **6 testes Forensics aprovados**, com API/frontend locais, SQLite isolado,
  `MATILDA_CACHE_TTL=999999999` para os snapshots existentes e as respostas de
  descoberta controladas pelos testes. Ambos os servidores Vite estavam ativos.
- **366 testes backend aprovados**; somente o aviso Starlette/TestClient existente.
- Tipagem do harness/componentes/testes, quatro fixtures TypeScript, build
  TypeScript/Vite e `git diff --check` aprovados. Saída de produção sem fixtures
  de aula, banner ou `setLessonExample`.

Revisão por agentes nos eixos Standards e Spec: nenhum achado de padrões; o
achado de foco da revisão de spec foi corrigido com a regressão acima. O aceite
do PR por outro integrante da equipe continua necessário antes do merge.

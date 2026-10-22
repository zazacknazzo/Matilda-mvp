# Validação local — 21/10/2026

## Resultado automatizado

- Backend: **38 testes aprovados** (`.venv/bin/python -m pytest backend/tests -q`).
- Navegador Chromium: **4 testes aprovados** (`npm run test:e2e` no frontend).
- Produção: TypeScript e Vite compilados com `npm run build`.

Os testes backend utilizam snapshots reais dos dez DOIs abaixo. API indisponível,
404, 401/403, 429 e falhas de rede são simulados com HTTPX ou substituição do
adaptador externo. Não se usa conteúdo bibliográfico fictício em produção.
A suite testa a rejeição de alegações históricas sem evidência, a exclusão de
candidatos sem documentação, identidade DOI incompatível, fontes, autorias,
direção das citações, nós consolidados e exportações.

| DOI real | Uso |
|---|---|
| 10.1126/science.1225829 | Fonte experimental CRISPR-Cas9 |
| 10.1038/nature09886 | CRISPR; cenário sem resumo no OpenAlex |
| 10.1126/science.1192272 | Processamento de RNA por Csy4 |
| 10.1126/science.1258096 | Revisão de CRISPR-Cas9 |
| 10.1016/j.immuni.2005.06.008 | Modificações de nucleosídeos |
| 10.1038/mt.2008.200 | Pseudouridina em mRNA |
| 10.1056/NEJMoa2034577 | Demonstração de vacinas RNA |
| 10.1056/NEJMoa2035389 | Generalização para outro artigo de vacina RNA |
| 10.1126/science.1231143 | Demonstração de edição genômica |
| 10.1038/171737a0 | Fora da cobertura conceitual atual |

Todos os registros foram recuperados ao vivo do OpenAlex durante a implementação,
com URLs e datas preservadas em `data/openalex_snapshots/`. Os testes repetíveis
usam o cache, sem alegar uma nova consulta externa em cada execução.

## Testes de navegador

1. Importar DOI, investigar CRISPR, selecionar contribuição, conferir participantes
   e DOI de evidência, alternar camadas e lista, baixar Markdown.
2. Investigar RNA em viewport 390 × 844, abrir dossiê sem depender do grafo,
   alternar abas e verificar ausência de rolagem horizontal.
3. Erro de DOI inválido e estado vazio sem inferir inexistência de contribuições.
4. Submeter DOI, iniciar investigação e selecionar contribuição por teclado.

A inspeção visual das capturas identificou uma falha inicial de dimensionamento
dos nós do React Flow. A correção passou a aplicar as mudanças de dimensão e
posição do componente. O teste confirma visibilidade dos nós e presença das
arestas. Capturas finais:

- [Página inicial](screenshots/inicio.png)
- [Investigação com dossiê](screenshots/investigacao.png)
- [Dossiê em celular](screenshots/mobile.png)

## Limites desta validação

Não foram realizados testes com usuários, leitores de tela, avaliação completa
WCAG, teste de carga nem medição de 40 nós no equipamento da apresentação.
Os tempos observados localmente não representam SLA. A revisão final das fontes,
a equipe e o pitch permanecem sob responsabilidade dos participantes.

A versão atual do TestClient gera um aviso de depreciação sobre HTTPX; os testes
passam. Não afeta as requisições da aplicação, feitas pelo adaptador HTTPX.

## Ampliação automática — atualização de 21/10/2026

Validação atual: **59 testes backend aprovados**, **6 testes de navegador
aprovados** e build TypeScript/Vite concluído. Os testes adicionais cobrem:

- ORCID e ID OpenAlex exatos, identidade sem identificador, declarações sem fonte,
  referências com protocolo inválido e identidades conflitantes.
- Ingestão por DOI normalizado, cache com procedência, histórico idempotente,
  limites de paginação e preservação do catálogo editorial.
- Trecho literal de resultados, ausência de resumo, recusa de complementos com
  DOI incompatível, respostas malformadas, retries de 429 e timeout parcial.
- Interface de candidatos, filtro de identidade documentada, fontes, celular e
  tentativa novamente após falha sem perder a investigação original.

O teste real com CRISPR e RNA também foi executado por API e navegador. Cada
cenário retornou oito candidatos. A identificação de Ann M. Arvin por ORCID no
Wikidata demonstrou descoberta fora dos três nomes manuais, mantendo a atribuição
científica pendente. As consultas, datas, fontes e indicações de cache constam em
[automatic-discovery-live-check.json](automatic-discovery-live-check.json).

[Captura da ampliação automática](screenshots/automatic-discovery.png).
As integrações públicas podem mudar; a validação registra uma observação datada.

## T13 — candidato P0 integrado, 22/10/2026

Código validado: `06a98f1`, base main `f7f2972` (PR #29 incluído), branch
`feat/issue-14-integrated-demo`. Documentação/capturas são acrescentadas depois
desse commit; não modificam o código validado.

Ambiente local: macOS, Python 3.14.7, Node 26.10.0, TypeScript 5.9.3,
Vite 6.4.5 e Playwright 1.64.1/Chromium headless. SQLite temporário por suíte.
Não foi publicado deploy nem verificado host HTTPS nesta execução.

| Verificação executada | Resultado |
|---|---|
| `.venv/bin/python -m pytest backend/tests -q` | **558 passaram**, 6,66 s na execução final |
| `scripts/check_scientific_contract.py` | 7 fixtures científicas conformes |
| `scripts/check_studio_contract.py` | 40 payloads HTTP conformes Pydantic/TypeScript |
| `node scripts/check_lesson_types.mjs` | 4 fixtures LessonBundle conformes |
| `tsc -b` e projetos generation/bridge/review/lesson-harness | aprovados |
| `tsc --noEmit` no novo `studio-integrated.spec.ts` | aprovado |
| `npm run build` | aprovado, 1771 módulos, 3,45 s |
| `playwright.studio.config.ts` | **20 passaram**, inclui os 6 testes Forensics do config padrão e 9 novos T13 |
| `playwright.generation.config.ts` | **18 passaram** |
| `playwright.review.config.ts` | **19 passaram** |
| `playwright.lesson.config.ts` | **14 passaram** |
| `playwright.bridge.config.ts` | **5 passaram** |
| `playwright.export.config.ts` | **11 passaram** |
| Total Playwright, sem duplicar Forensics do config padrão | **87 passaram** |
| Revisões independentes Standards e Spec | achados corrigidos e revalidados; [relatório](reviews/t13-code-review.md) |
| Guard do script live sem `--allow-paid-gemini` | recusou executar, exit 2, nenhuma chamada |

Backend emite duas depreciações preexistentes (Starlette/HTTPX e google.genai no
Python 3.14). Build mantém aviso de chunk JS acima de 500 kB (517,52 kB minificado,
160,51 kB gzip). Nenhum desses avisos foi tratado como falha nem ocultado.

Para repetir Playwright, executar em `frontend`:

```sh
node node_modules/@playwright/test/cli.js test --config playwright.studio.config.ts
node node_modules/@playwright/test/cli.js test --config playwright.generation.config.ts
node node_modules/@playwright/test/cli.js test --config playwright.review.config.ts
node node_modules/@playwright/test/cli.js test --config playwright.lesson.config.ts
node node_modules/@playwright/test/cli.js test --config playwright.bridge.config.ts
node node_modules/@playwright/test/cli.js test --config playwright.export.config.ts
```

Os seis casos `investigation.spec.ts` do config padrão são executados pelo config
Studio com servidores automáticos, preservando sua cobertura completa. Harnesses
isolados mantêm as substituições declaradas em seus guias; os novos E2E T13 e o
fluxo T10 usam frontend/backend/SQLite reais sem mocks nas APIs internas. Somente
provedores externos são controlados nessa integração.

TDD: o snapshot gravado da investigação, os eventos das seis etapas e a manutenção
no host falharam antes da conexão dos módulos; passaram após reutilizar T06/T12.
No navegador, a troca de origem durante uma prévia falhou antes da proteção contra
resposta antiga. Revisores identificaram retorno à contribuição incorreta/ausente
e exploração limitada à primeira contribuição; cada problema foi reproduzido
antes da correção e os nove cenários T13 passaram depois.

Segurança real: sessão alheia/expirada não exporta, origem externa é rejeitada,
formato/parâmetros inválidos falham, headers/escaping são seguros; material privado
original não entra no Markdown e exportar não chama IA. A suíte completa também
cobre limites, referências inválidas, prompt injection, idempotência, persistência,
reinício e expiração. O Forensics permanece funcional com IA indisponível.

CRISPR/RNA 50 minutos, slides/plano, evidências, revisão, Markdown, PDF, teclado,
notas ocultas, mobile, reconexão e retry foram verificados **com provedor externo
controlado**. Fontes bibliográficas provêm de snapshots reais com cache identificado.
As [capturas T13 e matriz CT/P0](integrated-demo-t13.md) permitem conferir o escopo.

**Gemini live não foi executado.** A chamada simples de 11,72 s informada pelo
usuário não comprova a prévia estruturada. Há instrumentação para recuperação,
contexto, contagem, geração, validação e persistência, com limites 45/75 s mantidos;
o gargalo real continua sem diagnóstico confirmado até autorização específica.
Projetor físico, diálogo de impressão/PDF no navegador do pitch, revisão humana
das fontes/pedagogia e aceite A/B/C/D também permanecem pendentes. M4 não é declarado
concluído. Nenhuma chamada paga ou alteração da Issue #1 foi realizada.

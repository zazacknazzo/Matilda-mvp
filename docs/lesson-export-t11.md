# Markdown e impressão — T11 / Issue #12

O mesmo LessonBundle v1 já validado de T08 alimenta slides, plano, impressão e
Markdown. Esta entrega não cria outra geração nem aceita material original como
entrada do exportador. O texto pedagógico é tratado como texto e cada bloco
`evidence_claim` resolve a afirmação do snapshot documental do bundle.

## Interface de aula

`LessonWorkspace` agora oferece **Baixar Markdown** e **Imprimir plano / salvar
PDF**. Recebe `exportApi?: LessonExportApi` para composição por portas; o padrão
usa GET `/api/studio/lessons/{id}/export?format=markdown`, com cookie same-origin.
Não há fallback para fixture em produção. Download falho conserva a aula, permite
nova tentativa explícita e não expõe o corpo de erro. MIME incorreto bloqueia o
download; nome de arquivo inválido usa uma alternativa segura.

`LessonPrintView` reutiliza `LessonPlan` em um portal direto no body, oculto na
tela e visível na mídia de impressão. Ctrl+P imprime o plano mesmo com a aba de
slides selecionada. CSS A4 oculta o host/controles e imprime notas, atividades,
avaliação, fontes com URLs e limitações. Blocos pequenos de notas/evidências são
mantidos juntos; texto que excede uma página pode continuar sem altura/overflow
limitantes. `afterprint` devolve o foco ao botão acionado. Não há PDF dos slides,
PDF binário no backend ou chamada ao provedor para exportar/imprimir.

## Serviço Markdown e handler isolado

- `backend/app/services/studio/lesson_export.py`: `lesson_markdown(bundle)` é
  determinístico, revalida o contrato e percorre a ordem das seções/slides.
  Inclui objetivos, conhecimentos prévios, materiais, tempos, atividades,
  critérios, notas, afirmações, participantes, referências, limites e registro
  de geração. Não recebe nem anexa SourceDocument, chave ou contexto de sessão.
- HTML e sintaxe Markdown de strings são escapados; URLs documentais exigem
  HTTP(S), sem credenciais/espaços/controles, com delimitadores percent-encoded.
  O resultado mantém o conteúdo canônico quando renderizado como Markdown.
- `backend/app/api/studio_exports.py`: `create_export_router(repository,
  resolve_session, clock=...)` prepara o handler, sem registrá-lo no app de
  produção. B fornece o StudioRepository T03 e um resolvedor de sessão real.

O resolvedor é assíncrono e retorna o ID interno da sessão válida ou None. Não
confundir o token opaco do cookie com o ID interno. `get_lesson` recebe sessão,
ID da aula e instante UTC explícito; cabe ao adaptador cumprir ownership e
expiração do contrato T03. Ausência/inexistência/expiração/outra sessão dão o
mesmo 404. Query desconhecida, repetida ou formato diferente de markdown dá 422.
Falha de validação do bundle armazenado dá 502 sanitizado, sem exportação parcial.

Resposta: UTF-8 `text/markdown`, Content-Disposition attachment com filename ASCII
derivado de hash do ID opaco, Cache-Control `no-store, private` e `nosniff`.
Títulos/IDs não entram literalmente no header. Só a leitura autorizada é chamada;
não há Set-Cookie, renovação de retenção, método de escrita ou serviço de IA.

T13 registra a rota em série com B após T10 e repete os testes com sessão, banco
e host reais. O handler isolado não é prova dessas integrações em produção.
Schemas, portas compartilhadas, tipos, catálogo e app Forensics foram preservados.

## Executar o harness

Requer dependências Python do README e `npm.cmd ci` no frontend.
Na raiz, em um terminal:

```powershell
.venv/Scripts/python.exe -X utf8 backend/tests/studio_export_harness.py
```

Em outro terminal, na pasta `frontend`:

```powershell
node node_modules/vite/bin/vite.js --config lesson-harness/vite.config.ts
```

Abrir `http://127.0.0.1:5174`; o Vite encaminha /api para o host de exemplo em
127.0.0.1:8001. O banner identifica a aula de teste, o repositório e a autorização
simulados. O resolvedor desse host sempre retorna fixture-owner: **não é uma
implementação de segurança**, não deve ser registrado no produto. O host importa
o handler/serializador reais e serve somente quatro bundles T02 explícitos.

## Verificação

```powershell
.venv/Scripts/python.exe -X utf8 -m pytest backend/tests -q
```

Na pasta `frontend`:

```powershell
node node_modules/typescript/bin/tsc -p lesson-harness/tsconfig.json
node node_modules/@playwright/test/cli.js test --config playwright.export.config.ts
node node_modules/@playwright/test/cli.js test --config playwright.lesson.config.ts
node node_modules/@playwright/test/cli.js test --config playwright.review.config.ts
npm.cmd run build
```

O config de exportação inicia os dois hosts isolados. Descobre `.venv` Windows ou
Linux/macOS; `MATILDA_TEST_PYTHON` permite escolher o intérprete. A suíte Forensics
usa o frontend/API em 5173/8000 conforme README, com `-X utf8` no Windows.

Resultados desta entrega em Windows, Python 3.14.6/Pydantic 2.13.4, Node 26.5.1,
Vite 6.4.5 e Chromium 156.0.8078.4:

- 387 testes backend aprovados, incluindo 21 de serialização/handler T11;
  somente aviso preexistente Starlette/TestClient com HTTPX.
- 50 testes Playwright aprovados: 11 exportação/print, 14 slides/plano,
  19 revisão docente e 6 Forensics. Download usa HTTP real com o handler isolado
  e portas simuladas; cenários de falha usam respostas controladas.
- Build TypeScript/Vite, tipagem do harness, 40 payloads Studio, 7 fixtures
  científicas e 4 fixtures de aula aprovados; nenhum contrato alterado.
- Quatro PDFs de teste gerados pelo Chromium: CRISPR/RNA com 4 páginas A4 cada,
  zero enriquecimentos com 3, notas longas com 4. Texto integral, participantes,
  fontes, notas e critérios conferidos por extração; todas as páginas renderizadas
  e inspecionadas, sem cortes ou controles. Também conferido mobile de 390 px.

O teste de teclado verifica a chamada a window.print e o evento afterprint; os
PDFs são salvos pelo mecanismo de impressão do Chromium. Diálogo nativo do
sistema, impressora física e equipamento do pitch continuam para o ensaio T13.
Revisão B/outro integrante e aceite permanecem necessários antes da integração.
Não encerrar automaticamente a Issue #1.

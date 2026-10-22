# T10 — fluxo completo integrado

Issue: https://github.com/zazacknazzo/Matilda-mvp/issues/11

O percurso de produção começa no formulário vazio e usa as rotas reais de prévia,
revisão, geração e leitura da aula. `ReviewWorkspace`, `GenerationPanel` e
`LessonWorkspace` foram conectados aos contratos existentes; nenhum harness ou
provedor de teste é importado pela aplicação de produção.

## Persistência e segurança

- Revisão compara `review_revision` dentro de `BEGIN IMMEDIATE`, grava somente
  decisões/campos pedagógicos permitidos e objetivos aprovados, incrementa uma
  vez e renova sessão/projeto. Conflitos não substituem a versão salva.
- Prévia, revisão, operação de geração e bundle usam o mesmo projeto/sessão e
  banco SQLite. GET da aula devolve exatamente o ID retornado pela geração.
- `studio_scientific_snapshots` guarda a autoridade científica resolvida pelo
  servidor junto da publicação. `studio_generation_operations` guarda claims,
  fingerprint e idempotência. Ambas são migrações aditivas com cascade.
- `studio_preview_operations` também controla a admissão da geração: uma
  operação por sessão, duas globais. A revisão fica bloqueada durante geração;
  o limite de cinco gerações/hora é atômico. Recuperação de operação abandonada
  preserva decisões e registra erro após 75 segundos mais 15 de tolerância.
- Toda leitura exige sessão proprietária válida. Escritas exigem Origin
  permitido; leituras verificam Origin quando enviado (GET same-origin pode
  omiti-lo). GET, exportação e replay concluído não renovam retenção/cookie.
- O bundle é imutável e sobrevive a uma nova revisão. A nova revisão exige
  nova chave/operação para gerar. A limpeza remove dados Studio expirados e
  preserva as tabelas Forensics.
- Prévias T05 antigas sem snapshot científico não são apagadas nem completadas
  com dados inventados: continuam consultáveis e exigem nova prévia para gerar.
- O catálogo JSON é lido explicitamente em UTF-8 para a execução no Windows.

## Verificação local

Executado em Windows, Python 3.14 e Node, sem chamadas reais ao Gemini:

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest backend\tests -q
npm.cmd --prefix frontend run build
.\.venv\Scripts\python.exe scripts\check_studio_contract.py
.\.venv\Scripts\python.exe scripts\check_scientific_contract.py
node scripts\check_lesson_types.mjs
Push-Location frontend
node node_modules/@playwright/test/cli.js test --config playwright.studio.config.ts
node node_modules/@playwright/test/cli.js test --config playwright.lesson.config.ts
Pop-Location
```

- 537 testes backend passaram, incluindo 12 novos casos HTTP T10. API,
  recuperação científica, validadores e SQLite são reais; somente o provedor
  externo é controlado. Um caso usa o SDK oficial Gemini com MockTransport
  somente na conexão Google e verifica os dois estágios, tokens, ausência de
  ferramentas e modelo efetivo.
- Jornada Studio e regressão Forensics: 10 testes passaram antes de adicionar
  a segunda resolução ao T10. Depois, os dois percursos integrais T10 passaram
  em 1440 px e 390 px. Sem seed, armazenamento preparado ou interceptação de
  APIs internas: aceitar/rejeitar, editar, aprovar, salvar, recarregar, gerar,
  abrir slides/plano pelo ID e voltar à revisão por teclado.
- 14 testes de renderização T08 passaram, incluindo seis layouts, tempos,
  apresentação, notas, teclado/foco, links seguros e celular. São testes de
  componentes com fixtures declaradas; não representam prova de Gemini real.
- Build e verificadores de 40 payloads Studio, 7 fixtures científicas e
  4 fixtures LessonBundle passaram. O build avisa sobre chunk acima de 500 kB;
  a suíte conserva os avisos de depreciação das dependências existentes.

## Gate real pendente

O usuário autorizou explicitamente o envio do exemplo CRISPR ao Gemini e o
consumo da API em 22/10/2026. A tentativa de executar o roteiro com
`--allow-paid-gemini` encerrou na checagem de configuração: `GEMINI_API_KEY`
ausente no ambiente do backend e no `.env` do clone. Nenhuma chamada externa
foi enviada nem houve cobrança. O ensaio real continua pendente da configuração
da chave; nenhum teste local deve ser apresentado como essa prova real.

`scripts/smoke_studio_t10.py` está preparado e requer a opção explícita
`--allow-paid-gemini`. Executar somente após autorização para enviar o exemplo
CRISPR e consumir a API, com `GEMINI_API_KEY` configurada no backend:

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts\smoke_studio_t10.py --allow-paid-gemini
```

O roteiro usa API, ciência e SQLite reais em `.runtime/studio-t10-smoke.sqlite`,
sem seed/mocks; cria a prévia, aprova uma sugestão e rejeita as demais, aprova
objetivos, gera e recupera o mesmo bundle. Registra IDs, modelo efetivo, latência
e uso agregado, sem expor chave, material ou resposta bruta do provedor.
O resultado real e a revisão por outro integrante continuam pendentes; a issue
11 e a especificação #1 não devem ser encerradas por esta entrega local.

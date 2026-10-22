# T12 — robustez operacional (Issue #13)

Base atual: `main` em `3bfdcd6223f0d019d35b4f282499b0e1c5f8d9aa`, merge do
PR #28 com a T10 integrada. A atualização do PR #29 incorporou essa base pelo
merge `efca5c4`, preservando a história da branch
`feat/issue-13-operational-robustness`. Não houve conflito textual.
Skills implement, tdd e code-review disponíveis em `.agents/skills/`.
Pontos de teste aprovados nas Issues #1/#13: HTTP, portas M0, transporte externo
e navegador. Desenvolvimento em worktree/branch exclusiva, sem alterar contratos
M0, rotas de revisão, repositório de prévia, `main.py` ou composição da T10 no
delta em relação à main. A validação atual inclui o fluxo T10; os resultados
anteriores à integração estão identificados como histórico abaixo.

## Comportamento

- Consultar o estado ou admitir uma repetição no adaptador SQLite da T09 recupera
  operações abandonadas a partir de 75 + 15 segundos. Antes disso conserva
  `generating`; depois registra timeout sanitizado, conserva revisão, objetivos,
  documentos, retenção concedida e eventual bundle anterior. Claim antigo não
  consegue finalizar sobre uma operação recuperada.
- `studio_maintenance_lifespan(repository)` recebe a porta M0: executa limpeza
  ao iniciar e a cada 15 s, cancela/aguarda sua tarefa ao encerrar. O repositório
  conserva responsabilidade por recuperação e limpeza atômicas. Falha de
  armazenamento gera aviso fixo e contador; não impede o host independente do
  Forensics de iniciar. Não há importação da implementação T05/T10.
- GenerationPanel consulta por GET ao reconectar ou voltar à aba. Abandona apenas
  uma consulta presa na conexão antiga, sem cancelar uma geração admitida por
  reflexo. Bloqueia nova geração offline ou enquanto o resultado é incerto.
  Recupera um bundle pronto sem POST e permite abrir a aula anterior, identificada
  como correspondente à revisão anterior; repetição exige ação explícita e mantém a
  chave existente em sessionStorage. A espera de uma tarefa retomada também
  avisa ao ultrapassar a meta de 45 s. Não há porcentagens/etapas inventadas.
- Os limites M0 permanecem: até duas tentativas no mesmo deadline, metas 30/45 s,
  backend 45/75 s, cliente 55/85 s, proxy >=100 s, reserva de persistência de 5 s.
  Retenção de sete dias renova somente em ação válida; GET/export/replay não
  renovam. Segurança e validação continuam obrigatórias nas rotas de origem.

## Observabilidade e composição

`GenerationService(..., metrics=metrics)` aceita opcionalmente `StudioMetrics`.
Sem argumento, cria seus próprios contadores; assinatura existente permanece
compatível. `metrics.snapshot()` devolve somente agregados: resultados/replays/
falhas/cancelamentos, códigos Studio, tentativas de geração, tokens de entrada
contados, tokens de saída reportados, soma das durações e limpeza/erros/remoções.
Não representa faturamento: tentativas sem resposta não têm uso de saída conhecido.
Os contadores são locais ao processo e reiniciam com ele. Logs registram apenas
resultado, código permitido e duração; sem material, prompt, respostas brutas,
chaves, sessões ou labels de cardinalidade ilimitada. Não há dashboard nem rota
pública de métricas.

Para a composição adicional em T13, usar o **mesmo repositório de produção** que implementa
as garantias de cleanup_expired M0; não selecionar IsolatedGenerationRepository
em produção nem importar o harness. Preservar o lifespan do host:

```python
metrics = StudioMetrics()
maintenance = studio_maintenance_lifespan(repository, metrics=metrics)

@asynccontextmanager
async def lifespan(app):
    async with existing_lifespan(app):
        async with maintenance(app):
            yield
```

A composição e o lifespan existentes da T10 não são substituídos neste PR.
A adoção da manutenção opt-in de 15 s e o ensaio live permanecem na T13,
conforme a própria Issue #13. A regressão da API integrada T10 já é exercitada
na atualização atual, com apenas o provedor externo controlado.
A manutenção já é executável no harness isolado T09/T12. Seus endpoints
`/test/interrupt` e `/test/advance` existem exclusivamente em backend/tests;
a interrupção reconstrói o adaptador sobre o SQLite persistido. Isso testa a
recuperação controlada, não um kill real do servidor em produção.

## Matriz de validação

| Garantia | Evidência reproduzível | Limite da evidência |
|---|---|---|
| 401/403, 429, bloqueio, JSON inválido, truncamento, timeout e desconexão | test_studio_operations_transport.py: SDK oficial, router/orquestrador/validador e SQLite reais; HTTPX MockTransport na fronteira Google | Sem Google real, chave/quota/modelo real não atestados |
| Falhas sem chave/material em resposta, logs e métricas | matriz de transporte e test_studio_operations.py | Sentinelas de teste; não equivale a auditoria de toda dependência |
| Orçamento comum, duas tentativas, tokens, metas e tetos | testes T09, T05 e caso T12 de sucesso aos 46 s; navegador com relógio controlado | Tempo sintético não é medição de latência Gemini |
| Reconexão, aba retomada, perda da resposta, mesma chave, consulta presa | operations.spec.ts e generation.spec.ts | API/SQLite reais no harness; sessão e revisão de referência controladas |
| Reinício, deadline +15, conclusão tardia e bundle anterior | test_studio_operations.py e testes T09; navegador com admissão persistida/reconstrução | Reabertura de SQLite e operação abandonada controlada |
| 24 h < retomada <7 dias; não renovar GET/download/replay; renovar admissão | test_studio_operations.py; test_studio_flow.py testa também a persistência T10 | Relógio controlado; sem medição de latência Gemini |
| Limpeza sem visita e armazenamento indisponível | lifespan real, relógio controlado, SQLite temporário e falha real de filesystem | Opt-in; requer composição no host integrado |
| Sessão/Origin/corpo/quota, IDs e evidências maliciosas | regressões T05/T09/T03/T04 e exportação T11 | T12 não dispensa as verificações das rotas reais da T10 |
| Forensics sem Gemini | backend e navegador existentes, inclusive bridge com chave vazia | Fontes científicas controladas/snapshots |

Não foi constatada ausência de proteção nas rotas existentes exercitadas.
As rotas de revisão/leitura/geração T10 vieram da main e são verificadas pelos
testes de integração; nenhuma rota nova foi criada nesta atualização.
Qualquer falha de segurança encontrada na conexão
real deve bloquear a rota e ser corrigida pelo ticket que a introduz; não é
uma melhoria opcional futura.

## Executar

Na raiz, após instalar backend/requirements.txt e dependências frontend:

```sh
.venv/bin/python -m pytest backend/tests/test_studio_operations.py backend/tests/test_studio_operations_transport.py -q
.venv/bin/python -m pytest backend/tests -q
.venv/bin/python scripts/check_studio_contract.py
.venv/bin/python scripts/check_scientific_contract.py
node scripts/check_lesson_types.mjs
cd frontend
npx tsc -p generation-harness/tsconfig.json --noEmit
npm run build
npx playwright test --config playwright.generation.config.ts
npx playwright test --config playwright.studio.config.ts
npx playwright test --config playwright.bridge.config.ts
npx playwright test --config playwright.review.config.ts
npx playwright test --config playwright.lesson.config.ts
npx playwright test --config playwright.export.config.ts
```

A configuração Studio inicia a aplicação real com apenas a dependência externa
controlada e inclui os seis cenários Forensics. As demais configurações mantêm
os limites declarados por seus harnesses. Nenhum mock é fallback do produto.

## Histórico da entrega inicial — antes da integração T10

Base dessa execução inicial: `16285169a92a43e2ab2c45df58b56eba969ae4af`
(PR #27). Os números abaixo pertencem à versão original do PR #29.

Ambiente: Linux x64, Python 3.12.14, FastAPI 0.141.1, Pydantic 2.13.4,
google-genai 2.32.0, Node 24.19.0, TypeScript 5.9.3, Vite 6.4.5,
Playwright 1.64.1 e Chromium 156.0.8078.4.

| Execução | Resultado obtido |
|---|---|
| pytest backend/tests -q | **541 aprovados**, 10,56 s; inclui os 16 novos casos T12 |
| Typecheck generation-harness e build TypeScript/Vite | aprovados; build Vite em 3,07 s |
| check_studio_contract.py | 40 payloads HTTP conferidos em Pydantic/TypeScript |
| check_scientific_contract.py | 7 fixtures científicas conferidas |
| check_lesson_types.mjs | 4 fixtures de aula conferidas |
| Playwright generation | **18 aprovados**, 12,9 s; 11 T09 + 7 T12 |
| Playwright studio | **9 aprovados**, 11,1 s; inclui 6 Forensics |
| Playwright bridge | **5 aprovados**, 4,3 s; Forensics sem chave Gemini |
| Playwright review | **19 aprovados**, 10,2 s |
| Playwright lesson | **14 aprovados**, 7,0 s |
| Playwright export | **11 aprovados**, 6,0 s |
| Total Playwright | **76 aprovados** |
| Verificação do bundle de produção | sem sentinelas de material/chave, identidade de fixture ou endpoints de controle do harness |

TDD em fatias verticais: o teste de status após reinício primeiro falhou
(`generating` aos 90 s), passou após recuperação no GET; os casos de reconexão,
offline, retomada da aba, espera após a meta, consulta presa e acesso à aula
anterior falharam no comportamento ausente antes das respectivas implementações.
O teste de manutenção antecedeu o lifespan; o de métricas antecedeu os contadores.
As regressões de retenção/transporte usam as fronteiras públicas já aprovadas,
sem redesenhar contratos compartilhados.

[Revisão independente em dois eixos](reviews/t12-code-review.md): Standards
**0 achados**, Spec **0 achados**. Nenhuma correção funcional foi necessária
após essa revisão. Aceite humano antes da integração permanece pendente.

Há um aviso preexistente de depreciação Starlette TestClient/HTTPX; não houve
falha de teste. As screenshots Forensics regeneradas pelos testes foram
descartadas, sem incluir alterações visuais incidentais neste PR.

**Adaptadores controlados:** Google HTTP simulado no SDK oficial; geração por
portas M0 com orquestrador, validador e SQLite reais, sessão/revisão de referência
no harness. Prévia T05 exercitada com aplicação real e provedor controlado.
**APIs externas reais:** nenhuma chamada live, chave/quota/modelo/latência reais
não atestados. Não houve ensaio no projetor. Na entrega inicial, a regressão
integrada T10 ainda não estava disponível; ela foi executada na atualização
abaixo. A composição adicional de manutenção/live da T13 permanece fora do escopo.

## Atualização do PR #29 com a main do PR #28

Comparação conferida: `git diff 3bfdcd6...HEAD`. A main atual foi incorporada
sem descartar commits da T12 nem reescrever módulos da T10.

- `generation_repository.py` mantém os imports de `timestamp`/`fingerprint` de
  `generation_identity.py` introduzidos na T10 e `_recover` da T12 em GET,
  admissão e limpeza. As funções de identidade não foram duplicadas ou alteradas.
- O adaptador isolado continua exclusivo dos testes. `StudioRepository`, as
  tabelas e os snapshots científicos da T10 foram preservados; a produção não
  seleciona o banco isolado. A recuperação já disponível no runtime T10 continua
  usando suas transações e dados próprios.
- A nova regressão `test_t12_restart_preserves_t10_bundle_review_retention_and_same_key`
  usa revisão criada pela API real e provedor controlado. Admite geração perto da
  expiração, reabre o adaptador sobre o mesmo SQLite, conserva `generating` aos
  89 s, recupera aos 90 s e preserva decisões, objetivos, documentos, prazo
  concedido e bundle anterior. Rejeita conclusão tardia do claim antigo; retry
  explícito com a mesma chave gera uma única nova aula e replay 24 h depois não
  chama o provedor nem renova o prazo. O isolamento de outra sessão permanece.

Não foi encontrada regressão funcional que exigisse alterar código de produção
após o merge. O cenário adicional amplia a evidência de compatibilidade pelas
fronteiras públicas M0/HTTP já aprovadas; não cria funcionalidade ou harness T13.

Ambiente desta execução: macOS arm64, Python 3.14.7, Node 26.10.0,
TypeScript 5.9.3, Vite 6.4.5 e Playwright 1.64.1. Worktree separado em
`/private/tmp/matilda-t12-update`; dependências frontend instaladas pelo lockfile
em modo offline, sem mudança de manifesto ou lockfile.

| Execução atual | Resultado |
|---|---|
| `.venv/bin/python -m pytest backend/tests -q` | **554 aprovados**, 9,77 s |
| TypeScript produto e harnesses generation/bridge/review/lesson | aprovados |
| `npm run build` | aprovado, Vite em 2,20 s |
| Contratos científico / Studio / LessonBundle | 7 / 40 / 4 fixtures aprovadas |
| Playwright Studio | **11 aprovados**, incluindo 2 jornadas T10 CRISPR (1440/390 px) e 6 Forensics |
| Playwright geração/recuperação | **18 aprovados** |
| Playwright bridge / revisão / slides / exportação | **5 / 19 / 14 / 11 aprovados** |
| Total Playwright | **78 cenários distintos aprovados** |

O E2E T10 parte do formulário vazio, cria prévia e revisão pela API real, gera,
consulta e retoma o mesmo bundle, valida sessão isolada e conserva decisões ao
voltar. Não usa seed nem interceptação de APIs internas; apenas o provedor externo
é controlado. A matriz T12 continua separada no harness M0/T09, com transporte
Google controlado nos testes do SDK. Nenhuma chamada paga ou externa real ao
Gemini foi executada; chave/quota/modelo e latência live não são atestados.

Os dois avisos backend são de depreciação de dependências (TestClient/HTTPX e
SDK Gemini no Python 3.14). O build informa chunk de 506,81 kB; não houve mudança
de bundling ou falha. Screenshots Forensics geradas pela regressão não são
incluídas no PR. Revisões independentes Standards e Spec contra as Issues
#11/#13: **0 achados em cada eixo**, conforme o relatório atualizado.

PR permanece aberto, sem merge automático. A manutenção opt-in em produção,
ensaio Gemini live e demais entregas da Issue #14/T13 não foram implementados.

# T12 — robustez operacional (Issue #13)

Base: `main` em `16285169a92a43e2ab2c45df58b56eba969ae4af`, merge do
PR #27. Skills implement, tdd e code-review disponíveis em `.agents/skills/`.
Pontos de teste aprovados nas Issues #1/#13: HTTP, portas M0, transporte externo
e navegador. Desenvolvimento em worktree/branch exclusiva, sem alterar contratos
M0, rotas de revisão, repositório de prévia, `main.py` ou composição da T10.

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

Para compor em T10/T13, usar o **mesmo repositório de produção** que implementa
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

A composição existente de prévia não é substituída neste PR. A adoção na API
integrada e reexecução live pertencem à T13, conforme a própria Issue #13.
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
| 24 h < retomada <7 dias; não renovar GET/download/replay; renovar admissão | test_studio_operations.py; T05 testa criação e cookie reais | save_review de produção pertence à T10, sem declaração de integração antecipada |
| Limpeza sem visita e armazenamento indisponível | lifespan real, relógio controlado, SQLite temporário e falha real de filesystem | Opt-in; requer composição no host integrado |
| Sessão/Origin/corpo/quota, IDs e evidências maliciosas | regressões T05/T09/T03/T04 e exportação T11 | T12 não dispensa as verificações das rotas reais da T10 |
| Forensics sem Gemini | backend e navegador existentes, inclusive bridge com chave vazia | Fontes científicas controladas/snapshots |

Não foi constatada ausência de proteção nas rotas existentes exercitadas.
As rotas de revisão/leitura/geração integrada da T10 não são criadas nem
certificadas antecipadamente. Qualquer falha de segurança encontrada na conexão
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

## Resultados desta revisão

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
não atestados. Não houve ensaio no projetor. A conexão final com as rotas da T10
e a reexecução integrada/live ficam na T13 conforme a Issue #13; esta entrega
não declara esse gate concluído nem implementa a Issue #14.

# Ponte científica Forensics–Studio — T06 / Issue #7

T06 fornece um resolvedor e componentes independentes do host para transferir
ciência existente à preparação e conferir suas fontes. Reutiliza o adaptador
T04 e os modelos M0 integrados. Nenhuma rota, schema, tabela, catálogo, cliente
Studio ou módulo de geração foi alterado. A composição final no host de
produção pertence à Issue #14; o E2E do fluxo Studio integrado pertence à T13.

## Resolução no servidor

```python
from app.services.studio.source_resolver import resolve_scientific_source

source = await resolve_scientific_source(
    project_id=project.id,
    analysis_id=existing_analysis_id,  # alternativa: doi=canonical_or_url_doi
    documents=original_material_documents,
)
snapshot = source.snapshot()
```

O chamador é responsável pela sessão, ownership do projeto e por construir os
documentos originais no servidor. `documents` admite somente texto/conceitos
do projeto de destino; o resolvedor constrói metadados a partir do Paper real.
Não confiar em Paper, contexto ou snapshot enviados pelo navegador/modelo.

DOI reutiliza normalização, cache datado, fallback explícito e orçamento/retries
existentes do OpenAlex. DOI e `analysis_id` simultâneos são 422, mesmo havendo
material; ausência de origem ou identificador vazio também. Investigação
ausente/expirada é 404, sem consulta alternativa pelo DOI. Erros upstream mantêm
os status/detail Forensics; cabe ao consumidor HTTP Studio adaptar apenas o
envelope. Erros de composição de documentos são `ValueError` e devem ser
corrigidos pelo chamador antes de admitir uma operação.

`analysis_id` lê a investigação persistida sem rede, conservando seu Paper,
cache, data e avisos. Sem material adicional, conserva integralmente os matches
registrados, inclusive participantes, evidências, classificação e ordenação,
mesmo após uma atualização editorial. Não incorpora candidatos automáticos.
Adicionar material produz contexto misto e nova busca T04 sobre esse contexto;
a comparação bibliográfica continua limitada ao artigo da investigação.

Texto/conceitos sem DOI usam diretamente T04, sem criar artigo, investigação ou
grafo. A comparação é UNKNOWN/THEMATIC_ONLY segundo o motor existente. Sem
cobertura, o contexto válido conserva uma limitação explícita e matches vazios.

`snapshot()` devolve uma cópia JSON independente contendo:

| Campo | Modelo existente |
|---|---|
| `scientific_context` | ScientificContext, incluindo procedência e analysis_id |
| `source_documents` | SourceDocument[], incluindo originais e metadados reais |
| `papers` | Paper[], vazio para material sem DOI |
| `matches` | DiscoveryMatch[], participantes e evidências completas |

Esta composição de modelos M0 é um resultado de serviço/componente, sem nova
variante de contrato HTTP. O consumidor persiste os dados científicos ao criar
a prévia; guardar apenas `analysis_id` não basta. Consultar/explorar a cópia não
precisa resolver novamente o link e não renova a retenção da investigação.
O resolvedor não persiste nem renova projetos, não chama IA e não importa T05.

## Portas dos componentes

`ForensicsStudioBridge<State>` recebe `source` (a composição acima), `state`
(estado opaco mantido pelo host) e callbacks:

- `onConfigure(origin, snapshot, state)`: Transformar em aula entrega origem
  exclusiva `{analysis_id}` ou `{doi}`, cópia da ciência e o estado recebido.
  O host abre configuração confirmável; o componente não solicita prévia nem
  geração. Para material, origin é `{}` e os documentos originais seguem no
  snapshot para preencher texto/conceitos explicitamente.
- `onExplore?(contributionId, state)`: informa a contribuição selecionada e o
  estado ao host. A ponte abre o dossiê correspondente sem consulta obrigatória.
- `onReturn(state)`: devolve o estado recebido ao voltar do dossiê; o foco
  retorna à descoberta acionada quando a ponte continua montada.

O host mantém material, decisões, filtros e posição de apresentação, inclusive
quando desmonta um modo. A ponte não conhece App, router, planner ou repositório.
Não usa hash, localStorage ou API Studio, nem altera estado pedagógico.

`ScientificDossier` também pode ser montado diretamente com `source`,
`contributionId` e `onBack`. Apresenta artigo real quando disponível,
procedência, pesquisadores, todos os participantes, fontes, afirmações literais,
localizações, classificações independentes e limitações. Usa apenas os dados
recebidos; material sem DOI continua consultável sem artigo raiz. Conteúdo é
somente leitura, links aceitam apenas HTTP(S) sem credenciais e strings são
renderizadas como texto React.

## Testes e execução

Fronteiras da Issue #7 usadas nos ciclos TDD: resolvedor público com SQLite e
APIs Forensics existentes; callbacks e navegação dos componentes no navegador.
Falhas observadas antes da implementação: módulo inexistente, suporte a
analysis_id ausente, origem ambígua aceita, contribuição registrada substituída
por revisão posterior do catálogo e ação Explorar descoberta ausente.

```sh
.venv/bin/python -m pytest backend/tests/test_studio_source_resolver.py -q
cd frontend
node node_modules/typescript/bin/tsc -b
node node_modules/typescript/bin/tsc -p bridge-harness/tsconfig.json
node node_modules/@playwright/test/cli.js test --config playwright.bridge.config.ts
```

O harness é isolado, marcado como **HARNESS DE TESTE T06**, somente DEV e fora
da entrada/build de produção. Usa fixtures científicas M0 e as APIs Forensics
existentes, com SQLite temporário e snapshots reais identificados como cache.
A configuração confirmável é uma porta Studio de teste, não uma prévia real.
Nenhum endpoint científico de teste foi criado; nenhuma chamada Gemini é feita.
Os testes não chamam nem substituem o cliente/planner/repositório T05.

Para explorar manualmente, iniciar a API em 8017 com banco de teste e
`MATILDA_CACHE_TTL=999999999`, e executar no frontend:

```sh
node node_modules/vite/bin/vite.js --config bridge-harness/vite.config.ts
```

Abrir `http://127.0.0.1:5177`. A suíte Playwright inicia ambos automaticamente.
Os testes de regressão e a revisão final são registrados abaixo após execução.

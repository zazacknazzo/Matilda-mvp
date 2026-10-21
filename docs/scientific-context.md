# Contrato científico inicial — T01 / Issue #2

Revisão proposta: **v1**, preparada em `feat/scientific-core` para a
[Issue #2](https://github.com/zazacknazzo/Matilda-mvp/issues/2), conforme as
seções 2, 3 e Testing Decisions da
[especificação #1](https://github.com/zazacknazzo/Matilda-mvp/issues/1).
Responsabilidade: frente A — Scientific Core. Consumidores: B/C/D.

Este artefato prepara M0. O aceite explícito dos consumidores e a revisão por
outro integrante ainda devem ser registrados pela equipe; preparar estes
arquivos não encerra M0 nem libera implementação paralela. Nenhuma rota,
persistência, extração de texto ou adaptação de recuperação Studio foi criada.

## Arquivos e compatibilidade

- `backend/app/schemas/scientific_context.py`: `SourceDocument`, `Provenance`,
  `ScientificContext` e `SourceAnchor`, em módulo separado dos modelos antigos.
- `frontend/src/types/scientific-context.ts`: formas **serializadas** desses
  quatro modelos; defaults materializados e campos nulos explícitos.
- `tests/fixtures/studio/scientific/`: exemplos compartilhados e contraexemplos.
- `backend/tests/test_scientific_context_contract.py`: validação pública dos
  modelos, integridade dos exemplos e regressão científica.
- `scripts/check_scientific_contract.py`: compila os JSON válidos contra os tipos
  TypeScript, sem casts que escondam divergências.

Os arquivos e contratos existentes do Forensics permanecem intactos. Os novos
modelos não são reexportados por `app.schemas`; consumidores usam o módulo novo.
Não existe endpoint HTTP Studio nesta fatia. Quando B publicar sua API, o schema
Pydantic será a referência do OpenAPI; `schema_version = 1` pertence ao envelope
Studio, não é um campo adicional de ScientificContext.

## Uso e validação

```python
from app.schemas.scientific_context import ScientificContext, SourceAnchor, SourceDocument

document = SourceDocument.model_validate_json(document_json)
context = ScientificContext.model_validate_json(context_json)
context.validate_references([document], concepts=editorial_concepts, papers=[])
anchor = SourceAnchor.model_validate_json(anchor_json)
start, end = anchor.locate(document)
```

São duas etapas obrigatórias para um consumidor: validação estrutural Pydantic e
`validate_references` com documentos, conceitos editoriais e Papers resolvidos
**pelo servidor**. Não aceitar do cliente ou da IA o conjunto que serve de
autoridade. A segunda etapa não consulta rede, banco ou catálogo: recebe os
objetos já recuperados. A autenticação do projeto e a resolução/expiração de
`analysis_id` pertencem à API futura, não a estes modelos.

Todos os modelos novos rejeitam campos extras e coerções de tipos. IDs são
opacos, não vazios; os IDs científicos existentes não são renomeados. Conceitos
e labels são alinhados, sem IDs duplicados, e cada conceito possui procedência.
IDs editoriais/labels devem coincidir com o catálogo. Conceitos dinâmicos só são
resolvidos a partir dos conceitos dos Papers reais fornecidos. Um alias
editorial deve corresponder literalmente a trecho do documento e respeitar a
normalização e os limites de palavra atuais. Labels pedagógicos livres da IA não
viram IDs científicos.

`SourceDocument.content` preserva o texto exato, inclusive espaços e acentos.
Todos os tipos de documento têm título e conteúdo de até 20.000 caracteres,
sem truncamento. Quotes de procedência e âncoras usam esse mesmo teto.
`concept_list` usa um conceito por linha, até
20 linhas não vazias com até 100 caracteres cada. `paper_metadata` exige DOI
normalizado pelo validador atual (limite efetivo 250) e preserva o título real;
seu conteúdo é `paper.title`, seguido de `"\n\n" + paper.abstract` quando houver
resumo. Esse formato é uma representação para ancoragem, não uma nova publicação.
Títulos de publicações não herdam o limite de 160 do título pedagógico do projeto;
respeitam o teto documental de 20.000, inclusive quando excedem 160 caracteres.

Procedência pode apontar para documento sem conceito (`concept_id = null`).
Para `ai_suggested`, esse nulo é obrigatório: nem IDs editoriais reais nem IDs
OpenAlex podem ser atribuídos por essa origem. Uma resolução científica
independente deve ter procedência autorizada própria; a sugestão pedagógica
não substitui essa resolução.
Quando há consulta científica, data UTC ISO 8601, indicador de cache e URL
HTTP/HTTPS sem credenciais são obrigatórios juntos. Em metadados de artigo,
esses valores devem coincidir com o Paper recuperado; a data não é atualizada
para fingir uma nova consulta. Uma quote fornecida é literal e não vazia;
um conceito vindo de tópicos/palavras-chave pode ter `quote = null`, pois essas
partes do registro não integram o conteúdo textual de ancoragem.

`SourceAnchor.occurrence` é inteiro >= 0; booleanos e floats são rejeitados.
`locate` exige documento com ID correspondente e verifica a ocorrência literal,
sensível a maiúsculas e acentos. Ocorrências sobrepostas contam: `aba` ocorre
duas vezes em `ababa`. Os offsets retornados são índices de caracteres Python,
somente uma utilidade do backend; não são offsets UTF-16 nem campos do JSON.
Sem texto docente, a âncora aponta para o documento de conceitos ou para os
metadados reais, nunca para um documento criado pela IA.

Origem `material` tem `paper_ids = []` e `analysis_id = null`. `doi` possui apenas
documentos de metadados reais; `mixed` possui metadados e material docente.
Todos os documentos de um contexto pertencem ao mesmo projeto. Uma investigação
real pode preencher `analysis_id` nas origens com artigo; os exemplos deixam
esse campo nulo para não inventar uma investigação persistida.

## Interface de recuperação para T03 — somente registrada

Forma proposta para o próximo ticket, ainda sem implementação:

```python
def search_context_contributions(
    context: ScientificContext,
    *,
    comparison_paper: Paper | None = None,
) -> list[DiscoveryMatch]: ...
```

Pré-condição: contexto com referências já conferidas; `comparison_paper`, quando
fornecido, é o artigo real vinculado em `paper_ids`. No MVP, é o único artigo de
comparação. T03 deverá reutilizar os aliases, seleção, elegibilidade e ordenação
existentes e preservar `search_contributions(paper)` como entrada compatível.
Esta proposta e o nome precisam de concordância dos consumidores antes de T03.

Somente contribuições verificadas, identidades verificadas e evidências
documentais/históricas verificadas da contribuição são elegíveis. Participantes,
afirmação, URLs, IDs e limitações canônicos permanecem preservados. Candidatos
automáticos pendentes não entram nesse conjunto. Ranking: quantidade de conceitos
correspondentes, depois ID; RNA exige `mrna` ou `nucleoside`, não basta
`rna-immunity` isolado. Toda correspondência é `RELATED_TO`.

Comparação bibliográfica independente da relação temática:

| Estado | Significado preservado |
|---|---|
| `CITED` | ID persistente encontrado nas referências recuperadas |
| `NOT_FOUND_IN_RETRIEVED_REFERENCES` | IDs conhecidos não encontrados no conjunto recuperado, cuja completude não foi auditada |
| `UNKNOWN` | Sem artigo comparável, referências indisponíveis, identidade bibliográfica incompleta ou comparação do artigo consigo mesmo |
| `THEMATIC_ONLY` | A contribuição não tem publicação associada identificável |

Em origem mista, apenas o artigo vinculado é comparado. Sua bibliografia não é a
bibliografia do material docente. Sem cobertura, contexto válido e lista vazia,
com aviso explícito do limite do catálogo. Sem conceitos resolvidos, o modelo
rejeita `limitations = []`; cada elemento deve ser não vazio. Ausência de
contribuições elegíveis mesmo com conceitos, como RNA inespecífico ou conceitos
fora do catálogo editorial, também exige aviso nos resultados: as fixtures
registram isso, e o motor futuro deverá aplicar a regra sem duplicar sua seleção
nos schemas desta fatia. Nenhum estado prova intenção, omissão,
discriminação ou influência histórica.

## Convenção consolidada dos PRs #15 e #16

Decisão do usuário: #15 como base; quatro melhorias selecionadas do #16
(`5d9d7f77463b2f9a3340870784e2cc7d0ecbbb9f`). A proposta e os impactos foram
[registrados na Issue #2](https://github.com/zazacknazzo/Matilda-mvp/issues/2#issuecomment-6326394436)
antes da edição. A integração continua dependente do acordo B/C/D.

| Divergência | Convenção única preservada/adotada |
|---|---|
| `validate_references` versus `validate_sources` | Manter a interface do #15 |
| `locate` com sobreposição versus `validate_source` sem sobreposição | Manter `locate` e a contagem do #15 |
| Metadados completos versus título isolado | Exigir título + resumo real quando disponível, como no #15 |
| DOI normalizado versus entrada já canônica obrigatória | Manter normalização Forensics do #15 |
| Respostas TypeScript completas versus opcionais de entrada | Manter tipos serializados, defaults e nulos explícitos do #15 |
| Envelopes/nomes de fixtures diferentes | Manter os sete exemplos e envelope do #15 |
| Conteúdo/quotes sem teto uniforme | Adotar teto documental comum de 20.000 e preservar limites da lista de conceitos |
| IA com ID científico | Adotar rejeição de `ai_suggested` com `concept_id` não nulo |
| Contexto vazio sem limitação | Adotar limitação obrigatória sem conceitos e auditar exemplos sem sugestões |
| Baseline de três versus dez snapshots | Incorporar expectativas congeladas dos dez, reutilizando registros do #15 |

Não foram incorporados o Protocol ScientificRetriever, o tipo ScientificMatch,
o segundo verificador TypeScript ou cenários duplicados do #16. A interface de
recuperação acima continua apenas documentada. Nenhuma branch foi mesclada.

## Exemplos e linha de base

Leia o [índice das fixtures](../tests/fixtures/studio/scientific/README.md).
Os JSON de DOI preservam Paper e DiscoveryMatch serializados a partir dos
snapshots reais versionados, incluindo cache, participantes, afirmações e limites.
Os testes HTTP comparam as respostas completas com esses exemplos congelados.
O índice `forensics-baseline.json` incorpora as expectativas dos dez snapshots do
#16. Três entradas referenciam diretamente os exemplos DOI existentes; as outras
sete referenciam os registros congelados de contribuição/pesquisadores/evidências
e guardam somente as diferenças de cada retorno. O teste recompõe o JSON completo
**a partir de fixtures**, sem gerar expectativas pelo motor ou catálogo atual.
Os resultados esperados de texto/misto são exemplos de contrato para T03; não
representam uma recuperação Studio executada ou uma API de produção.

Baseline antes da implementação, em 21/10/2026: **59 testes backend aprovados**,
Python 3.14.7, Pydantic 2.13.4, HTTPX 0.28.1. A dependência Starlette instalada
emite um aviso de depreciação de HTTPX/TestClient, já presente nesse baseline.
Nenhuma dependência do projeto foi alterada.

Verificações reproduzíveis (dependências conforme README):

```sh
.venv/bin/python -m pytest backend/tests/test_scientific_context_contract.py -q
.venv/bin/python scripts/check_scientific_contract.py
make test
make build
# Com API e frontend em execução, cache dos snapshots e Chromium instalado:
cd frontend
npm run test:e2e
```

A validação não exige chave Gemini nem chamada científica externa. Resultados
finais de execução e revisão são registrados no PR vinculado à Issue #2.

Execução inicial do PR #15 em 21/10/2026: **128 testes backend aprovados**
(59 anteriores + 69 de contrato/compatibilidade), **7 fixtures compiladas contra
TypeScript**, **build TypeScript/Vite aprovado** e **6 testes Playwright
aprovados** com frontend/API reais e SQLite temporário. Ambiente frontend:
Node 26.10.0, Vite 6.4.5, Chromium 156.0.8078.4. A descoberta externa nos testes
de navegador conserva os mocks já declarados na suíte existente. Isso comprova
regressão do Forensics, não integração ou geração real do Studio.

Após a consolidação seletiva com #16, os mesmos comandos passaram com **158
testes backend** (59 anteriores + 99 de contrato/compatibilidade), **7 fixtures
TypeScript**, **build TypeScript/Vite** e **6 testes Playwright** aprovados.
Foram adicionados 30 casos de regressão/validação; as expectativas completas dos
dez snapshots são recompostas sem duplicar os registros científicos congelados.
Mantidos ambiente, snapshots, mocks declarados e aviso preexistente do TestClient.

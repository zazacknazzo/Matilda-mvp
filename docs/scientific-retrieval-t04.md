# Recuperação compartilhada — T04 / Issue #5

O Forensics mantém `search_contributions(paper)` e seus retornos anteriores.
Esse wrapper e a entrada por contexto usam a mesma seleção documental, filtro
específico de RNA e ordenação por quantidade de conceitos e ID. Os modelos
ScientificContext, SourceDocument, DiscoveryMatch e os contratos Studio de M0
permanecem os já integrados à main.

## Consumo por B

```python
from app.schemas.scientific_context import SourceDocument
from app.services.scientific_context import build_scientific_context
from app.services.contribution_search import search_context_contributions

document = SourceDocument(
    id=server_document_id, project_id=project.id, type='text',
    title='Material do professor', content=original_material,
)
context = build_scientific_context([document])
matches = search_context_contributions(context)
```

Para conceitos, usar `type='concept_list'`, um termo por linha. Os limites são
os do SourceDocument existente. O adaptador preserva conteúdo, acentos e espaços;
resolve somente aliases editoriais com os mesmos limites de palavra e
normalização do Forensics. Registra a entrada docente e quotes literais das
correspondências, sem transformar termos desconhecidos em IDs científicos.

Para DOI ou investigação já recuperada, B fornece o Paper real e seu documento
`paper_metadata`, com título real e conteúdo `paper.title` seguido de
`'\n\n' + paper.abstract` quando houver resumo:

```python
context = build_scientific_context(
    [metadata_document, material_document],
    papers=[analysis.paper], analysis_id=analysis.id,
)
matches = search_context_contributions(context, comparison_paper=analysis.paper)
```

Omitir `material_document` produz origem `doi`; incluí-lo produz `mixed`.
`analysis_id` é opcional e só deve ser fornecido para investigação resolvida.
O MVP aceita um artigo comparável. DOI/cache/resolução da investigação continuam
nos serviços existentes; o adaptador recebe os objetos prontos e não faz rede,
persistência, criação de investigação ou chamada de IA.

`build_scientific_context` gera o ID do contexto, deriva procedência/cache do
Paper sem atualizar artificialmente a data e executa `validate_references` com
os documentos, catálogo e artigos reais. B continua responsável por ownership,
expiração, resolução dos IDs e construção dos documentos no servidor. Não
confiar em documentos, Papers ou contextos reenviados pelo cliente ou pela IA.

Ao chamar `search_context_contributions` diretamente com um contexto armazenado,
as referências devem estar previamente conferidas pelo servidor via
`context.validate_references(documents, concepts=editorial_concepts, papers=papers)`.
O Paper opcional deve pertencer ao contexto. Sem ele, a comparação é `UNKNOWN`
ou `THEMATIC_ONLY` para contribuição sem publicação associada. Na origem mista,
a bibliografia continua sendo exclusivamente a do artigo vinculado; conceitos
exclusivos do material não são atribuídos ao artigo na explicação.

O adaptador acrescenta limitação explícita quando nenhum registro elegível é
encontrado, inclusive imunogenicidade isolada. Isso não indica inexistência de
contribuições femininas. Pendências de contribuição, identidade ou evidência,
fontes meramente temáticas e evidências de outra contribuição são excluídas
pelo mesmo núcleo. Participantes, fontes e relação `RELATED_TO` são preservados.

## Validação

```sh
.venv/bin/python -m pytest backend/tests/test_scientific_context.py -q
make test
.venv/bin/python scripts/check_scientific_contract.py
.venv/bin/python scripts/check_studio_contract.py
node scripts/check_lesson_types.mjs
make build
# API e frontend em execução conforme README:
cd frontend
npm run test:e2e
node node_modules/@playwright/test/cli.js test --config playwright.lesson.config.ts
```

As expectativas HTTP completas dos dez snapshots, incluindo contribuições,
ordenação, evidências e classificações, continuam nos testes científicos de M0.
Os testes novos exercitam a fronteira pública de contexto autorizada pela Issue
#5; não há endpoint textual de produto nesta entrega. Texto e DOI usam fixtures
compartilhadas. A prosa ilustrativa da fixture mista menciona um artigo de CRISPR:
o teste compara todos os campos científicos e verifica separadamente o alcance
da explicação/limitações para não fixar essa frase em outros domínios.

Esta entrega não implementa rotas Studio, planner, validação de geração,
persistência, navegação ou UI dos tickets seguintes. A revisão por outro
integrante e integração via PR continuam necessárias antes do merge.

# T02 / issue #3 — proposta LessonBundle v1

Contrato aditivo preparado para Rafael, com base em `docs/spec-mvp-v4.md`, seção 6.
Não altera Forensics, contratos científicos, endpoints, persistência ou UI.
Não implementa slides/exportações: T08 (#9) e T11 (#12) têm aceites próprios.

## Consumo por B/C/D

- Backend: importar `LessonBundle` de `app.schemas.lesson`.
- Frontend: importar `LessonBundle` e o union `ContentBlock` de
  `frontend/src/types/lesson.ts`. Não manter uma cópia do contrato no renderer.
- Exemplos: `tests/fixtures/studio/lessons/`. São objetos de aula completos,
  sem envelope HTTP novo. `provider=fixture` e `model=not-generated` identificam
  que não foram produzidos pelo Gemini nem pertencem a um professor real.
- Schema independente: `LessonBundle.model_json_schema()`, sem importar motor,
  Paper ou ScientificContext. Não altera o OpenAPI dos endpoints existentes.

JSON usa snake_case, `schema_version=1`, minutos inteiros e datas ISO 8601 UTC.
Todos os modelos novos são estritos e rejeitam campos extras, inclusive nos blocos.
Listas não aceitam null. Apenas subtitle e contagens de tokens podem ser omitidos
ou null (default null). Strings são texto simples, nunca HTML confiável.

`metadata` é a única fonte de título, disciplina, nível, duração, objetivos,
conhecimentos prévios (`prior_knowledge`) e materiais (`materials`). Seções e
atividades usam `objective_indexes` de base zero nessa lista aprovada.
O servidor deve preservar os valores configurados/aprovados pelo professor em T09;
validade estrutural sozinha não prova aprovação docente.

O plano percorre `sections` na ordem da lista, resolve `slide_ids` e `activity_ids`
nas coleções do bundle e lê os mesmos blocos/fontes usados pelos slides. Cada slide
e atividade pertence a exatamente uma seção e é referenciado exatamente uma vez.
Atividades não têm duração separada: seu tempo já integra os slides/seção.
Seções somam exatamente metadata.duration_minutes; slides de cada seção somam
exatamente a duração dela. Tolerância zero, sem truncamento ou correção silenciosa.

Blocos discriminados:

| type | Campos além do discriminador |
|---|---|
| text | text |
| bullets | items não vazios |
| steps | 2–6 items não vazios |
| question | text |
| evidence_claim | somente evidence_id |

Layouts: TITLE, CONCEPT, PROCESS, SCIENTIST_SPOTLIGHT, QUESTION e SUMMARY.
PROCESS exige steps, QUESTION exige question, CONCEPT exige text/bullets e
SCIENTIST_SPOTLIGHT exige contribuição e evidence_claim. Notas são campo separado
`speaker_notes`, destinado ao plano/painel docente, nunca à projeção. Renderização
16:9, fullscreen, teclado e escaping de texto em React serão verificados em T08.

Limites: 3–8 seções, 4–12 slides, 1–4 atividades, duração 10–120 minutos, até
6 blocos por slide, título do slide até 100 caracteres, texto pedagógico visível
até 600 caracteres (incluindo título/subtítulo), notas até 1.500 e afirmação
documental até 1.500. Caracteres são pontos de código Unicode; o renderer deve usar
`Array.from(text).length` se repetir a contagem. Documentos não são truncados.
Bundle serializado em UTF-8 tem limite de 128 KiB; T03/T09 também devem controlar
o corpo HTTP e a saída bruta do provedor antes da desserialização.

## Compatibilidade científica e fronteira de confiança

IDs científicos permanecem referências externas. O bundle não embute nem redefine
ScientificContext, pesquisador, contribuição ou Paper. Seu vínculo ao contexto
autorizado é o preview_id/project_id/review_revision resolvido pelo servidor.
Isso permite revisar T02 sem escolher entre as propostas T01 dos PRs #15/#16.
Não se declara que essas propostas concorrentes estejam reconciliadas.

`references` contém snapshots canônicos deduplicados das evidências efetivamente
usadas por blocos nos slides/seções. Não contém fonte não utilizada nem artigo de
entrada disfarçado de evidência de atribuição. A eventual apresentação do material
de base separado será acordada na API; nenhum novo campo foi inventado para isso.

`LessonReference` conserva campos do Evidence existente, participantes coletivos,
IDs de pesquisadoras, limitações e procedência (`retrieved_at`, `from_cache`).
Os exemplos copiam evidências e participantes exatos do catálogo e datas de seus
snapshots reais. Campos documentais são preenchidos pelo servidor; não são texto
livre produzido pelo modelo ou editável pelo professor. O renderer resolve:

```text
evidence_claim.evidence_id → references[id].claim_supported / source_url
```

`contribution_ids` e `evidence_ids` de cada slide coincidem exatamente com seus
blocos e fontes. Fonte pendente, apenas temática ou bibliográfica não é aceita
como referência documental verificada. A aula sem enriquecimentos possui fontes
vazias, nenhum spotlight e limitação explícita; não exige inventar uma cientista.

Após `LessonBundle.model_validate(payload)`, T09 deve chamar
`bundle.validate_authorized_references(allowed)` com um mapa de LessonReference
construído **no servidor a partir das sugestões aceitas da revisão congelada**.
O método rejeita evidência canônica real fora dessa revisão e snapshot adulterado.
Nunca construir `allowed` com os dados da resposta do modelo.

Antes disso, T09 precisa conferir sessão/propriedade, revisão, objetivos aprovados,
elegibilidade da contribuição/identidades e pertencimento ao contexto. Essas
verificações não podem ser inferidas do JSON do bundle. Aqui não há endpoint nem
alegação de autorização de produção. T03 importa os modelos acordados em vez de
redefinir EvidenceReference/GenerationMetadata concorrentes; os nomes prefixados
LessonReference/LessonGenerationMetadata delimitam a proposta de T02.

## Exemplos, validação e revisão

- `crispr-50.json` e `rna-50.json`: seis layouts, três seções, atividade avaliativa,
  notas e fontes reais; a soma é 50 minutos nas duas visualizações.
- `no-enrichment-50.json`: zero enriquecimentos, sem spotlight ou fontes inventadas.
- `optional-fields.json`: ausência de subtitle/tokens e listas pedagógicas vazias.
- `authorized-references.json`: autoridade somente de teste; auditar contra
  catálogo/snapshots no teste, não carregar esse arquivo em produção.
- `invalid.json`: mutações declarativas compartilhadas; cada caso nomeia fixture,
  caminho de chaves/índices e valor a substituir. Inclui duração, layout, vínculo,
  evidência indevida/pendente, texto histórico livre e limites excedidos.

Verificado em 21/10/2026 sobre main `d56b3f9b04bc3c8983e60cc1bfa3aca6b1241da3`:
Windows, Python 3.14.6, Pydantic 2.13.4, pytest 9.1.1, Node 26.5.1,
TypeScript 5.9.3 e Vite 6.4.5. Sem mudanças nas dependências. Resultados:

- 136 testes backend aprovados: 59 anteriores e 77 novos de contrato.
- Quatro JSONs válidos compilados contra os tipos TypeScript sem casts.
- Build TypeScript/Vite aprovado.
- Aviso preexistente Starlette/TestClient com httpx, sem falhas.
- Sem chamadas científicas externas, IA, exportação ou testes de navegador;
  não há UI nova nesta fatia. Strings HTML maliciosas continuam literais e links
  inseguros são rejeitados; execução/escaping no renderer será testado em T08.

Reprodução após instalação conforme README:

```powershell
.venv/Scripts/python.exe -X utf8 -m pytest backend/tests -q
node scripts/check_lesson_types.mjs
npm.cmd --prefix frontend run build
```

Neste ambiente foi reutilizado o interpretador do checkout anterior com as mesmas
dependências (`../Matilda-mvp/.venv/Scripts/python.exe`) e diretório temporário
exclusivo `../pytest-issue-3`. O código testado é o deste checkout, via conftest.

Proposta/impactos registrados na issue antes da preparação. Falta revisão de B
para geração estruturada, A para uso científico, C/D para consumo e registro de
acordo antes da integração/congelamento. Não houve ensaio Gemini ou revisão por
especialista independente. T08 (#9) continua bloqueada enquanto T02 não estiver
integrada e estabilizada; esta entrega não declara M0 encerrado.

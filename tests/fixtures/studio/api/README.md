# Studio HTTP — fixtures T03 v1

Contrato em [`docs/studio-contracts.md`](../../../../docs/studio-contracts.md).
São dados de teste/revisão, não respostas de produto nem fallback de produção.

- `*-preview.json`: seis EnrichmentPreview completos. text/crispr/rna/mixed/
  no-coverage estão revisados; pending é a resposta inicial sem decisões. Preservam
  documentos e ScientificContext T01 e importam os snapshots LessonReference T02.
- `requests.json`: inputs para texto, DOI, RNA, misto, sem cobertura e analysis_id;
  revisão/objetivos e geração com zero ou mais aceitas. A ordem dos cinco primeiros
  casos é text, crispr, rna, mixed, no-coverage. São jornadas independentes.
- `http-examples.json`: método/path/status, headers/cookie de teste e referências
  `{fixture, path}` para os payloads. Resolver path como sequência de chaves/índices;
  `../lessons/crispr-50` reutiliza a aula existente, sem copiá-la. Os dois POST
  generate compartilham a mesma chave/entrada/bundle e ilustram 201 → replay 200.
- `errors.json`: envelopes e status; headers são strings HTTP, incluindo Retry-After.
- `invalid.json`: substituir `value` no `path` de uma cópia da fixture; o modelo
  deve rejeitar. Inclui versão, campos históricos, vínculos, retenção e estados.
- `provider-cases.json`: transporte simulado de teste, incluindo bytes JSON
  inválidos e falhas sanitizadas. T09 deve exercitar esses casos no validador real;
  este smoke do port não declara geração, quota ou proteção semântica reais.

`preview_id=preview-example`/`project_id=project-example` permitem vincular cada
jornada isolada aos LessonBundle existentes. Esses IDs/cookie são sintéticos e
não representam registros persistidos ou uma sessão válida do produto.
`provider=fixture`, `model=not-generated` e datas declaradas identificam a origem.
Fontes científicas, afirmações e participantes são os registros reais versionados.

Requests originais têm objectives vazios; sugestões não os substituem. Os dois
objetivos aprovados aparecem separadamente. A primeira sugestão é aceita e a
segunda rejeitada; só a evidência aceita pode compor a aula. Sem cobertura não há
sugestões/referências, mas a geração sem enriquecimento é permitida após revisão.

Usar `.venv/bin/python scripts/check_studio_contract.py` para validar e compilar os
mesmos payloads Pydantic/TypeScript. Os validadores de autoridade recebem dados
resolvidos pelo servidor; não usar as respostas de prévia como sua própria autoridade.

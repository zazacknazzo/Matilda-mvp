# Exemplos científicos compartilhados — schema_version 1

Fixtures exclusivamente de teste/revisão M0. Não são respostas de endpoints Studio
implementados nem caminho de sucesso para produção. Ler também
`docs/scientific-context-m0.md` para validação e interface proposta.

Cada cenário contém `source_documents`, `scientific_context`, `anchors`,
`paper_dois` (lookup nos snapshots reais existentes) e `expected_matches`
(DiscoveryMatch existente). O envelope serve ao teste; não define uma nova API.

| Arquivo | O que conferir |
|---|---|
| crispr-doi.json | DOI CRISPR real, procedência OpenAlex, evidências e autoria coletiva |
| rna-doi.json | DOI NEJM real, conceitos específicos e contribuições de Karikó |
| text-no-doi.json | Texto literal, segunda ocorrência de CRISPR, paper_ids vazio, UNKNOWN |
| mixed.json | Artigo CRISPR + lista docente de conceitos com RNA; procedências distintas |
| rna-material.json | Lista docente específica de RNA, sem Paper, comparação UNKNOWN |
| no-coverage.json | Material válido, conceitos/sugestões vazios e aviso de cobertura |
| rna-insufficient.json | Imunogenicidade identificada; nenhuma contribuição RNA elegível |

`invalid.json` contém mutações declarativas dos exemplos acima: nome, fixture
base, alvo, caminho de chaves/índices e valor substituto. O teste aplica a mutação
e exige rejeição. Inclui conceito desconhecido, evidência canônica real de outra
contribuição, evidência/identidade/contribuição pendentes, fonte apenas temática,
Paper inventado, label errado, procedência/âncora não literal e RNA insuficiente.

`forensics-baseline.json` contém o retorno original completo para cada um dos dez
DOIs dos snapshots do catálogo. Fontes, IDs, afirmações e todos os participantes
foram copiados dos registros existentes; os dados editoriais não foram alterados.

Para material sem DOI, os resultados esperados são exemplos do contrato futuro:
elegibilidade foi conferida com o catálogo/motor atual em teste, substituindo apenas
os conceitos de um Paper real como instrumento do teste. Não há Paper sintético
persistido nem adaptador material em produção. O estado de comparação esperado é
UNKNOWN; THEMATIC_ONLY sem publicação associada é coberto por teste isolado, sem
inventar uma nova contribuição no catálogo editorial.

O teste backend valida as fontes e compara os snapshots; o script
`node scripts/check_scientific_types.mjs` compila os sete JSONs válidos contra os
tipos novos. Não utilizar assertions TypeScript para esconder incompatibilidades.

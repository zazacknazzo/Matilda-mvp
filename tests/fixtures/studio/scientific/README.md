# Exemplos científicos compartilhados — v1 / T01

Consumidores B/C/D: importar estes JSON como dados de teste. Não os utilizar como
fallback de produção. Contrato e chamada dos validadores em
[`docs/scientific-context.md`](../../../../docs/scientific-context.md).

Cada exemplo válido contém `source_documents`, `scientific_context`, `papers`,
`anchors` e `expected_matches`. Esse objeto é um **envelope de fixture**, não uma
nova resposta HTTP. Papers são registros reais dos snapshots versionados;
`papers = []` significa que não há artigo, autores ou bibliografia artificiais.

| Arquivo | O que conferir |
|---|---|
| `crispr.json` | DOI `10.1126/science.1231143`, metadados/cache e baseline exato Forensics |
| `rna.json` | DOI `10.1056/nejmoa2034577`, especificidade RNA e autoria coletiva |
| `text.json` | Texto sem DOI, dois conceitos editoriais; segunda ocorrência literal de CRISPR; citações `UNKNOWN` |
| `mixed.json` | Artigo CRISPR + conceito docente de mRNA; origem de cada conceito separada; comparação somente com o artigo |
| `no-coverage.json` | DOI real `10.1038/171737a0`, conceitos reais sem contribuições elegíveis |
| `uncovered-text.json` | Material sem cobertura; nenhuma contribuição inventada; aviso explícito |
| `rna-insufficient.json` | Contexto válido, mas imunogenicidade isolada não torna RNA elegível |

`expected_matches` dos três exemplos DOI são respostas congeladas do Forensics
atual. Nos casos texto e misto são expectativas documentadas para o futuro T03,
com registros canônicos existentes, e não resultados de um adaptador já
implementado. Campos científicos dos matches são os modelos Forensics atuais.
Relação temática não implica influência histórica; ausência de cobertura não
implica inexistência de contribuições femininas.

| Contraexemplos | Como reproduzir |
|---|---|
| `invalid-contexts.json` | Carregar `fixture`, substituir o valor no `path` por `value`, esperar erro estrutural ou de referências/âncora |
| `ineligible-catalog.json` | Aplicar `changes` em cópia temporária dos arquivos de catálogo e conferir `expected_ids` pela recuperação Forensics atual |

Contraexemplos de catálogo abrangem identidade, evidência e contribuição pendentes,
evidência de outra contribuição e fonte meramente temática. Nunca modificar o
catálogo real ao consumir esses exemplos. Conceito desconhecido, label errado,
documento/projeto incorreto, trecho/ocorrência inexistente, metadados inventados e
cache adulterado são rejeitados pelos validadores, sem consultar fontes externas.

Antes de integrar, A/B/C/D devem registrar revisão e acordo explícito em M0.
Esta pasta, sozinha, não constitui esse aceite.

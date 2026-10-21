# LessonBundle v1 — fixtures de contrato T02

Somente testes e revisão M0. Nenhum arquivo representa geração real de IA,
endpoint implementado ou aula persistida de um professor. Não importar fixtures
no build de produção nem exibi-las como resultado de uma geração.

`crispr-50.json` e `rna-50.json` são aulas de 50 minutos com seis layouts e
evidência real do catálogo. `no-enrichment-50.json` exercita aula sem atribuições
históricas. `optional-fields.json` demonstra campos opcionais e listas vazias.

`authorized-references.json` é o mapa confiável somente para os testes de aceitação
documental; testes o conferem com o catálogo/snapshots reais. Em produção esse
mapa será construído da revisão aprovada no servidor, nunca de um fixture ou da IA.

`invalid.json` descreve mutações dos exemplos válidos com nome, fixture base,
caminho e valor substituto. Os testes exigem que cada mutação seja rejeitada.

Os JSONs válidos são usados tanto por Pydantic quanto por
`node scripts/check_lesson_types.mjs`. Guia de campos, invariantes, consumo e
limitações de integração em `docs/lesson-contract-m0.md`.

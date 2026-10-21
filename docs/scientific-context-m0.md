# T01 — contrato científico M0, versão 1

Proposta aditiva para [issue #2](https://github.com/zazacknazzo/Matilda-mvp/issues/2),
baseada na especificação aprovada em `docs/spec-mvp-v4.md`. Preparada em branch
independente; aguarda revisão de outro integrante e acordo B/C/D. Não encerra M0
nem autoriza iniciar implementação paralela. A proposta e seus impactos foram
registrados na discussão da issue antes da preparação destes artefatos.

## Modelos e validação

`backend/app/schemas/scientific_context.py` define somente SourceDocument,
Provenance, SourceAnchor, ScientificContext e a declaração ScientificRetriever.
Os modelos existentes, catálogo, armazenamento, endpoints e motor não mudam.
Os tipos correspondentes ficam em `frontend/src/types/scientific-context.ts`.

Novos modelos rejeitam extras e coerção de tipos. Campos opcionais aceitam null;
listas com default são vazias, nunca null. Datas de consulta exigem ISO 8601 UTC.
IDs são opacos e devem ser gerados pelo servidor na implementação futura.

Há duas etapas obrigatórias para o consumidor servidor:

1. `ScientificContext.model_validate(payload)` valida estrutura, origem,
   alinhamento posicional de conceitos/labels, duplicatas e vínculos internos.
2. `context.validate_sources(source_documents=documents, concepts=resolved,
   papers=real_papers)` confere os vínculos com registros de confiança resolvidos
   pelo servidor. Não passar conceitos ou Papers produzidos pela IA como autoridade.
   As referências de documentos/artigos devem coincidir exatamente com o contexto;
   conceitos resolvidos podem incluir um conjunto maior do catálogo.

`SourceAnchor.model_validate(payload)` valida a forma; em seguida chamar
`anchor.validate_source(document)`. A ocorrência começa em zero; a busca é literal,
sensível a maiúsculas, sem normalização, da esquerda para a direita e sem sobreposição.
`aaaa` tem duas ocorrências não sobrepostas de `aa`. Aspas inexistentes e ocorrência
fora do documento são inválidas. Espaços originais não são removidos.

Convenção dos exemplos de SourceDocument: texto guarda o material literal; lista
de conceitos usa uma entrada por linha (1–20 entradas, até 100 caracteres cada);
metadados guardam o título real ou título + duas quebras de linha + resumo real.
Metadados exigem DOI canônico e correspondência com o Paper recuperado. Título tem
até 160 caracteres e conteúdo até 20.000. DOI reutiliza o normalizador e limite
efetivo de 250 caracteres do Forensics; URLs arbitrárias não são aceitas como DOI.
Esses modelos não fazem chamadas de rede. A imutabilidade por prévia, autorização,
expiração e persistência serão aplicadas pela API em T03/T05.

Procedência OpenAlex exige data, indicador de cache e URL iguais aos do artigo
recuperado, além de conceito presente nele. `from_cache=false` é valor válido.
Aliases editoriais usam `contains` do Forensics: mesmos acentos, normalização e
limites de palavras. `ai_suggested` não pode resolver um concept_id; rótulos
pedagógicos sugeridos ficam separados da lista científica.

## Interface de recuperação a implementar em T04

`ScientificRetriever(context, *, comparable_paper=None) -> list[DiscoveryMatch]`
é um Protocol, sem implementação e sem registro de rota HTTP.

Pré-condição: contexto e documentos já validados contra registros do servidor.
Para `doi` e `mixed`, passar o único Paper real identificado por `paper_ids`.
Para `material`, não passar Paper nem criar investigação. A entrada anterior por
Paper continuará como adaptador compatível quando T04 for implementada.

O retorno deve preservar seleção, elegibilidade, participantes, evidências,
limitações e ranking do motor: conceitos correspondentes em ordem decrescente,
desempate por ID de contribuição. Somente contribuição verificada, identidades
verificadas e evidência documental/histórica verificada da contribuição correta
são elegíveis. Candidatos automáticos não entram nesse conjunto.

Toda correspondência conceitual continua RELATED_TO. Imunogenicidade isolada não
habilita contribuições de RNA: exige mrna ou nucleoside. Comparação bibliográfica
é independente da correspondência temática:

| Estado | Significado preservado |
|---|---|
| CITED | ID associado encontrado nas referências recuperadas |
| NOT_FOUND_IN_RETRIEVED_REFERENCES | IDs conhecidos não encontrados no conjunto recuperado, de completude não auditada |
| UNKNOWN | Sem artigo comparável, referências indisponíveis, identidade bibliográfica incompleta ou autocitação impossível |
| THEMATIC_ONLY | Contribuição sem publicação associada identificável |

Em origem mista, usar exclusivamente as referências do Paper vinculado, incluindo
para contribuições relacionadas aos conceitos adicionais do material. Não tratar
isso como bibliografia do texto docente. Sem cobertura, retornar lista científica
vazia e limitação explícita; não inventar pesquisadoras, Paper ou evidências.

## Verificação em 21/10/2026

Base: `d56b3f9b04bc3c8983e60cc1bfa3aca6b1241da3`. Windows, Python 3.14.6,
Pydantic 2.13.4, FastAPI 0.141.1, pytest 9.1.1, Node 26.5.1, TypeScript 5.9.3,
Vite 6.4.5. Dependências Python instaladas de `backend/requirements.txt`;
frontend de `package-lock.json`. Nenhuma chave Gemini ou chamada científica externa.

- Baseline antes dos novos testes: 59 testes backend aprovados.
- Suíte completa: 142 aprovados, sendo 83 novos casos de contrato/regressão.
- Sete fixtures JSON compartilhadas aprovadas em TypeScript.
- Build TypeScript/Vite aprovado. Nenhum componente de UI alterado; navegador
  E2E não executado nesta fatia de contratos.
- Aviso existente de depreciação Starlette/TestClient com httpx; sem falhas.

Comandos na raiz, após instalar as dependências como no README:

```powershell
.venv/Scripts/python.exe -X utf8 -m pytest backend/tests -q --basetemp=../pytest-issue-2
node scripts/check_scientific_types.mjs
Push-Location frontend
npm.cmd run build
Pop-Location
```

`-X utf8` evita a decodificação cp1252 dos snapshots no Windows. O basetemp deve
ser um diretório exclusivo de testes: pytest limpa esse diretório ao executá-lo.
Usar a área temporária permitida do ambiente. As primeiras tentativas locais sem
UTF-8/acesso adequado a temporários não concluíram a suíte; os resultados acima
são da execução completa com ambiente corrigido, sem mudanças no Forensics.

`forensics-baseline.json` congela os retornos completos dos dez snapshots atuais,
incluindo participantes, fontes, ordem e estados; não atualizar para mascarar
regressões. Dois testes HTTP comparam CRISPR/RNA com essas fixtures. Os demais
testes auditam textos sem Paper, procedência distinta em origem mista, fronteiras
de aliases, âncoras, limites e rejeição de elegibilidade inválida pelo motor atual.

Pendências de entrega: revisão humana e registro explícito do acordo B/C/D antes
de integrar. Não foi realizada revisão por especialista científico independente.

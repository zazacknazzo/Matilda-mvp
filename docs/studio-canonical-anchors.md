# Âncoras canônicas na prévia — Issue #31 / PR #32

Base desta correção: `6816c30`, cabeça anterior de `feat/nvidia-studio`.
Não foram realizadas chamadas reais NVIDIA/Gemini nesta investigação.

## Causa e limite da evidência

O último smoke, **relatado pelo usuário**, aprovou CRISPR (201, 2,99 s, quatro
contribuições autorizadas, uma sugestão) e rejeitou RNA (NVIDIA 200, 4,29 s;
Matilda 502, invalid_source_anchor, plano válido, prévia inválida; duas
contribuições, dois documentos, uma sugestão). Não houve geração de aula.

A geração livre permitia ao modelo escrever documento, quote e occurrence.
O schema estrutural aceitava esses valores, mas não podia garantir a igualdade
literal com um dos documentos. Essa é a causa estrutural demonstrada no código
e na reprodução controlada: uma resposta HTTP/JSON válida pode violar o contrato
de localização. O relatório real não reteve os valores da âncora; **não é possível
afirmar qual dos três componentes estava errado na resposta original**.

Antes da mudança da fronteira, três mutações isoladas de uma resposta RNA
controlada reproduziram 502 com plano Pydantic válido e prévia inválida:
documento inexistente, quote não literal, ocorrência inexistente. O primeiro teste
ficou vermelho pela ausência do subcódigo, depois verde com a classificação.
O teste de seleção canônica ficou vermelho no schema antigo, que exigia âncora
livre, e verde após a implementação. O teste `xmRNA; mRNA e mRNA` ficou vermelho
com ocorrência zero e verde quando o servidor passou a contar todas as
ocorrências literais, incluindo a substring não elegível em `xmRNA`.

Loop final, sem rede:

```sh
.venv/bin/python -m pytest backend/tests/test_studio_canonical_anchors.py backend/tests/test_studio_preview_diagnostics.py -q
```

## Fronteira interna e invariantes

1. Após resolver a fonte científica, o servidor cruza proveniência por documento,
   conceitos editoriais realmente localizados e conceitos suportados pelas
   contribuições autorizadas. Não usa prefixos arbitrários do material.
2. Os aliases editoriais são localizados com as mesmas fronteiras lexicais da
   resolução científica. A normalização serve só à busca; a quote sempre é uma
   fatia **original** do documento, preservando Unicode e acentos decompostos.
3. O servidor calcula occurrence pela contagem literal exata e confere a posição
   com SourceAnchor.locate. IDs derivam de contexto da operação, documento,
   conceito e posição; são estáveis durante a correção da mesma operação e não
   são reutilizáveis em outra operação.
4. O material/schema privados oferecem source_anchor_id e as escolhas autorizadas
   para cada contribuição. Há no máximo oito escolhas, até duas ocorrências por
   conceito/documento. Primeiro se garante uma escolha para cada contribuição;
   depois se incluem alternativas, sem aumentar o orçamento de tokens.
5. O modelo escolhe o ID e o singleton concept_ids daquela âncora. O backend
   rejeita IDs desconhecidos e relações incompatíveis, confere a evidência da
   contribuição selecionada e materializa o SourceAnchor original. Campos de
   âncora livre na resposta do modelo são proibidos.
6. EnrichmentPreview e sua autoridade científica continuam sendo validados antes
   da persistência. A API pública, os tipos TypeScript, SQLite, catálogo,
   referências, participantes, aprovação docente e LessonBundle não mudaram.

A âncora indica **onde o conceito aparece no material**. A evidência histórica
continua sendo a evidência canônica da contribuição, não uma alegação inferida
a partir da ocorrência de uma palavra. Não há substituição de evidências,
correspondência fuzzy ou fatos acrescentados pelo servidor.

Se houver contribuição autorizada, mas nenhum trecho conceitual literal elegível
(por exemplo, conceito vindo somente de keyword OpenAlex sem presença no título
ou resumo), a operação falha explicitamente como missing_grounded_anchor,
retryable=false, **antes de inferência**. Não inventa cobertura, não cria citação
e não transforma esse caso em sucesso sem sugestões. O professor pode fornecer
material que contenha o conceito. Se o limite de escolhas não comportar uma
âncora para cada contribuição, também falha. Sem cobertura científica real,
choices e suggestions permanecem vazios, com as limitações explícitas existentes.

## Diagnósticos e segurança

O código público permanece invalid_generation; a telemetria usa somente códigos,
contagens e resultados de validação. O evento invalid_source_anchor inclui
anchor_error sanitizado:

| anchor_error | Significado |
|---|---|
| invalid_source_document | Documento diferente/inexistente no contrato público |
| non_literal_quote | Trecho não ocorre literalmente no documento |
| invalid_occurrence | Trecho existe, mas o índice solicitado não existe |
| unknown_anchor_id | Seleção não pertence às escolhas desta operação |
| anchor_binding_mismatch | Escolha não corresponde à contribuição/conceitos selecionados |

Os três primeiros continuam obrigatórios no contrato público de leitura e
persistência. Os dois últimos protegem a fronteira com o modelo. Nenhum evento
inclui resposta bruta, valores inválidos, quote, documento, prompt ou chave.
missing_grounded_anchor registra apenas contagens e validações ainda não executadas.

Não foram alterados os deadlines 45/75 s, teto de entrada 12.000, saída 8.000,
limite do corpo, concorrência, fallback ou retries do provedor. A operação normal
mantém até duas tentativas compartilhando deadline; **o smoke bloqueia qualquer
segunda inferência na mesma operação**, inclusive após falha de validação.
O orçamento do smoke permanece três chamadas totais / 180 s / modelo solicitado
fixo em nvidia/nemotron-3.5-super-vl-120b-a12b. Testes controlados verificam que o
bloqueio preserva o primeiro diagnóstico e não consome outra chamada.

## Validação desta correção

- Backend completo: **650 passed**, 9,15 s, incluindo regressão Forensics.
- Contratos: **7** científicos, **40** Studio HTTP e **4** LessonBundle TypeScript.
- TypeScript/build aprovado; permanece o aviso Vite de bundle acima de 500 kB.
- Playwright e revisões independentes: resultados serão registrados ao concluir.
- HTTPX MockTransport cobre RNA, CRISPR, texto sem DOI, documentos múltiplos,
  Unicode composto/decomposto, termos repetidos, ausência de cobertura,
  vínculos inválidos, IDs de outra operação, retry e recuperação da prévia anterior.
- O caso keyword-only comprova recusa antes da IA. A prévia pública continua
  rejeitando cada erro de documento/quote/ocorrência separadamente.

Os testes simulados validam o contrato enviado e as verificações do backend;
não comprovam qualidade pedagógica ou sucesso do novo schema no compilador live.
Nenhuma prévia ou aula nova foi produzida por inferência real nesta correção.

## Smoke real — exige nova autorização

Com dependências instaladas no checkout atualizado e chave somente no .env local:

```sh
.venv/bin/python scripts/smoke_studio_nvidia.py --env-file /caminho/local/.env --allow-paid-nvidia
```

O script verifica a chave localmente; não é necessário compartilhá-la. Executa
CRISPR e RNA, revisão de teste explícita, aula de 50 minutos, leitura persistida
e exportação Markdown. Interrompe na primeira falha. O roteiro completo só é
aprovado após ambas as prévias e a aula válida/persistida/exportada; não há novas
tentativas pagas automáticas, fallback ou merge.

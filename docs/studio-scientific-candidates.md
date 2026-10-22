# Candidatos científicos indivisíveis — Issue #31 / PR #32

Base: `32562f5`, versão anterior do PR #32. Nesta correção não houve inferência
real NVIDIA/Gemini. API pública, SQLite, catálogo e limites permanecem intactos.

## Evidência real e reprodução

Terceiro teste **relatado pelo usuário**: NVIDIA 200, inferência 3.860 ms;
Matilda 413 input_too_large; PreviewPlan válido; quatro contribuições autorizadas
e uma sugestão; invalid_source_anchor / anchor_binding_mismatch. Estimativa
11.958, uso informado 2.867 entrada / 143 saída. Uma chamada externa, correção
impedida pelo orçamento. Esses valores não são novas medições desta sessão.

O JSON original não foi retido no relatório. O código distingue duas causas do
binding_mismatch: âncora não permitida para a contribuição, ou conceitos
selecionados diferentes do conceito daquela âncora. Não se afirma qual combinação
exata o modelo retornou. A falha de associação, porém, está comprovada pelo código
sanitizado real e reproduzida com transporte controlado.

O primeiro loop controlado preservou um plano válido com IDs individualmente
autorizados e trocou somente o conceito da âncora. Com quatro contribuições, uma
sugestão e estimativa calibrada em 11.958, reproduziu invalid_source_anchor /
anchor_binding_mismatch e 413 antes de outra requisição. O teste ficou vermelho
porque não havia diagnóstico específico do bloqueio corretivo. Passou após
acrescentar corrective_input_too_large, sem remover a rejeição científica.

O teste de candidate_id ficou vermelho contra o schema antigo (ainda exigia
contribution_id/concept_ids/evidence_ids/source_anchor_id) e passou após substituir
a seleção livre pela associação construída pelo servidor. O loop final de
orçamento usa candidato desconhecido: o defeito antigo foi eliminado do formato,
mas sua seleção inválida continua sendo rejeitada, nunca corrigida pelo servidor.

```sh
.venv/bin/python -m pytest backend/tests/test_studio_scientific_candidates.py backend/tests/test_studio_candidate_budget.py backend/tests/test_studio_preview_diagnostics.py backend/tests/test_studio_canonical_anchors.py -q
```

## Causa raiz e correção

Enums independentes restringiam os valores, mas ainda permitiam o produto
cartesiano: uma contribuição válida, um conceito válido e uma âncora válida
podiam formar uma tupla não autorizada. O schema do modelo tinha mais liberdade
que a associação científica permitida pelo servidor. A validação fez corretamente
seu trabalho ao rejeitar essa tupla; não deve ser enfraquecida.

ScientificCandidates concentra a construção e a resolução atrás de uma interface
pequena: material para o modelo, schema e resolução por ID. Cada candidato liga
uma contribuição verificada, um conceito elegível localizado pela proveniência,
as evidências elegíveis **dessa contribuição** e uma SourceAnchor literal exata.
A localização mantém fronteiras lexicais, Unicode original e contagem literal
correta de occurrence. Evidências e todos os participantes continuam canônicos.

PreviewPlan privado agora contém somente objetivos e sugestões com candidate_id,
pedagogical_rationale e suggested_content. O modelo não escreve mais nenhum ID
científico, documento ou âncora. O backend resolve o ID para o conjunto completo,
acrescenta os campos canônicos e executa os mesmos validadores públicos de
EnrichmentPreview/autoridade antes de publicar e persistir.

O ID deriva do contexto da operação e de toda a associação, incluindo evidências
e âncora; permanece estável no retry da mesma operação. Um ID desconhecido ou de
outra operação gera invalid_scientific_candidate. IDs extras livres, inclusive
combinações cruzadas do formato antigo, falham no Pydantic com extra=forbid.
**Não há seleção automática de outro candidato**, escolha aproximada, inventada
ou fallback. Uma tentativa corretiva normal precisa obter nova seleção válida do
modelo; no smoke ela é impedida pelo limite de uma inferência por operação.

Há no máximo oito candidatos; primeiro se garante um por contribuição e depois
alternativas. Evidências/contribuições não verificadas são recusadas na construção,
e as verificações completas de identidade/autoria continuam obrigatórias. Sem
âncora conceitual literal ou capacidade para todas as contribuições, falha antes
da IA. Sem cobertura real, candidatos e sugestões vazios mantêm a limitação
explícita. Não há enriquecimento artificial para satisfazer o schema.

## Compactação e estimativa

Documentos completos são enviados uma vez cada, com chave local/tipo/conteúdo,
sem repetir UUID de projeto, DOI, título já presente nos metadados e outros campos
administrativos. Título da contribuição e afirmações documentais ficam uma vez por
contribuição; candidatos referenciam essas entradas. Saem os mapas repetidos de
IDs/evidências, listas de associações e explicações redundantes. Instruções passam
a descrever a seleção única, sem ensinar o modelo a reconstruir tuplas científicas.
O schema mantém os limites/required/additionalProperties e passa a ter um único
enum científico. Não há downgrade para JSON livre.

Medição offline das **mesmas entradas públicas do script smoke**, na base e após
a correção. O transporte é MockTransport e retorna 401 local para capturar somente
os tamanhos, antes de qualquer geração. Não é medição de tokens reais NVIDIA.

| Cenário | Payload UTF-8 antes → depois | Redução | Estimativa antes → depois |
|---|---:|---:|---:|
| CRISPR | 10.934 → 6.467 bytes | 40,85% | 11.958 → 7.491 |
| RNA | 9.130 → 6.773 bytes | 25,82% | 10.154 → 7.797 |

Componentes: instruções 1.985 → 1.061 bytes; material CRISPR 6.361 → 3.556;
schema CRISPR 1.856 → 1.247; material RNA 4.987 → 4.000; schema RNA 1.602 → 1.173.
Os tamanhos dos componentes não somam o envelope inteiro: ele inclui configurações,
wrappers e escaping das strings JSON. [Registro de números](nvidia-preview-payload-comparison.json).

A estimativa real relatada **11.958 = 10.934 bytes + 1.024 de reserva** foi
reproduzida na entrada CRISPR pública. Ela excede o uso informado 2.867 em 9.091
(aproximadamente 4,17 vezes o uso). É um teto por bytes de todo o envelope JSON,
incluindo escaping e schema, mais reserva; não é contagem pelo tokenizer da NVIDIA.
Tokens podem representar vários bytes e o servidor pode incorporar schema/template
de forma diferente do envelope HTTP. Não se conhece a decomposição interna dessa
contagem; não se atribui um número exato de tokens a cada diferença.

A diferença não justifica dividir caracteres por quatro, calibrar uma razão por
uma única amostra nem presumir um endpoint de contagem hospedado. O contador
conservador permanece inalterado. Mantêm-se os limites 12.000 entrada / 8.000 saída,
com verificação de uso efetivo no retorno. Entradas grandes ainda podem ser
recusadas conservadoramente. A correção remove bytes repetidos do contrato.

Para repetir a medição sem créditos:

```sh
.venv/bin/python scripts/measure_studio_preview_payload.py
```

## Orçamento corretivo e estado

Antes de qualquer nova chamada, o payload corrigido completo é recontado com o
mesmo deadline absoluto. Se exceder o teto, o evento sanitizado
studio_preview_validation registra corrective_input_too_large, previous_code,
estimated_input_tokens e contagens; não registra IDs, prompt, resposta ou material.
O evento da rejeição científica original continua separado e preservado.
O envelope público continua input_too_large/413, com mensagem específica de que
a tentativa corretiva foi bloqueada e nenhuma nova inferência foi iniciada.

Testes usam o contador real e calibram o material para 11.958, 12.000 e 12.001:
correção acima do teto não faz outro HTTP; 12.000 é aceito quando a seleção é válida;
12.001 é barrado antes do transporte. Material/configuração da operação falha
continuam preservados e a prévia anterior permanece legível com seu último erro.
Não há aumento de timeouts, nova cota ou extensão de deadline para retry.

## Verificação e limitações

Backend: **656 passed**, 9,67 s, incluindo Forensics. Contratos científicos/Studio/
LessonBundle: **7/40/4**. TypeScript/build aprovado; aviso Vite de chunk >500 kB
permanece. Playwright e revisões independentes serão registrados ao concluir. Os testes exercitam somente interfaces HTTP,
transporte controlado e validadores públicos; não substituem qualidade pedagógica
e aceitação do schema no endpoint real.

O fluxo normal de revisão docente, snapshots científicos, persistência, aula,
leitura e Markdown permanece. O próximo smoke precisa comprovar ambas as prévias
e uma aula completa; esta correção não declara o Matilda pronto em produção.

## Smoke real — requer nova autorização

No checkout atualizado, com dependências e NVIDIA_API_KEY somente no .env local:

```sh
.venv/bin/python scripts/smoke_studio_nvidia.py --env-file /caminho/local/.env --allow-paid-nvidia
```

Até três chamadas / 180 segundos, modelo solicitado fixo
nvidia/nemotron-3.5-super-vl-120b-a12b: CRISPR, RNA, aula de 50 minutos, revisão
de teste, leitura persistida e Markdown. Uma inferência por operação; a primeira
falha interrompe o roteiro. Não executar sem nova autorização. Nenhuma chamada
NVIDIA real, merge ou fallback automático foi feito nesta correção.

> Atualização #31: a branch de migração seleciona NVIDIA por padrão e mantém
> Gemini como alternativa explícita. A descrição e as medições Gemini abaixo são
> o registro histórico da base T13. O [guia NVIDIA](studio-nvidia.md) registra a
> validação da migração; ensaio NVIDIA live permanece pendente.

# T13 — candidato integrado ao ensaio P0

Issue: [#14](https://github.com/zazacknazzo/Matilda-mvp/issues/14).
Base: `f7f2972a997f892102638fa75df563d5a207b3c8` (main com PR #29).
Branch: `feat/issue-14-integrated-demo`. Data: 22/10/2026.

## Implementação e módulos reutilizados

| Etapa | Módulo existente e conexão T13 |
|---|---|
| Investigação | Forensics continua responsável por DOI, artigo, grafo, classificação, descoberta e exportações. `ForensicsLessonAction` transfere o ID da investigação para a configuração confirmável do Studio. |
| Ciência | A prévia chama `resolve_scientific_source` T06, que reutiliza T04. Investigação sem novo material conserva seu snapshot; texto não ganha Paper fictício. Metadados, fontes, participantes e limitações são persistidos com a autoridade científica. |
| Preparação | `StudioSetup` aceita DOI ou investigação além de texto/conceitos. Nova origem invalida respostas assíncronas anteriores na interface. |
| Revisão | T07 conserva decisões e edições; `ScientificDossier` consome os dados canônicos da prévia M0. Com `analysis_id`, explorar abre a investigação real e seleciona a contribuição; voltar preserva edição não salva e foco. Se o link estiver indisponível, o dossiê retido continua acessível. Nenhuma classificação de citação é inventada quando o contrato não a fornece. |
| Geração | T09/T10 usam revisão aprovada e snapshot autorizado. `LessonBundle` continua único para slides, plano, referências e notas. |
| Entrega | T08/T11 já ligados por T10: sessão real, banco real, Markdown, impressão pelo navegador e apresentação. A aula salva permite explorar cada contribuição usada sem desmontar o visualizador. |
| Recuperação | T12 passa a compor o lifespan real: varredura inicial/periódica de 15 s, reconciliação de operações órfãs e métricas agregadas de geração. GET/reconexão não inicia nova geração. |

Não há novo endpoint, schema, catálogo, mock de produção ou infraestrutura.
Os adaptadores/harnesses isolados continuam restritos a testes. O backend de
produção continua construindo somente `GeminiProvider` para IA.

## Evidência automatizada e fronteiras

`backend/tests/test_studio_integrated.py` exercita HTTP FastAPI e SQLite reais:
snapshot da investigação após alteração editorial, etapas de latência, manutenção
no host e exportação. A exportação verifica sessão alheia/expirada, origem externa,
formatos/parâmetros inválidos, headers, escaping e ausência do material privado.
O provedor controlado é a única substituição de IA.

`frontend/tests/studio-integrated.spec.ts` atravessa frontend, APIs internas e
SQLite reais, sem interceptar essas APIs. O servidor de teste substitui somente
provedores externos; seus resultados trazem `model=controlled`, nunca Gemini live.
Cobre CRISPR via Forensics e RNA por DOI em aulas de 50 minutos, fontes coletivas,
edição/foco preservados, mobile, sem cobertura, falha e retry explícito, desconexão
após admissão, reload, download, projeção virtual sem notas e impressão em PDF.

| Aceite da Issue #1 | Evidência repetível nesta versão |
|---|---|
| P0-1 / CT-02,03,04,16 | testes científicos, contexto T04/T06, regressão HTTP e `investigation.spec.ts` |
| P0-2 / CT-01,05,15 | prévia HTTP e `studio.spec.ts`, `studio-integrated.spec.ts` |
| P0-3 / CT-06,07,10 | revisão HTTP, harness T07 e dossiê integrado |
| P0-4 / CT-08,13,14 | geração HTTP, transporte SDK controlado, falhas/recuperação integradas; live pendente |
| P0-5 / CT-09 | harness T08, aula real persistida no E2E controlado; projetor físico pendente |
| P0-6 / CT-11,12 | exportação HTTP real, download, harness T11, CSS print/PDF Chromium; diálogo físico pendente |
| P0-7 / CT-02,10 | Transformar em aula, retorno à investigação/contribuição, dossiê textual e preservação de editor/slide/foco |
| Transversais | segurança HTTP, contratos, idempotência, expiração/manutenção T12 e reconexão integrada |
| P0-8 | resultados em `validation.md`, roteiro em `demo-scenarios.md`; ensaio live/humano pendente |

As contagens finais e comandos estão em [validation.md](validation.md).

## Diagnóstico da prévia de 45 segundos

A observação informada pelo usuário (chamada simples de 11,72 s e prévia real
frequentemente acima de 45 s) ainda precisa de reprodução autorizada. Uma chamada
simples não mede o mesmo payload/schema nem a contagem externa de tokens.
Não há diagnóstico confirmado do gargalo live nem otimização de desempenho alegada.

`matilda.studio.timings` registra eventos `studio_stage` com nome da etapa,
duração em ms e status, inclusive em erro/cancelamento. As etapas são:
`scientific_retrieval`, `context` (T04 e montagem do payload), `token_count`,
`structured_generation`, `validation` e `persistence`. Eventos repetidos indicam
subetapas ou tentativas; somar por etapa na mesma execução. Não são registrados
prompt, resposta completa, material docente, chave ou identificadores científicos.
A inicialização lazy do SDK é contabilizada na primeira contagem de tokens.
Os eventos não têm correlação por operação; executar o ensaio CLI isoladamente
para não misturar etapas de requisições concorrentes.

Uma execução local do teste de transporte SDK **controlado**, anterior ao ensaio
live, mediu: recuperação 0,001 ms; contexto T04 13,121 ms; contagem de tokens
202,753 ms; geração estruturada 21,337 ms; validação 0,490 ms; persistência
2,377 ms somadas; prévia total 0,244 s. Esses números incluem transporte simulado
e não medem rede, inferência, quota ou latência do Gemini real. Testes com atraso
externo conhecido verificam que os atrasos aparecem nas etapas correspondentes.

Os limites contratuais continuam 45 s para prévia e 75 s para geração, com no
máximo duas tentativas compartilhando o deadline. Não foi aumentado timeout,
reduzida a validação científica ou removida a contagem de tokens.

Após autorização específica de custo, executar separadamente cada cenário:

```sh
.venv/bin/python scripts/smoke_studio_t10.py --allow-paid-gemini --scenario crispr
.venv/bin/python scripts/smoke_studio_t10.py --allow-paid-gemini --scenario rna
```

O nome do script T10 é preservado por compatibilidade. `--preview-only` permite
isolar a prévia; `--env-file /caminho/.env` seleciona a configuração do backend.
Sem a flag o script recusa executar. Cada invocação limita chamadas estruturadas
a duas prévias e uma geração; contagem de tokens também chama o provedor.
Usa SQLite separado `.runtime/studio-t13-smoke.sqlite`, snapshots bibliográficos
reais datados e Gemini real. Não injeta respostas prontas. Relatório JSON inclui
modelo/tokens/latências/códigos sem credencial ou material. Falha permanece falha.
Diagnosticar a etapa predominante antes de otimizar e repetir dentro do orçamento
autorizado. Não tratar `preview_passed` como ensaio completo de geração.

## Limitações e gate presencial

- Nenhuma chamada paga foi realizada nesta execução. Gemini live, modelo/quota,
  geração real CRISPR/RNA e gargalo acima de 45 s permanecem pendentes de autorização.
- Ambiente automatizado local: FastAPI/Uvicorn, Vite e SQLite temporário, APIs na
  mesma origem por proxy. Não houve publicação nem validação HTTPS/host público.
  No ambiente publicado: cookie, download, SQLite persistente e proxy ≥100 s
  precisam de conferência. O proxy não altera o deadline interno do backend.
- Chromium headless confere teclado, foco, viewport 390 px, notas ocultas e PDF.
  Projetor físico, diálogo de impressão/PDF do navegador do pitch, leitura dos
  links/fontes e adequação pedagógica exigem ensaio humano no equipamento alvo.
- As seis fontes editoriais e seus participantes são preservados; testes de
  integridade não equivalem a aprovação científica independente de especialista.
  As frentes A/B/C/D ainda precisam registrar seu aceite da versão candidata.
- Aula recuperada deve ser anunciada como recuperada, com data/modelo efetivos.
  Cache científico real deve ser anunciado como cache; não equivale a busca live.

O candidato não representa aceite M4 concluído enquanto esses gates estiverem
pendentes. Não modificar/fechar automaticamente a Issue #1.

## Capturas conferidas

Provedor externo controlado; ciência de snapshots reais identificados como cache.
As imagens não constituem ensaio Gemini nem validação no projetor físico.

- [Dossiê RNA em viewport mobile](screenshots/t13-dossier-rna-mobile.png).
- [Plano CRISPR na mídia de impressão](screenshots/t13-plan-crispr-print.png).

Inspeção visual: texto, DOI e autoria coletiva legíveis no dossiê; plano contém
sequência de 50 minutos, atividade, notas, evidências e limitações, sem controles
de navegação na impressão. Quebras do PDF e legibilidade no equipamento do pitch
permanecem no checklist humano.

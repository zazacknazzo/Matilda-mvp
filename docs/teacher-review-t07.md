# Revisão docente — T07 / Issue #8

Workspace de revisão independente, consumindo o contrato T03 v1 já integrado.
Permite aceitar/rejeitar sugestões, editar somente proposta e justificativa
pedagógicas, revisar/aprovar objetivos e salvar decisões parciais. Evidência,
histórico canônico, participantes, conceitos e material original são somente leitura.

## Consumo por T10

```tsx
const reviewApi = createReviewApi(); // instância estável no host

<ReviewWorkspace
  previewId={previewId}
  api={reviewApi}
  onContinue={(request) => showGenerationPanel(request)}
  onRequestNewPreview={() => showSetup()}
/>
```

Imports: `frontend/src/studio/ReviewWorkspace.tsx` e `review-api.ts`.
`ReviewApi` oferece `getPreview` e `saveReview`, com AbortSignal opcional.
O adaptador HTTP usa as rotas T03 GET preview e POST review, `credentials:
same-origin` e Origin enviado pelo navegador. Falhas HTTP são `ReviewApiError`;
corpos de erro não são exibidos nem registrados. Não há fallback para fixtures.
Um host em outra origem deve fornecer seu próprio adaptador conforme a política
de sessão/CORS de B; não enviar tokens de sessão pelo componente.

`onContinue` recebe GenerateRequest construído exclusivamente a partir da
resposta persistida: preview_id, review_revision e IDs aceitos. Não chama IA,
não cria idempotência nem dispara POST generate. T09/T10 cuidam da geração.
Só é liberado com todos decididos, objetivos aprovados, nenhuma edição pendente,
nenhuma operação incerta, prévia não expirada e geração não ativa. Zero aceitas
e zero sugestões são válidos. Salvar uma edição pedagógica de sugestão pendente
exige primeiro aceitar/rejeitar essa sugestão para evitar perda silenciosa.

O callback de nova prévia é chamado após confirmação e invalida a revisão atual.
O host deve criar outra prévia ao alterar material, DOI/investigação ou configuração,
e passar seu novo previewId. Não reaproveitar a revisão antiga. Trocar previewId
remonta o editor e cancela as requisições anteriores. Não mutar os objetos recebidos.

Salvar usa a revisão esperada e envia somente ReviewDecision e objetivos, sem
campos científicos. O estado exibido é substituído pela resposta da API; a UI não
simula sucesso local. O prazo é sempre o da resposta, sem renovação calculada no
cliente. Erro, desconexão, 409 e resposta inconsistente conservam o rascunho na tela,
bloqueiam reenvio/avanço e exigem consulta explícita do estado salvo. Se houver
edições, carregar essa versão pede confirmação antes de substituí-las. Não há
retry automático de POST. Editar objetivos remove sua aprovação até nova confirmação.

## Harness e testes

Na pasta `frontend`:

```powershell
npm.cmd ci
node node_modules/vite/bin/vite.js --config review-harness/vite.config.ts
```

Abrir `http://127.0.0.1:5175`. Banner permanente identifica EXEMPLO / API simulada.
O middleware Vite serve as fixtures T03 e guarda decisões **apenas em memória**;
reiniciar o processo perde esse estado. Não implementa segurança de servidor.
As datas originais das fixtures são preservadas; os testes fixam o relógio para
21/10/2026. Não publicar o harness como fluxo de produção. Ele tem entrada, cache,
configuração e testes separados, sem alterações em App, host, backend ou contratos.

```powershell
node node_modules/typescript/bin/tsc -p review-harness/tsconfig.json
node node_modules/@playwright/test/cli.js test --config playwright.review.config.ts
npm.cmd run build
```

Os testes usam o adaptador fetch real com HTTP interceptado e estado isolado por
teste. Conferem payloads, resposta confirmada, retomada após reload, revisão parcial,
zero aceitas, sem cobertura, aprovação/limites dos objetivos, erros 409/422/503,
desconexão sem repetição, resposta inconsistente, IDs duplicados, requisição antiga,
edição pendente, invalidação de entrada, expiração, bloqueio durante geração,
HTML literal, URLs inseguras, participantes, teclado, foco e viewport de 390 px.
Um cenário adicional percorre o middleware manual sem interceptação HTTP.

## Validação desta entrega

Executado no Windows, Node 26.5.1, Python 3.14.6, Pydantic 2.13.4,
Vite 6.4.5 e Chromium 156.0.8078.4:

- 19 testes Playwright T07 aprovados; desktop/mobile inspecionados visualmente.
- 6 testes Playwright Forensics aprovados com frontend/API reais e SQLite isolado;
  snapshots identificados pelo produto e descoberta simulada pelos testes existentes.
- 13 testes Playwright de slides/plano aprovados.
- 366 testes backend aprovados; aviso preexistente Starlette/TestClient com HTTPX.
- 40 payloads Studio, 7 fixtures científicas e 4 fixtures de aula conferidos pelos
  verificadores existentes; tipagem do harness e build de produção aprovados.

No Windows, executar o backend com `.venv/Scripts/python.exe -X utf8 -m uvicorn
app.main:app --app-dir backend --host 127.0.0.1 --port 8000`. O primeiro ensaio sem
`-X utf8` falhou na leitura CP1252 de snapshots por `gap_analysis.py` existente;
reiniciar com UTF-8 e banco isolado novo resolveu a execução, sem editar esse módulo.

Esta entrega não comprova cookie, Origin, isolamento entre sessões, persistência
real, autoridade científica do servidor ou geração Gemini. As guardas de renderização
não substituem os validadores T03. Rotas, autorização, gravação/revisão atômica,
retomada real e ligação ao host pertencem a T10. Revisão por outro integrante e aceite
continuam necessários antes da integração; a Issue #1 permanece intacta.

# T05 — texto/conceitos até prévia persistida

Implementa [#6](https://github.com/zazacknazzo/Matilda-mvp/issues/6), usando
[#1](https://github.com/zazacknazzo/Matilda-mvp/issues/1) e os contratos integrados
T01/T03/T04, sem alterar seus schemas/tipos/fixtures. Responsabilidade desta fatia:
B (API/IA/persistência) com a entrada mínima de C. Revisão docente real e geração
final permanecem nos próximos tickets; os módulos T07/T08 não foram modificados.

## Fluxo demonstrável

1. Instale `backend/requirements.txt` (SDK oficial `google-genai==2.32.0`) e as
   dependências frontend conforme README. Configure `GEMINI_API_KEY` no `.env`
   da raiz; opcionalmente configure `GEMINI_MODEL`, padrão `gemini-3.8-flash`.
2. Execute API e frontend. Selecione **Studio — Criar aula**.
3. Informe título **Edição genética**, texto **CRISPR-Cas9 permite discutir
   edição genética e mecanismos de reparo do DNA.** e conceito **CRISPR-Cas9**.
4. Confira disciplina, nível, duração e aviso de envio ao Gemini. Crie a prévia.
5. Confira original preservado, conceitos resolvidos, âncora literal, proposta,
   justificativa, estado pendente, afirmação canônica, participantes e fonte.
6. Recarregue o endereço `#studio/previews/<id>` no mesmo navegador: GET consulta
   SQLite sem chamar IA. Outro contexto de navegador recebe 404 genérico.
7. Alterne para Forensics e volte: ambos os workspaces conservam o estado.
8. Para sem cobertura, use **Trigonometria e triângulos**. A lista científica
   fica vazia, com aviso de limite do catálogo. Falha do provedor não vira sucesso.

## Limites e validação

- POST `/api/studio/preview` retorna 201 somente após validar e publicar;
  GET `/api/studio/previews/{id}` recupera o snapshot autorizado. Origem de escrita
  é validada contra `MATILDA_CORS_ORIGINS`. Erros não expõem corpo upstream.
- Corpo limitado em streaming a 128 KiB, material a 20.000 caracteres, até
  20 conceitos e 10 objetivos. SDK conta instrução/material/schema antes de gerar;
  limite 12.000 tokens de entrada e 8.000 de saída, incluindo raciocínio.
- Deadline monotônico compartilhado de 45 s, até duas tentativas incluindo
  correção, sem retry para 401/403/timeout; cliente 55 s e proxy Vite 100 s.
  O navegador anuncia espera superior à meta de 30 s sem progresso fictício.
- O modelo só escolhe IDs e âncoras e escreve propostas pedagógicas. O servidor
  resolve pesquisadores, evidência, explicação científica, participantes, URL e
  concatenação literal de `claim_supported`. IDs fora do conjunto, evidência de
  outra contribuição, trecho ausente, campos novos, JSON inválido/incompleto ou
  saída acima do limite não publicam uma prévia.
- Campos pedagógicos livres exigem revisão humana: validação estrutural e de IDs
  não demonstra correção semântica universal. A interface diferencia esses campos
  da afirmação documental canônica. HTML continua texto React.
- O material é dado não confiável, separado da instrução. Sem ferramentas,
  navegação, execução de código ou busca de URLs fornecidas pelo modelo.
- Tabelas Studio são aditivas, transacionais, com foreign keys; documentos originais
  são gravados antes da IA. A evidência referencia snapshot do catálogo local
  (`from_cache=true`, `retrieved_at` é a leitura do snapshot, não nova consulta à
  publicação). Nada altera catálogo ou classificação científica Forensics.
- Token opaco seguro em cookie HttpOnly, SameSite=Lax, Path=/api/studio, Secure
  sob HTTPS. Só o hash do token é armazenado; ownership não chega à resposta.
  Sessão e projeto recebem sete dias na admissão; cookie usa o prazo admitido,
  descontando a execução. GET não renova. Limpar cookie impede retomada.
- Limpeza de expirados no início e a cada hora, além dos acessos Studio;
  operações admitidas continuam protegidas até deadline + tolerância.
- Admissão/cota persistidas e atômicas: uma operação por sessão, duas globais,
  cinco prévias por hora. Operação interrompida libera após 45 + 15 s. Transação
  SQLite não permanece aberta na rede. Conflito ativo é 409; cota é 429 com
  Retry-After; capacidade global é 503 sem bloquear o Forensics.
- T05 não expõe `/generate`: a idempotência sessão/prévia/revisão/chave desse
  endpoint continua no contrato M0 para T09/T10. POST de prévia não ganhou um
  cabeçalho idempotente alternativo. GET nunca gera de novo; pedidos simultâneos
  da mesma sessão são barrados por admissão persistida.
- Antes da primeira prévia válida, erro devolve project_id próprio e permite
  tentativa explícita com o formulário preservado. Drafts ficam no banco, sem
  novo CRUD/GET público; fechar a tela nessa fase não restaura o formulário.

## Verificação em 21/10/2026

Ambiente: macOS arm64, Python 3.14, Node 26.10, SDK Google 2.32.0,
SQLite local temporário. Os requisitos mínimos do README permanecem Python 3.12+
e Node 22+. Testes não declaram ensaio em todas essas versões.

- `.venv/bin/python -m pytest backend/tests -q`: 429 testes aprovados, incluindo
  43 novos testes T05 na fronteira HTTP com SQLite real e provedor controlado.
- `npm run build` em frontend: TypeScript e Vite aprovados.
- `scripts/check_studio_contract.py`: 40 payloads; `check_scientific_contract.py`:
  7 fixtures; `node scripts/check_lesson_types.mjs`: 4 fixtures, aprovados.
- `playwright.studio.config.ts`: 9 aprovados (6 Forensics sem enfraquecer asserts,
  3 Studio com API real/SQLite). `playwright.lesson.config.ts`: 14 aprovados;
  `playwright.review.config.ts`: 19 aprovados. Os dois últimos continuam harnesses
  declarados, não comprovação de revisão/geração integrada em produção.
- `pip check` e `git diff --check`: aprovados.

TDD: primeiro HTTP falhou pela ausência da rota/módulo e passou após implementar
POST/GET. Transporte do SDK falhou antes de admitir transporte controlado e passou
com a conexão HTTP externa substituída. OpenAPI da rota e cookie com prazo admitido
falharam antes das correções. Playwright falhou com Studio ausente; servidor real
revelou diferença de relógio do uvloop, corrigida usando duração restante em vez
de misturar relógios absolutos. Jornadas completas passaram depois.

A suíte completa revelou uma asserção de M0 que exigia ausência de todas as rotas
Studio. Mantida a verificação de que gerar o contrato standalone não altera a
aplicação, removida somente a premissa temporal agora superada por T05. O primeiro
build executado junto do checker científico encontrou um arquivo temporário que
esse checker removeu durante a compilação. Build repetido após concluir checkers;
esses comandos devem ser executados sequencialmente, pois compartilham a árvore.

Avisos: depreciação preexistente Starlette/TestClient/HTTPX e aviso do SDK Google
sobre typing no Python 3.14.

## Ensaio Gemini real

Não executado: não havia `GEMINI_API_KEY` no ambiente nem no `.env`. Nenhum segredo
foi impresso, nem chamada paga feita pela suíte. O ensaio requer confirmar chave,
quota, modelo efetivo, latência e qualidade pedagógica com o texto acima. Sucesso
com provedor controlado não comprova disponibilidade real de Gemini para o pitch.

Referências oficiais consultadas para o adaptador:
[SDK Python](https://googleapis.github.io/python-genai/),
[saídas estruturadas](https://ai.google.dev/gemini-api/docs/structured-output) e
[Gemini 3.8 Flash](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash).

Produção mantém a implementação real como único provedor. A composição que
substitui Gemini está exclusivamente em `backend/tests/studio_e2e_app.py` e é
iniciada pelo Playwright em porta/banco temporários; não há flag de mock no app.


## Revisão da implementação

Primeira passagem de code-review contra `main` `de5abcb`, em agentes separados:
Standards: um P2 (último erro/estado na retomada); Spec: dois P2 (limpeza sem
lifecycle e leitura do corpo fora do prazo total). Todos corrigidos sem mudar
schemas compartilhados. Regressões HTTP falharam antes e passaram após os ajustes.
A conferência operacional de retenção, com relógio controlado e reinício real do
lifespan, removeu 2 documentos expirados antes de qualquer acesso Studio e
preservou a investigação Forensics. Essa verificação de armazenamento é registrada
separadamente dos testes de comportamento HTTP.

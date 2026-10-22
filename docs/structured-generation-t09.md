# T09 — geração estruturada

Implementa a geração a partir de uma revisão salva usando os contratos congelados de T02/T03. Não altera os schemas públicos, o cliente Gemini da T05, a revisão T07 nem os renderizadores T08/T11.

## Composição para T10

- `GenerationService` recebe explicitamente `StudioRepository`, `StudioProvider` e um resolvedor de `ScientificAuthority`. O resolvedor precisa consultar snapshots científicos confiáveis do servidor, independentemente do conteúdo da prévia ou da resposta do modelo.
- `create_generation_router` recebe o serviço, resolvedor real de sessão, renovação de cookie e origens permitidas. Não está registrado em `app.main`. O corpo e os cabeçalhos seguem T03; criação retorna 201, repetição concluída 200.
- `GenerationPanel` recebe o request congelado, `GenerationApi` e `onOpenLesson`. Não importa a interface de revisão nem o renderizador. `createGenerationApi` usa a API da mesma origem.
- `IsolatedGenerationRepository` é um adaptador SQLite opt-in, com tabelas próprias. `store_reference_preview` serve somente para preparar a revisão de referência; não existe endpoint de seed no produto. T10 deve integrar as operações à persistência/sessão de produção ou fornecer um adaptador compatível.

O provider recebe instrução de sistema separada do material não confiável e um schema interno estrito com chaves locais. O servidor gera IDs finais, resolve literalmente referências autorizadas e deriva configuração/objetivos da revisão. Claims estruturados só podem apontar evidências aceitas; referências rejeitadas, desconhecidas ou alteradas são recusadas. Texto pedagógico livre ainda requer revisão humana; esta implementação não verifica semanticamente toda afirmação em linguagem natural.

O adaptador de transporte fornecido pela T10 deve desabilitar ferramentas, navegação e execução de código, como exige o port. T09 não instancia SDK, executa ferramentas nem faz fallback de produção para fixtures. Os testes usam provider simulado; não houve chamada ao Gemini real.

## Operação e recuperação

Admissão atômica valida revisão, posse, expiração, fingerprint e idempotência. Uma operação por sessão, duas globais, cinco admissões por hora; replay concluído não cobra quota nem renova retenção. Nova admissão renova sessão/projeto por sete dias, inclusive quando a geração admitida falha. Leituras não renovam.

São no máximo duas tentativas de provider dentro do mesmo prazo: 75 s no backend, reserva de 5 s para persistência, 12.000 tokens de entrada e 8.000 de saída, JSON/corpo de até 128 KiB. Timeout, autenticação, bloqueio e truncamento não são repetidos; indisponibilidade/429 ou resposta inválida podem consumir a segunda tentativa. As duas tentativas contam como uma admissão, sem garantia de cobrança única pelo provedor.

A conclusão revalida revisão/fingerprint e salva um único bundle. Falhas preservam decisões e a aula anterior. Operações abandonadas podem ser recuperadas após 75 + 15 s; conclusões tardias não sobrescrevem outra operação. T12/T10 devem agendar a limpeza e compor a infraestrutura de produção.

O cliente encerra a espera em 85 s, informa a meta de 45 s, conserva a chave em sessionStorage e nunca repete POST automaticamente. Após resultado incerto exige reconciliação por GET; operações em andamento permitem consultas limitadas. Após salvar, consulta o prazo atualizado sem renová-lo. O callback abre um ID existente, sem acoplamento ao renderizador.

## Validação

- 49 testes específicos T09: schemas, evidências, snapshots independentes, duração/vínculos, saída inválida, falhas do provider, tokens/prazos, concorrência entre conexões SQLite, quotas, replay/reinício, recuperação e HTTP/cookie.
- Suíte backend: 499 testes aprovados. No Windows/Python 3.14, um teste preexistente da T05 parametriza 128 KiB no nome e excede o limite de `PYTEST_CURRENT_TEST`. A execução completa usou um plugin temporário que encurta apenas node IDs acima de 1.000 caracteres com hash, preservando os dados e as asserções. Nenhum arquivo T05 foi alterado.
- 11 testes de navegador T09 usam revisão de referência + orquestrador/validador/SQLite reais e provider simulado: sucesso, erros, reconciliação após perda da resposta, chave estável, limite do cliente, polling, revisão divergente, teclado e viewport móvel.

Com dependências instaladas, na raiz: `.venv/Scripts/python.exe -X utf8 -m pytest backend/tests/test_studio_generation.py -q` (Linux: `.venv/bin/python`). Em `frontend`: `npx playwright test --config playwright.generation.config.ts`, `npx tsc -p generation-harness/tsconfig.json --noEmit` e `npm run build`.

O Playwright inicia automaticamente o harness isolado nas portas 8017/5177. Para uso manual, iniciar `backend/tests/generation_harness.py` com Python e Vite com `--config generation-harness/vite.config.ts`. A página identifica permanentemente EXEMPLO / DESENVOLVIMENTO · GEMINI SIMULADO. O harness usa sessão falsa e dados de referência e não é registrado/importado pelo aplicativo de produção.

Regressão adicional aprovada: 9 testes Studio/Forensics, 19 revisão, 14 renderização e 11 exportação; com os 11 T09, total de 64 testes de navegador. Build de produção e typecheck do harness aprovados. Screenshots regenerados de Forensics foram descartados; somente arquivos novos da T09 integram a entrega.

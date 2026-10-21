# Matilda — Forensics e Studio

**Toda descoberta tem uma história. Investigue a participação delas.**

MVP local do PRD v3.0 para o I Hackathon da SEDCITEC 2026 — Ciência Delas,
IFSP Campus São Paulo. Um DOI inicia a recuperação de metadados reais no
OpenAlex, a descoberta de contribuições documentadas e a exploração de relações
bibliográficas e temáticas com dossiês verificáveis.

## Executar

Requisitos: Python 3.12+, Node.js 22+ e npm. Escolha as instruções para seu
sistema operacional. No Windows, use PowerShell e os comandos da seção seguinte;
os comandos `make` e `.venv/bin/...` abaixo são para Linux/macOS.

### Windows (PowerShell)

Abra PowerShell na pasta do repositório. Crie o ambiente Python e instale as
dependências:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
Copy-Item .env.example .env
Push-Location frontend
npm.cmd ci
Pop-Location
```

Abra dois terminais PowerShell na pasta do repositório. No primeiro, inicie a
API:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
```

No segundo, inicie a interface:

```powershell
Push-Location frontend
npm.cmd run dev
```

Abra **http://localhost:5173**. A API e o Swagger ficam em
**http://localhost:8000/docs**. Mantenha os dois terminais abertos. Para parar
cada processo, pressione `Ctrl+C`; no terminal do frontend, depois execute
`Pop-Location` ou feche o terminal.

Para verificar a instalação no PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests -q
Push-Location frontend
npm.cmd run build
Pop-Location
```

### Linux/macOS

Na raiz do repositório:

```sh
make setup
cp .env.example .env
make backend
```

Em outro terminal:

```sh
make frontend
```

Abra **http://localhost:5173**. A API e o Swagger ficam em
**http://localhost:8000/docs**. O Vite encaminha `/api` ao backend.

Sem Make, execute os comandos equivalentes:

```sh
python -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
cd frontend
npm ci
```

Na raiz: `.venv/bin/python -m uvicorn app.main:app --app-dir backend --port 8000`.
No frontend: `npm run dev`.

## Experimente

- CRISPR: `10.1126/science.1231143`
- Vacinas de RNA: `10.1056/NEJMoa2034577`
- Fora da cobertura atual: `10.1038/171737a0`

Confirme a ficha bibliográfica e clique em **Investigar contribuições femininas**.
Selecione uma contribuição, leia a classificação bibliográfica e abra a evidência.
Use as camadas do grafo, a alternativa em lista ou exporte Markdown/JSON.

## Studio: texto até prévia verificável (T05)

Selecione **Studio — Criar aula**, informe título, texto e/ou conceitos (por
exemplo CRISPR-Cas9), confira os defaults e clique em **Criar prévia**.
O texto é enviado ao Gemini junto da configuração e do conjunto científico
resolvido pelo mesmo motor do Forensics. A tela separa material original,
propostas pedagógicas pendentes e evidências canônicas com participantes e fontes.
A revisão docente e a geração final ainda não estão conectadas neste fluxo.

Configure `GEMINI_API_KEY` no `.env` da raiz, exclusivamente no backend, e
reinicie a API. O modelo configurável é `GEMINI_MODEL=gemini-3.8-flash`.
Sem chave/quota ou com resposta inválida, a prévia falha explicitamente e conserva
a entrada; o Forensics permanece disponível. Nenhum retorno simulado é selecionado
pela aplicação de produção.

Uma prévia válida é persistida no SQLite e pode ser retomada pelo endereço
`#studio/previews/<id>` no mesmo navegador. O cookie é HttpOnly; outro navegador
não acessa o material. A retenção é de sete dias por criação válida admitida;
consultar não renova. Material e configuração ficam gravados antes da IA;
erro devolve o projeto próprio para tentativa explícita. Antes da primeira
prévia válida, o formulário mantém a entrada na tela; não há consulta pública
de drafts nem recuperação de formulário após fechar essa tela.

Testes com API, SQLite e provedor externo controlado, incluindo a regressão
Forensics (os servidores são iniciados automaticamente):

```sh
cd frontend
node node_modules/@playwright/test/cli.js test --config playwright.studio.config.ts
```

[Contrato e execução T05](docs/studio-preview-t05.md). Para publicar, mantenha
frontend e `/api` na mesma origem HTTPS, proxy com timeout de pelo menos 100 s
e SQLite persistente. No desenvolvimento, `MATILDA_API_PROXY` altera o destino
do proxy Vite; o navegador continua usando `/api` e não recebe a chave.

## Ampliação automática

Após investigar um DOI, clique em **Ampliar descoberta automaticamente**.
O sistema busca publicações relacionadas no OpenAlex e Europe PMC, consulta
identidades por ORCID/ID OpenAlex no Wikidata e acumula candidatos com fontes,
trechos de resumos e histórico em SQLite. Novos registros ficam pendentes de
revisão e não recebem automaticamente o selo de contribuição verificada.

[Funcionamento, limites e API da ampliação](docs/automatic-catalog.md).

## Implementado

- DOI normalizado e validado; consulta OpenAlex com timeout e retries limitados.
- Conceitos específicos com procedência e explicações determinísticas.
- Catálogo de 3 pesquisadoras e 6 contribuições nos dois domínios do PRD.
- Grafo integrado com entidades e relações tipadas, zoom, pan e seleção.
- Duas camadas e comparação por identificadores bibliográficos persistentes.
- Dossiês com fontes primárias, coautores, localização e limitações.
- Cache real identificado com data, fallback explícito e SQLite local.
- Interface responsiva, controles por teclado, foco visível e lista textual.
- Exportações Markdown/JSON e API de resultados persistidos por sete dias.

A correspondência temática **não comprova influência histórica**. Uma publicação
não localizada nas referências recuperadas **não comprova exclusão**.

## Variáveis de ambiente

| Variável | Uso |
|---|---|
| `OPENALEX_API_KEY` | Chave opcional do OpenAlex, apenas no backend; pode ser exigida pelo serviço |
| `OPENALEX_MAILTO` | Contato opcional para consultas acadêmicas |
| `GEMINI_API_KEY` | Chave Gemini, somente no backend; exigida apenas pelo Studio |
| `GEMINI_MODEL` | Modelo Studio; padrão `gemini-3.8-flash` |
| `MATILDA_DB` | Banco SQLite; padrão `.runtime/matilda.db` na raiz |
| `MATILDA_CACHE_TTL` | Validade do cache em segundos; padrão 86400; use 0 para tentar atualizar |
| `MATILDA_CORS_ORIGINS` | Origens frontend permitidas, separadas por vírgula |

As regras vigentes de autenticação, créditos e limites são definidas pelo
[OpenAlex](https://help.openalex.org/api/). Sem chave, o funcionamento depende
do acesso permitido pela API. Os exemplos incluem snapshots reais com data e
origem que são sempre apresentados como cache. Segredos não vão para o frontend.

## Verificar

```sh
make test
make build
```

Com backend e frontend em execução:

```sh
cd frontend
npx playwright install chromium
npm run test:e2e
```

A suíte backend verifica dez DOIs reais com snapshots e cenários de erros
simulados; não depende de chamadas externas para seus testes. A suíte de navegador
exercita DOI, dossiê, fontes, exportação, filtros, camadas, lista, estados vazios,
celular e teclado. Evidências de execução em [docs/validation.md](docs/validation.md).

## Arquitetura e fontes

React 19, TypeScript, Vite, React Flow e Lucide; FastAPI, Pydantic, HTTPX,
SQLite e catálogo JSON. O Forensics mantém explicações determinísticas. O Studio
usa Gemini real por meio do SDK oficial `google-genai`, com validação no servidor.

- [Arquitetura e API](docs/architecture.md)
- [Método científico e fontes](docs/research-methodology.md)
- [Catálogo automático](docs/automatic-catalog.md)
- [Cenários de demonstração](docs/demo-scenarios.md)
- [Escopo e pendências do PRD](docs/prd-status.md)
- [PRD da próxima expansão do motor de busca](docs/prd-expansao-motor-busca.md)

Equipe prevista: quatro desenvolvedores. Nomes e créditos institucionais finais
aguardam preenchimento pela equipe; não foram inventados.

## Limitações e créditos

O catálogo está abaixo da meta quantitativa do PRD e exige revisão final pela
equipe. Não há busca livre, PDF, login, expansão recursiva ou identificação de
injustiças. A comparação informa somente presença no conjunto recuperado, cuja
completude não foi auditada. Validação por usuários, revisão especializada e teste
no equipamento do pitch permanecem pendentes.

Metadados OpenAlex: [CC0](https://docs.openalex.org/additional-help/faq).
Artigos e páginas externas mantêm os direitos dos respectivos autores e editores;
o projeto armazena metadados, paráfrases e referências, sem distribuir PDFs.
Lucide usa licença ISC; React, Vite e React Flow usam MIT. O código deste
repositório ainda não recebeu licença de distribuição definida pela equipe.

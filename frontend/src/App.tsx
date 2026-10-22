import { StudioWorkspace } from "./studio/StudioWorkspace";
import { useState, useRef, useEffect, type FormEvent } from "react";
import {
  ArrowRight,
  ArrowUpRight,
  Atom,
  BookOpen,
  Check,
  ChevronLeft,
  CircleHelp,
  Download,
  ExternalLink,
  FileSearch,
  Fingerprint,
  FlaskConical,
  GitBranch,
  Info,
  List,
  LoaderCircle,
  Network,
  Search,
  ShieldCheck,
  X,
} from "lucide-react";
import { AutomaticDiscovery } from "./components/AutomaticDiscovery";
import { GuidedMap } from "./components/GuidedMap";
import { retrievePaper, investigate } from "./services/api";
import type { Analysis, Paper, Match, GraphNode } from "./types";
import {
  ScientificGraph,
  relationNames,
  typeNames,
} from "./components/ScientificGraph";
import {
  EvidenceInspector,
  citationLabels,
} from "./components/EvidenceInspector";
const examples = [
  {
    label: "Edição genômica",
    doi: "10.1126/science.1231143",
    detail: "CRISPR · Cong et al., 2013",
  },
  {
    label: "Vacinas de RNA",
    doi: "10.1056/NEJMoa2034577",
    detail: "BNT162b2 · Polack et al., 2020",
  },
];
function ForensicsApp() {
  const [doi, setDoi] = useState("");
  const [paper, setPaper] = useState<Paper | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [selected, setSelected] = useState<Match | null>(null);
  const [node, setNode] = useState<GraphNode | null>(null);
  const [busy, setBusy] = useState<"retrieving" | "investigating" | null>(null);
  const [error, setError] = useState("");
  const [view, setView] = useState<"map" | "graph" | "list">("map");
  const [filter, setFilter] = useState("all");
  const [about, setAbout] = useState(false);
  const [mobileTab, setMobileTab] = useState("explore");
  const heading = useRef<HTMLHeadingElement>(null);
  const errorRef = useRef<HTMLDivElement>(null);
  const evidenceRef = useRef<HTMLDivElement>(null);
  function revealEvidence() {
    setMobileTab("evidence");
    requestAnimationFrame(() => {
      evidenceRef.current?.focus();
      evidenceRef.current?.scrollIntoView({ block: "start" });
    });
  }
  async function load(value: string) {
    setDoi(value);
    setError("");
    setAnalysis(null);
    setPaper(null);
    setSelected(null);
    setNode(null);
    setBusy("retrieving");
    try {
      const result = await retrievePaper(value);
      setPaper(result);
      setTimeout(() => heading.current?.focus(), 0);
    } catch (e) {
      setError((e as Error).message);
      setTimeout(() => errorRef.current?.focus(), 0);
    } finally {
      setBusy(null);
    }
  }
  async function run() {
    if (!paper) return;
    setBusy("investigating");
    setError("");
    try {
      const result = await investigate(paper.doi);
      setAnalysis(result);
      setFilter("all");
      setView("map");
      setMobileTab("explore");
      setTimeout(() => heading.current?.focus(), 0);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  }
  function submit(e: FormEvent) {
    e.preventDefault();
    if (doi.trim() && !busy) void load(doi);
  }
  function choose(match: Match) {
    setSelected(match);
    setNode(null);
    revealEvidence();
  }
  function selectNode(n: GraphNode) {
    setNode(n);
    const match = analysis?.contributions.find(
      (m) =>
        n.metadata.contribution_id === m.contribution.id ||
        (n.type === "RESEARCHER" &&
          m.researchers.some((r) => r.openalex_id === n.id)),
    );
    setSelected(match || null);
    revealEvidence();
  }
  const results =
    analysis?.contributions.filter(
      (m) => filter === "all" || m.citation_status === filter,
    ) || [];
  return (
    <>
      <a className="skip-link" href="#main">
        Pular para o conteúdo
      </a>
      <header className="site-header">
        <button
          className="brand"
          aria-label="Matilda Forensics — início"
          onClick={() => {
            setPaper(null);
            setAnalysis(null);
            setError("");
            setSelected(null);
            setNode(null);
          }}
        >
          <span className="brand-mark">
            <Fingerprint size={27} />
          </span>
          <span>
            matilda<span className="brand-sub">FORENSICS</span>
          </span>
        </button>
        <div className="header-center">
          <span className="live-dot" /> DESCUBRA HISTÓRIAS. CONFIRA AS FONTES.
        </div>
        <button className="quiet-button" onClick={() => setAbout(true)}>
          <CircleHelp size={16} />
          <span>Como investigamos</span>
        </button>
      </header>
      <main id="main" className="forensics-main">
        <ol className="journey" aria-label="Etapas da investigação">
          {[
            "Encontre um artigo",
            "Explore as conexões",
            "Confira as fontes",
          ].map((label, index) => (
            <li
              key={label}
              aria-current={
                (selected ? 2 : analysis ? 1 : 0) === index ? "step" : undefined
              }
            >
              <span>{index + 1}</span>
              {label}
            </li>
          ))}
        </ol>
        {!paper ? (
          <div className="landing">
            <div className="hero-copy">
              <div className="eyebrow hero-eyebrow">
                <span /> CIÊNCIA DELAS · SEDCITEC 2026
              </div>
              <h1>
                Toda descoberta
                <br />
                tem uma história.
                <br />
                <em>
                  Investigue a<br className="desktop-break" /> participação
                  delas.
                </em>
              </h1>
              <p className="hero-description">
                Descubra as mulheres por trás de contribuições científicas.
                Comece com um artigo, explore as conexões e confira as fontes.
              </p>
              <form onSubmit={submit} className="doi-form">
                <label htmlFor="doi">COMECE POR UM ARTIGO CIENTÍFICO</label>
                <div className="search-field">
                  <Search size={20} />
                  <input
                    id="doi"
                    value={doi}
                    onChange={(e) => setDoi(e.target.value)}
                    placeholder="Cole um DOI ou https://doi.org/..."
                    required
                    maxLength={300}
                    autoComplete="off"
                    spellCheck={false}
                  />
                  <button
                    disabled={!!busy}
                    type="submit"
                    aria-label="Recuperar artigo por DOI"
                  >
                    {busy ? (
                      <LoaderCircle className="spin" size={21} />
                    ) : (
                      <ArrowRight size={22} />
                    )}
                  </button>
                </div>
                <p>
                  DOI é o identificador de um artigo. Não tem um? Use um exemplo
                  abaixo.
                </p>
              </form>
              <div className="examples">
                <span>Experimente uma investigação</span>
                {examples.map((example) => (
                  <button
                    key={example.doi}
                    disabled={!!busy}
                    onClick={() => void load(example.doi)}
                  >
                    <FlaskConical size={15} />
                    <div>
                      <strong>{example.label}</strong>
                      <small>{example.detail}</small>
                    </div>
                    <ArrowUpRight size={16} />
                  </button>
                ))}
              </div>
            </div>
            <div
              className="hero-visual"
              aria-label="Ilustração do mecanismo de investigação"
            >
              <div className="visual-topline">
                <span>DA CURIOSIDADE À EVIDÊNCIA</span>
                <span>FIG. 01</span>
              </div>
              <div className="orbital">
                <div className="orbit orbit-one" />
                <div className="orbit orbit-two" />
                <div className="orbit orbit-three" />
                <div className="orbit-center">
                  <Fingerprint size={45} />
                  <strong>
                    Um novo olhar
                    <br />
                    para a ciência.
                  </strong>
                </div>
                <div className="orbit-label orbit-paper">
                  <BookOpen size={18} />
                  <span>
                    Artigo científico<small>O ponto de partida</small>
                  </span>
                </div>
                <div className="orbit-label orbit-concept">
                  <Atom size={19} />
                  <span>
                    Conceitos<small>Conhecimento conectado</small>
                  </span>
                </div>
                <div className="orbit-label orbit-person">
                  <FlaskConical size={18} />
                  <span>
                    Contribuições<small>Participação documentada</small>
                  </span>
                </div>
                <div className="orbit-label orbit-evidence">
                  <ShieldCheck size={18} />
                  <span>
                    Evidências<small>Fontes que você pode verificar</small>
                  </span>
                </div>
                <span className="orbital-dot dot-one" />
                <span className="orbital-dot dot-two" />
                <span className="orbital-dot dot-three" />
              </div>
              <div className="visual-foot">
                <span>Bibliografia + contribuições documentadas</span>
                <GitBranch size={17} />
              </div>
              <div className="scientific-note">
                <ShieldCheck size={20} />
                <p>
                  <strong>Evidência antes de afirmação.</strong> Uma conexão
                  temática é um caminho de descoberta. Ela não comprova
                  influência histórica.
                </p>
              </div>
            </div>
            <div className="method-strip">
              {[
                [
                  FileSearch,
                  "01",
                  "Recupere o artigo",
                  "Um DOI, metadados reais.",
                ],
                [
                  GitBranch,
                  "02",
                  "Explore as conexões",
                  "Duas redes, relações explícitas.",
                ],
                [
                  Fingerprint,
                  "03",
                  "Verifique as fontes",
                  "Cada contribuição, um dossiê.",
                ],
              ].map(([Icon, number, title, text]) => {
                const I = Icon as typeof FileSearch;
                return (
                  <div key={String(number)}>
                    <I size={22} />
                    <span className="method-number">{String(number)}</span>
                    <div>
                      <h2>{String(title)}</h2>
                      <p>{String(text)}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ) : (
          <div className="workspace">
            <div className="workspace-heading">
              <div>
                <button
                  className="back-link"
                  onClick={() => {
                    setPaper(null);
                    setAnalysis(null);
                    setSelected(null);
                    setNode(null);
                    setError("");
                  }}
                >
                  <ChevronLeft size={14} /> Nova investigação
                </button>
                <h1 ref={heading} tabIndex={-1}>
                  {analysis
                    ? "Explore o conhecimento. Siga as evidências."
                    : "O ponto de partida da investigação."}
                </h1>
              </div>
              <div className="workspace-actions">
                {analysis && (
                  <>
                    <a
                      className="outline-button"
                      href={`/api/analyses/${analysis.id}/export?format=markdown`}
                      download
                    >
                      <Download size={15} /> Dossiê .md
                    </a>
                    <a
                      className="quiet-button"
                      href={`/api/analyses/${analysis.id}/export?format=json`}
                      download
                    >
                      JSON <Download size={13} />
                    </a>
                  </>
                )}
                <span className="badge">
                  <span className="live-dot" />
                  {paper.from_cache
                    ? "Cache identificado"
                    : "OpenAlex · consulta real"}
                </span>
              </div>
            </div>
            {!analysis ? (
              <section className="paper-preview">
                <span className="eyebrow">
                  ARTIGO RECUPERADO · {paper.year || "ANO NÃO INFORMADO"}
                </span>
                <h2>{paper.title}</h2>
                <p className="author-list">
                  {paper.authors.map((a) => a.name).join(" · ")}
                </p>
                <a
                  className="text-link"
                  href={"https://doi.org/" + paper.doi}
                  target="_blank"
                  rel="noreferrer"
                >
                  {paper.doi}
                  <ExternalLink size={13} />
                </a>
                <div className="preview-concepts">
                  {paper.concepts.map((c) => (
                    <span key={c.id} className="badge">
                      {c.name}
                    </span>
                  ))}
                </div>
                <details open>
                  <summary>
                    Resumo {paper.abstract ? "disponível" : "indisponível"}
                  </summary>
                  <p>
                    {paper.abstract ||
                      "Sem resumo na fonte. A investigação usará o título, os tópicos e as palavras-chave disponíveis."}
                  </p>
                </details>
                <div className="notice">
                  <Info size={18} />
                  <div>
                    <strong>Cobertura desta consulta</strong>
                    <ul>
                      {paper.limitations.map((w) => (
                        <li key={w}>{w}</li>
                      ))}
                    </ul>
                  </div>
                </div>
                <p className="small">
                  Metadados recuperados em{" "}
                  {new Date(paper.retrieved_at).toLocaleString("pt-BR")}. Fonte:{" "}
                  <a href={paper.source_url} target="_blank" rel="noreferrer">
                    OpenAlex
                  </a>
                  .
                </p>
                <button
                  className="primary-button"
                  onClick={() => void run()}
                  disabled={!!busy}
                >
                  {busy ? (
                    <LoaderCircle size={18} className="spin" />
                  ) : (
                    <Fingerprint size={19} />
                  )}
                  Investigar contribuições femininas
                  <ArrowRight size={17} />
                </button>
              </section>
            ) : (
              <>
                <div className="investigation-summary" role="status">
                  <div>
                    <strong>{analysis.contributions.length}</strong>
                    <span>contribuições no catálogo</span>
                  </div>
                  <div>
                    <strong>
                      {
                        new Set(
                          analysis.contributions.flatMap((m) =>
                            m.researchers.map((r) => r.id),
                          ),
                        ).size
                      }
                    </strong>
                    <span>pesquisadoras relacionadas</span>
                  </div>
                  <p>
                    <ShieldCheck size={19} /> Uma conexão é um convite à
                    leitura. Confira o que cada fonte sustenta.
                  </p>
                </div>
                <nav
                  className="mobile-tabs"
                  aria-label="Painéis da investigação"
                >
                  {[
                    ["explore", "Descobertas"],
                    ["graph", "Mapa e lista"],
                    ["evidence", "Evidências"],
                  ].map(([value, label]) => (
                    <button
                      key={value}
                      aria-current={mobileTab === value ? "page" : undefined}
                      onClick={() => setMobileTab(value)}
                    >
                      {label}
                    </button>
                  ))}
                </nav>
                <div className={"investigation-grid tab-" + mobileTab}>
                  <aside className="explorer">
                    <div className="panel-toolbar">
                      <div>
                        <Search size={16} />
                        <strong>Suas descobertas</strong>
                      </div>
                      <span>01</span>
                    </div>
                    <div className="explorer-content">
                      <div className="eyebrow">
                        ARTIGO ANALISADO · {paper.year}
                      </div>
                      <h2>{paper.title}</h2>
                      <p className="small">
                        {paper.authors
                          .slice(0, 3)
                          .map((a) => a.name)
                          .join(", ")}
                        {paper.authors.length > 3 ? " et al." : ""}
                      </p>
                      <a
                        className="text-link small"
                        href={"https://doi.org/" + paper.doi}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Publicação original
                        <ArrowUpRight size={13} />
                      </a>
                      <div className="concept-list">
                        <h3>
                          Assuntos do artigo{" "}
                          <span>{paper.concepts.length}</span>
                        </h3>
                        {paper.concepts.length ? (
                          paper.concepts.map((c) => (
                            <span
                              className="badge"
                              key={c.id}
                              title={
                                "Identificado em: " + c.provenance.join(", ")
                              }
                            >
                              {c.name}
                            </span>
                          ))
                        ) : (
                          <p className="small">
                            Nenhum termo específico do catálogo identificado.
                          </p>
                        )}
                      </div>
                      <div className="discoveries-heading">
                        <h3>Contribuições</h3>
                        <span className="count">
                          {analysis.contributions.length}
                        </span>
                      </div>
                      <label className="filter-label" htmlFor="citation-filter">
                        Presença nas referências
                      </label>
                      <select
                        id="citation-filter"
                        value={filter}
                        onChange={(e) => setFilter(e.target.value)}
                      >
                        <option value="all">Todas as contribuições</option>
                        {Object.entries(citationLabels).map(([key, value]) => (
                          <option key={key} value={key}>
                            {value}
                          </option>
                        ))}
                      </select>
                      <div className="discovery-list">
                        {results.map((m, index) => (
                          <button
                            className={
                              "discovery-card " +
                              (selected?.contribution.id === m.contribution.id
                                ? "selected"
                                : "")
                            }
                            key={m.contribution.id}
                            onClick={() => choose(m)}
                            aria-pressed={
                              selected?.contribution.id === m.contribution.id
                            }
                          >
                            <span className="discovery-number">
                              {String(index + 1).padStart(2, "0")}
                            </span>
                            <span>
                              <strong>{m.contribution.title}</strong>
                              <small>
                                {m.researchers.map((r) => r.name).join(" · ")}
                              </small>
                              <span className="mini-status">
                                <Check size={11} /> Evidência documental
                              </span>
                            </span>
                            <ArrowUpRight size={14} />
                          </button>
                        ))}
                      </div>
                      {results.length === 0 && (
                        <div className="empty-result">
                          <Search size={22} />
                          <h3>
                            {analysis.contributions.length
                              ? "Nenhum resultado neste filtro"
                              : "Sem correspondência no catálogo"}
                          </h3>
                          <p>
                            {analysis.contributions.length
                              ? "Experimente selecionar todas as contribuições."
                              : "Isso não indica ausência de contribuições femininas. A cobertura inicial se limita a RNA e CRISPR."}
                          </p>
                        </div>
                      )}
                      <details className="coverage">
                        <summary>
                          <Info size={14} /> Cobertura e limitações
                        </summary>
                        <ul>
                          {analysis.coverage_warnings.map((w) => (
                            <li key={w}>{w}</li>
                          ))}
                        </ul>
                        <p>
                          Metadados recuperados em{" "}
                          {new Date(paper.retrieved_at).toLocaleString("pt-BR")}
                          .{" "}
                          {paper.from_cache
                            ? "Fonte: cache do OpenAlex."
                            : "Fonte: consulta ao OpenAlex."}
                        </p>
                      </details>
                    </div>
                  </aside>
                  <div className="center-panel">
                    <div className="center-top">
                      <span className="eyebrow">EXPLORE AS CONEXÕES</span>
                      <div
                        className="view-toggle"
                        aria-label="Visualização dos resultados"
                      >
                        <button
                          aria-pressed={view === "map"}
                          onClick={() => setView("map")}
                        >
                          <GitBranch size={14} />
                          Mapa simples
                        </button>
                        <button
                          aria-pressed={view === "graph"}
                          onClick={() => setView("graph")}
                        >
                          <Network size={14} />
                          Rede completa
                        </button>
                        <button
                          aria-pressed={view === "list"}
                          onClick={() => setView("list")}
                        >
                          <List size={14} />
                          Lista
                        </button>
                      </div>
                    </div>
                    {view === "map" ? (
                      <GuidedMap
                        analysis={analysis}
                        matches={results}
                        selected={selected}
                        onSelect={choose}
                      />
                    ) : view === "graph" ? (
                      <ScientificGraph
                        analysis={analysis}
                        selected={selected}
                        onSelect={selectNode}
                      />
                    ) : (
                      <section
                        className="text-results"
                        aria-label="Alternativa textual ao grafo"
                      >
                        <h2>Relações da investigação</h2>
                        <p>
                          Todas as conexões abaixo correspondem às arestas do
                          grafo.
                        </p>
                        <ul>
                          {analysis.graph.edges.map((e) => (
                            <li key={e.id}>
                              <strong>
                                {
                                  analysis.graph.nodes.find(
                                    (n) => n.id === e.source,
                                  )?.label
                                }
                              </strong>
                              <span
                                className={
                                  "relation-text " +
                                  (e.verification_status === "thematic"
                                    ? "thematic"
                                    : "")
                                }
                              >
                                {relationNames[e.relation_type]}
                              </span>
                              <strong>
                                {
                                  analysis.graph.nodes.find(
                                    (n) => n.id === e.target,
                                  )?.label
                                }
                              </strong>
                              <p>{e.explanation}</p>
                            </li>
                          ))}
                        </ul>
                        <h3>Entidades</h3>
                        {analysis.graph.nodes.map((n) => (
                          <button
                            key={n.id}
                            className="entity-button"
                            onClick={() => selectNode(n)}
                          >
                            {typeNames[n.type]} · {n.label}
                            <ArrowUpRight size={13} />
                          </button>
                        ))}
                      </section>
                    )}
                    <div className="interpretation-note">
                      <ShieldCheck size={19} />
                      <p>
                        <strong>
                          Conexões explicáveis, conclusões responsáveis.
                        </strong>{" "}
                        Ausência nas referências recuperadas não comprova
                        exclusão. Relação temática não comprova influência.
                      </p>
                    </div>
                  </div>
                  <div
                    className="evidence-region"
                    ref={evidenceRef}
                    tabIndex={-1}
                    aria-label="Fontes da contribuição selecionada"
                  >
                    <EvidenceInspector
                      match={selected}
                      node={node}
                      paper={paper}
                    />
                  </div>
                </div>
                <details className="advanced-discovery">
                  <summary>
                    Quer ir além do catálogo? Ampliar a busca em outras fontes
                  </summary>
                  <AutomaticDiscovery
                    key={analysis.id}
                    analysis={analysis}
                    onUpdated={(result) =>
                      setAnalysis((current) =>
                        current?.id === result.id ? result : current,
                      )
                    }
                  />
                </details>
              </>
            )}
          </div>
        )}
        {busy && (
          <div className="processing" role="status">
            <LoaderCircle className="spin" size={19} />
            <span>
              {busy === "retrieving"
                ? "Consultando os metadados do artigo…"
                : "Comparando conceitos, contribuições e referências…"}
            </span>
          </div>
        )}
        {error && (
          <div
            className="error-message"
            role="alert"
            tabIndex={-1}
            ref={errorRef}
          >
            <Info size={20} />
            <div>
              <strong>Não foi possível concluir</strong>
              <p>{error}</p>
            </div>
            <button aria-label="Fechar mensagem" onClick={() => setError("")}>
              <X size={18} />
            </button>
          </div>
        )}
      </main>
      <footer className="site-footer">
        <span>
          MATILDA FORENSICS <span className="footer-divider">/</span> IFSP ·
          Campus São Paulo
        </span>
        <span>
          Ciência Delas <span className="footer-divider">/</span> Evidência
          antes de afirmação.
        </span>
      </footer>
      {about && (
        <div className="modal-backdrop" onClick={() => setAbout(false)}>
          <section
            className="about-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="about-title"
            onClick={(e) => e.stopPropagation()}
            onKeyDown={(e) => {
              if (e.key === "Escape") setAbout(false);
              if (e.key === "Tab") {
                const focusables = Array.from(
                  e.currentTarget.querySelectorAll<HTMLElement>(
                    "button,a[href]",
                  ),
                );
                const first = focusables[0],
                  last = focusables[focusables.length - 1];
                if (e.shiftKey && document.activeElement === first) {
                  e.preventDefault();
                  last.focus();
                } else if (!e.shiftKey && document.activeElement === last) {
                  e.preventDefault();
                  first.focus();
                }
              }
            }}
          >
            <button
              autoFocus
              className="close-button"
              aria-label="Fechar explicação"
              onClick={() => setAbout(false)}
            >
              <X size={20} />
            </button>
            <span className="eyebrow">NOSSO MÉTODO</span>
            <h2 id="about-title">Da pergunta à evidência.</h2>
            <p>
              O OpenAlex fornece os metadados e os identificadores citados. Um
              catálogo editorial conecta termos específicos do artigo a
              contribuições documentadas. A ampliação automática busca
              publicações relacionadas no OpenAlex e no Europe PMC e consulta
              identidades por ORCID ou ID OpenAlex no Wikidata. Os candidatos
              permanecem pendentes de revisão.
            </p>
            <p>
              As explicações usam templates determinísticos. Não há geração de
              fatos históricos por IA nem classificação de gênero pelo nome.
            </p>
            <p>
              <strong>Escopo inicial:</strong> 3 pesquisadoras, 6 contribuições,
              2 domínios. Fontes primárias sustentam as contribuições;
              biografias oficiais do Nobel documentam identidades.
            </p>
            <div className="notice">
              <Info size={19} />
              <p>
                Uma citação comprova uma ligação bibliográfica. Uma relação
                temática sugere leitura complementar. Nenhuma delas,
                isoladamente, comprova influência histórica ou discriminação.
              </p>
            </div>
            <a
              href="https://help.openalex.org/"
              target="_blank"
              rel="noreferrer"
              className="text-link"
            >
              Conheça a fonte bibliográfica
              <ArrowUpRight size={15} />
            </a>
          </section>
        </div>
      )}
    </>
  );
}

/** Keep both workspaces mounted so mode changes preserve the investigation. */
export default function App() {
  const [studio, setStudio] = useState(() =>
    location.hash.startsWith("#studio"),
  );
  const studioLocation = useRef("#studio");
  useEffect(() => {
    const update = () => setStudio(location.hash.startsWith("#studio"));
    window.addEventListener("hashchange", update);
    return () => window.removeEventListener("hashchange", update);
  }, []);
  return (
    <>
      <nav className="mode-navigation" aria-label="Modos Matilda">
        <button
          aria-pressed={!studio}
          onClick={() => {
            if (studio) studioLocation.current = location.hash;
            setStudio(false);
            history.replaceState(null, "", "#forensics");
          }}
        >
          Forensics — Investigar ciência
        </button>
        <button
          aria-pressed={studio}
          onClick={() => {
            setStudio(true);
            history.replaceState(null, "", studioLocation.current);
          }}
        >
          Studio — Criar aula
        </button>
      </nav>
      <div hidden={studio}>
        <ForensicsApp />
      </div>
      <div hidden={!studio}>
        <StudioWorkspace />
      </div>
    </>
  );
}

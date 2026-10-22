import { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { ForensicsStudioBridge } from "../src/studio/ForensicsStudioBridge";
import type { ScientificSourceSnapshot } from "../src/studio/scientific-source";
import type { PreviewRequest } from "../src/types/studio";
import { investigate } from "../src/services/api";
import crispr from "../../tests/fixtures/studio/scientific/crispr.json?url";
import rna from "../../tests/fixtures/studio/scientific/rna.json?url";
import text from "../../tests/fixtures/studio/scientific/text.json?url";
import empty from "../../tests/fixtures/studio/scientific/no-coverage.json?url";
import "../src/studio/scientific-dossier.css";
import "./style.css";

const examples = { crispr, rna, text, empty };
async function snapshot(
  name: keyof typeof examples,
): Promise<ScientificSourceSnapshot> {
  const example: Omit<ScientificSourceSnapshot, "matches"> & {
    expected_matches: ScientificSourceSnapshot["matches"];
  } = await (await fetch(examples[name])).json();
  return {
    scientific_context: { ...example.scientific_context, analysis_id: null },
    source_documents: example.source_documents,
    papers: example.papers,
    matches: example.expected_matches,
  };
}
function Harness() {
  const [name, setName] = useState<keyof typeof examples>("crispr");
  const [source, setSource] = useState<ScientificSourceSnapshot | null>(null);
  const [state, setState] = useState({
    material: "Material original conservado",
    decision: "accepted",
    slide: 3,
    view: "list",
  });
  const [transfer, setTransfer] = useState<unknown>(null);
  const [configuration, setConfiguration] = useState<PreviewRequest | null>(
    null,
  );
  const [returned, setReturned] = useState<unknown>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    void snapshot("crispr").then(setSource);
  }, []);
  if (!source)
    return <p role="status">Carregando snapshots científicos de teste…</p>;
  return (
    <main>
      <aside aria-label="Ambiente de teste">
        <strong>
          HARNESS DE TESTE T06 · Porta Studio de exemplo; sem prévia ou geração
          real.
        </strong>
        <p>
          Snapshots científicos M0 e APIs Forensics existentes. Esta tela não
          integra o host de produção.
        </p>
        <label>
          Cenário{" "}
          <select
            value={name}
            onChange={async (e) => {
              const next = e.target.value as keyof typeof examples;
              setName(next);
              setSource(await snapshot(next));
              setTransfer(null);
              setError("");
            }}
          >
            <option value="crispr">CRISPR</option>
            <option value="rna">RNA</option>
            <option value="text">Texto sem DOI</option>
            <option value="empty">Sem cobertura</option>
          </select>
        </label>
        <label>
          Material em preparação{" "}
          <textarea
            value={state.material}
            onChange={(e) => setState({ ...state, material: e.target.value })}
          />
        </label>
        {source.papers[0] && (
          <button
            onClick={async () => {
              try {
                const analysis = await investigate(source.papers[0].doi);
                setSource({
                  ...source,
                  papers: [analysis.paper],
                  matches: analysis.contributions,
                  scientific_context: {
                    ...source.scientific_context,
                    analysis_id: analysis.id,
                  },
                });
              } catch (e) {
                setError(
                  e instanceof Error ? e.message : "Falha na investigação",
                );
              }
            }}
          >
            Carregar investigação pela API Forensics
          </button>
        )}
        {error && <p role="alert">{error}</p>}
        <output aria-label="Investigação carregada">
          {source.scientific_context.analysis_id}
        </output>
      </aside>
      {configuration ? (
        <section aria-label="Configuração confirmável de teste">
          <h1>Confirmar configuração da aula</h1>
          <p>
            Defaults: Ciências · Ensino Médio · 50 minutos. Nenhuma geração foi
            solicitada.
          </p>
          <label>
            Título da aula{" "}
            <input
              value={configuration.title}
              onChange={(e) =>
                setConfiguration({ ...configuration, title: e.target.value })
              }
            />
          </label>
          <button
            onClick={() => {
              setConfiguration(null);
              setReturned(state);
            }}
          >
            Voltar à investigação
          </button>
        </section>
      ) : (
        <ForensicsStudioBridge
          source={source}
          state={state}
          onConfigure={(origin, science, received) => {
            setTransfer({ origin, snapshot: science, state: received });
            setConfiguration({
              title:
                science.papers[0]?.title.slice(0, 160) ||
                "Aula a partir do material",
              subject: "Ciências",
              education_level: "Ensino Médio",
              duration_minutes: 50,
              ...origin,
            });
          }}
          onExplore={(_id, received) => setReturned(received)}
          onReturn={(received) => setReturned(received)}
        />
      )}
      {transfer !== null && (
        <pre aria-label="Transferência recebida">
          {JSON.stringify(transfer)}
        </pre>
      )}
      {returned !== null && (
        <pre aria-label="Estado devolvido">{JSON.stringify(returned)}</pre>
      )}
    </main>
  );
}
if (import.meta.env.DEV)
  createRoot(document.getElementById("root")!).render(<Harness />);

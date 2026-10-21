import { StrictMode, useState } from "react";
import { createRoot } from "react-dom/client";
import { ReviewWorkspace } from "../src/studio/ReviewWorkspace";
import { createReviewApi } from "../src/studio/review-api";
import type { GenerateRequest } from "../src/types/studio";

const api = createReviewApi();
function Harness() {
  const [previewId, setPreviewId] = useState("preview-example");
  const [request, setRequest] = useState<GenerateRequest | null>(null);
  const [newPreview, setNewPreview] = useState(false);
  return (
    <>
      <aside
        style={{ padding: 16, background: "#fff0cb", fontFamily: "system-ui" }}
        aria-label="Ambiente de exemplos"
      >
        <strong>EXEMPLO / DESENVOLVIMENTO · API simulada</strong>
        <p>
          Dados de teste; não comprovam geração, persistência, sessão ou
          autorização reais.
        </p>
        <label>
          Prévia de exemplo{" "}
          <select
            value={previewId}
            onChange={(event) => {
              setPreviewId(event.target.value);
              setRequest(null);
              setNewPreview(false);
            }}
          >
            <option value="preview-example">CRISPR</option>
            <option value="preview-empty">Sem cobertura</option>
            <option value="preview-other">Outra prévia</option>
          </select>
        </label>
        {newPreview && (
          <p role="status">Solicitada nova prévia ao host de exemplo.</p>
        )}
        {request && (
          <pre aria-label="Pedido de geração confirmado">
            {JSON.stringify(request, null, 2)}
          </pre>
        )}
      </aside>
      <ReviewWorkspace
        previewId={previewId}
        api={api}
        onContinue={setRequest}
        onRequestNewPreview={() => {
          setNewPreview(true);
          setRequest(null);
        }}
      />
    </>
  );
}
if (import.meta.env.DEV)
  createRoot(document.getElementById("root")!).render(
    <StrictMode>
      <Harness />
    </StrictMode>,
  );

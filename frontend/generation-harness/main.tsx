import { StrictMode, useState } from "react";
import { createRoot } from "react-dom/client";
import { GenerationPanel } from "../src/studio/GenerationPanel";
import { createGenerationApi } from "../src/studio/generation-api";
const api = createGenerationApi();
function Harness() {
  const [example, setExample] = useState("success");
  const [opened, setOpened] = useState("");
  return (
    <>
      <aside
        style={{ background: "#ffefc1", padding: 20, fontFamily: "system-ui" }}
        aria-label="Ambiente de exemplos"
      >
        <strong>EXEMPLO / DESENVOLVIMENTO · GEMINI SIMULADO</strong>
        <p>
          Orquestrador, validador e SQLite isolado reais; provedor, sessão e
          revisão de referência simulados. Não comprova a integração de
          produção.
        </p>
        <label>
          Cenário{" "}
          <select
            value={example}
            onChange={(event) => {
              setExample(event.target.value);
              setOpened("");
            }}
          >
            {[
              "success",
              "invalid",
              "timeout",
              "unauthorized",
              "slow",
              "empty",
              "pending",
            ].map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
        {opened && (
          <p aria-label="Aula selecionada">Resultado recebido: {opened}</p>
        )}
      </aside>
      <GenerationPanel
        request={{
          preview_id: `preview-${example}`,
          review_revision: example === "pending" ? 0 : 1,
          accepted_suggestion_ids:
            example === "empty" || example === "pending"
              ? []
              : ["suggestion-1"],
        }}
        api={api}
        onOpenLesson={setOpened}
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

import { StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import type { LessonBundle } from "../src/types/lesson";
import { LessonWorkspace } from "../src/lesson/LessonWorkspace";
import crispr from "../../tests/fixtures/studio/lessons/crispr-50.json";
import rna from "../../tests/fixtures/studio/lessons/rna-50.json";
import empty from "../../tests/fixtures/studio/lessons/no-enrichment-50.json";
import optional from "../../tests/fixtures/studio/lessons/optional-fields.json";
import "./style.css";

// This entry is served only by the separate development harness, never the product build.
const examples = { crispr, rna, empty, optional };
declare global {
  interface Window {
    setLessonExample: (bundle: LessonBundle) => void;
  }
}
function Harness() {
  const [bundle, setBundle] = useState<LessonBundle>(crispr as LessonBundle);
  useEffect(() => {
    window.setLessonExample = setBundle;
    return () => {
      Reflect.deleteProperty(window, "setLessonExample");
    };
  }, []);
  return (
    <>
      <aside
        className="lesson-example-banner"
        aria-label="Ambiente de exemplos"
      >
        <strong>EXEMPLO / DESENVOLVIMENTO</strong>
        <span>
          Dados de teste. Esta aula não foi gerada por IA nem pertence a um
          professor. Download usa o host de exportação de desenvolvimento;
          autorização e repositório são simulados.
        </span>
        <label>
          Exemplo{" "}
          <select
            defaultValue="crispr"
            onChange={(event) => {
              const name = event.target.value;
              if (Object.hasOwn(examples, name))
                setBundle(
                  examples[name as keyof typeof examples] as LessonBundle,
                );
            }}
          >
            <option value="crispr">CRISPR · 50 min</option>
            <option value="rna">RNA · 50 min</option>
            <option value="empty">Sem enriquecimentos</option>
            <option value="optional">Campos opcionais</option>
          </select>
        </label>
      </aside>
      <LessonWorkspace bundle={bundle} />
    </>
  );
}
if (import.meta.env.DEV)
  createRoot(document.getElementById("root")!).render(
    <StrictMode>
      <Harness />
    </StrictMode>,
  );

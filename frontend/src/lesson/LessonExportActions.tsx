import { useEffect, useRef, useState } from "react";
import {
  createLessonExportApi,
  downloadMarkdown,
  type LessonExportApi,
} from "./export-api";

const httpApi = createLessonExportApi();

export function LessonExportActions({
  bundleId,
  api = httpApi,
}: {
  bundleId: string;
  api?: LessonExportApi;
}) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [failed, setFailed] = useState(false);
  const operation = useRef<AbortController | null>(null);
  const feedback = useRef<HTMLParagraphElement>(null);
  const printButton = useRef<HTMLButtonElement>(null);
  const printRequested = useRef(false);
  useEffect(() => () => operation.current?.abort(), []);
  useEffect(() => {
    const restoreFocus = () => {
      if (printRequested.current) {
        printRequested.current = false;
        window.requestAnimationFrame(() => printButton.current?.focus());
      }
    };
    window.addEventListener("afterprint", restoreFocus);
    return () => window.removeEventListener("afterprint", restoreFocus);
  }, []);
  useEffect(() => {
    if (message) feedback.current?.focus();
  }, [message]);

  async function exportLesson() {
    if (operation.current) return;
    const controller = new AbortController();
    operation.current = controller;
    setBusy(true);
    setMessage("");
    setFailed(false);
    try {
      const file = await api.getMarkdown(bundleId, controller.signal);
      if (controller.signal.aborted) return;
      downloadMarkdown(file);
      setMessage("Download de Markdown iniciado.");
    } catch (error) {
      if (controller.signal.aborted) return;
      setFailed(true);
      // The adapter produces safe messages; injected ports may throw arbitrary bodies.
      setMessage(
        error instanceof Error &&
          [
            "Aula indisponível ou sessão expirada. Consulte a aula antes de tentar novamente.",
            "A exportação não retornou um arquivo Markdown válido.",
          ].includes(error.message)
          ? error.message
          : "Não foi possível exportar o Markdown. Tente novamente.",
      );
    } finally {
      if (!controller.signal.aborted) {
        operation.current = null;
        setBusy(false);
      }
    }
  }

  return (
    <section aria-label="Exportar aula">
      <div className="lesson-export-actions">
        <button
          type="button"
          disabled={busy}
          onClick={() => void exportLesson()}
        >
          {busy ? "Preparando download…" : "Baixar Markdown"}
        </button>
        <button
          ref={printButton}
          type="button"
          onClick={() => {
            printRequested.current = true;
            window.print();
          }}
        >
          Imprimir plano / salvar PDF
        </button>
        <span>
          Exportações usam esta aula. Nenhuma nova geração é solicitada.
        </span>
      </div>
      {message && (
        <p ref={feedback} tabIndex={-1} role={failed ? "alert" : "status"}>
          {message}
        </p>
      )}
    </section>
  );
}

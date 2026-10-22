import { useEffect, useState, type FormEvent } from "react";
import type { EnrichmentPreview, PreviewRequest } from "../types/studio";
import { studioApi, StudioApiError, studioErrorMessage } from "./api";
import { StudioSetup, initialSetup } from "./StudioSetup";
import { PreviewPanel } from "./PreviewPanel";
import "./studio.css";

export function StudioWorkspace() {
  const [setup, setSetup] = useState<PreviewRequest>(initialSetup);
  const [preview, setPreview] = useState<EnrichmentPreview | null>(null);
  const [editing, setEditing] = useState(true);
  const [busy, setBusy] = useState(false);
  const [slow, setSlow] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    const restore = async () => {
      const match = location.hash.match(/^#studio\/previews\/([^/]+)$/);
      if (!match) return;
      setBusy(true);
      setError("");
      try {
        const result = await studioApi.getPreview(decodeURIComponent(match[1]));
        if (!active) return;
        setPreview(result);
        setError(
          result.last_error ? studioErrorMessage(result.last_error.code) : "",
        );
        setEditing(false);
        setSetup({
          title: result.project.title,
          subject: result.project.subject,
          education_level: result.project.education_level,
          duration_minutes: result.project.duration_minutes,
          objectives: result.project.learning_objectives,
          material_text:
            result.source_documents.find((document) => document.type === "text")
              ?.content || "",
          concepts:
            result.source_documents
              .find((document) => document.type === "concept_list")
              ?.content.split("\n") || [],
          project_id: result.project_id,
        });
      } catch (error) {
        if (active) setError((error as Error).message);
      } finally {
        if (active) setBusy(false);
      }
    };
    void restore();
    window.addEventListener("hashchange", restore);
    return () => {
      active = false;
      window.removeEventListener("hashchange", restore);
    };
  }, []);
  useEffect(() => {
    if (!busy) {
      setSlow(false);
      return;
    }
    const timer = window.setTimeout(() => setSlow(true), 30000);
    return () => window.clearTimeout(timer);
  }, [busy]);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      const result = await studioApi.createPreview({
        ...setup,
        concepts: (setup.concepts || [])
          .map((value) => value.trim())
          .filter(Boolean),
        objectives: (setup.objectives || [])
          .map((value) => value.trim())
          .filter(Boolean),
      });
      setPreview(result);
      setEditing(false);
      setSetup((previous) => ({ ...previous, project_id: result.project_id }));
      // Replace without a hashchange/refetch; GET is used when resuming the URL.
      history.replaceState(
        null,
        "",
        `#studio/previews/${encodeURIComponent(result.preview_id)}`,
      );
      setTimeout(
        () => document.getElementById("studio-preview-title")?.focus(),
        0,
      );
    } catch (error) {
      setError((error as Error).message);
      if (error instanceof StudioApiError && error.projectId)
        setSetup((previous) => ({ ...previous, project_id: error.projectId }));
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="studio-workspace" id="studio-main">
      {editing || !preview ? (
        <StudioSetup
          value={setup}
          onChange={setSetup}
          onSubmit={submit}
          busy={busy}
        />
      ) : (
        <PreviewPanel preview={preview} onEdit={() => setEditing(true)} />
      )}
      {busy && (
        <p role="status" aria-live="polite" className="studio-notice">
          {slow
            ? "A prévia está demorando mais que a meta de 30 segundos. A operação continua até o limite do servidor."
            : "Preparando a prévia: consultando ciência e propostas pedagógicas…"}
        </p>
      )}
      {error && (
        <p role="alert" className="studio-error">
          {error}
        </p>
      )}
    </main>
  );
}

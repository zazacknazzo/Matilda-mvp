import { useEffect, useRef, useState, type FormEvent } from "react";
import type {
  EnrichmentPreview,
  GenerateRequest,
  PreviewRequest,
} from "../types/studio";
import type { LessonBundle } from "../types/lesson";
import { getLesson } from "../lesson/api";
import { LessonWorkspace } from "../lesson/LessonWorkspace";
import { studioApi, StudioApiError, studioErrorMessage } from "./api";
import { StudioSetup, initialSetup } from "./StudioSetup";
import { PreviewPanel } from "./PreviewPanel";
import { ReviewWorkspace } from "./ReviewWorkspace";
import { createReviewApi } from "./review-api";
import { GenerationPanel } from "./GenerationPanel";
import { createGenerationApi } from "./generation-api";
import "./studio.css";

const reviewApi = createReviewApi();
const generationApi = createGenerationApi();
type View = "setup" | "preview" | "review" | "generation" | "lesson";

function setupFrom(value: EnrichmentPreview): PreviewRequest {
  return {
    title: value.project.title,
    subject: value.project.subject,
    education_level: value.project.education_level,
    duration_minutes: value.project.duration_minutes,
    objectives: value.project.learning_objectives,
    material_text:
      value.source_documents.find((doc) => doc.type === "text")?.content || "",
    concepts:
      value.source_documents
        .find((doc) => doc.type === "concept_list")
        ?.content.split("\n") || [],
    project_id: value.project_id,
    doi: value.scientific_context.analysis_id
      ? undefined
      : value.source_documents.find((doc) => doc.type === "paper_metadata")
          ?.doi || undefined,
    analysis_id: value.scientific_context.analysis_id || undefined,
  };
}

export function StudioWorkspace() {
  const [setup, setSetup] = useState<PreviewRequest>(initialSetup);
  const [preview, setPreview] = useState<EnrichmentPreview | null>(null);
  const [bundle, setBundle] = useState<LessonBundle | null>(null);
  const [generation, setGeneration] = useState<GenerateRequest | null>(null);
  const [view, setView] = useState<View>("setup");
  const [busy, setBusy] = useState(false);
  const [slow, setSlow] = useState(false);
  const [error, setError] = useState("");
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    let active = true;
    let revision = 0;
    const restore = async () => {
      const current = ++revision;
      const lesson = location.hash.match(/^#studio\/lessons\/([^/]+)$/);
      const match = location.hash.match(
        /^#studio\/previews\/([^/]+)(?:\/(review|generate))?$/,
      );
      if (!lesson && !match) {
        if (location.hash === "#studio") setView("setup");
        setBusy(false);
        return;
      }
      setBusy(true);
      setError("");
      if (lesson) {
        setBundle(null);
        setView("lesson");
      } else {
        setPreview(null);
        setGeneration(null);
        setView(
          match?.[2] === "review"
            ? "review"
            : match?.[2] === "generate"
              ? "generation"
              : "preview",
        );
      }
      try {
        if (lesson) {
          const result = await getLesson(decodeURIComponent(lesson[1]));
          if (!active || current !== revision) return;
          setBundle(result);
          setView("lesson");
        } else if (match) {
          const result = await studioApi.getPreview(
            decodeURIComponent(match[1]),
          );
          if (!active || current !== revision) return;
          setPreview(result);
          setSetup(setupFrom(result));
          setError(
            result.last_error ? studioErrorMessage(result.last_error.code) : "",
          );
          if (match[2] === "generate") {
            setGeneration({
              preview_id: result.preview_id,
              review_revision: result.review_revision,
              accepted_suggestion_ids: result.suggestions
                .filter((item) => item.status === "accepted")
                .map((item) => item.id),
            });
            setView("generation");
          } else setView(match[2] === "review" ? "review" : "preview");
        }
      } catch (failure) {
        if (active && current === revision)
          setError((failure as Error).message);
      } finally {
        if (active && current === revision) setBusy(false);
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
    heading.current?.focus();
  }, [view, bundle?.lesson_bundle_id, preview?.preview_id]);
  useEffect(() => {
    if (!busy) {
      setSlow(false);
      return;
    }
    const timer = window.setTimeout(() => setSlow(true), 30000);
    return () => window.clearTimeout(timer);
  }, [busy]);

  function navigate(path: string) {
    location.hash = path;
  }
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
      setSetup(setupFrom(result));
      setView("preview");
      history.replaceState(
        null,
        "",
        `#studio/previews/${encodeURIComponent(result.preview_id)}`,
      );
    } catch (failure) {
      setError((failure as Error).message);
      if (failure instanceof StudioApiError && failure.projectId)
        setSetup((previous) => ({
          ...previous,
          project_id: failure.projectId,
        }));
    } finally {
      setBusy(false);
    }
  }
  function edit() {
    setView("setup");
    history.replaceState(null, "", "#studio");
  }
  const labels: Record<View, string> = {
    setup: "Preparar aula",
    preview: "Prévia da aula",
    review: "Revisar a prévia",
    generation: "Gerar aula",
    lesson: "Aula salva",
  };
  return (
    <div className="studio-workspace" id="studio-main">
      <h2 ref={heading} tabIndex={-1}>
        {labels[view]}
      </h2>
      {view === "setup" && (
        <StudioSetup
          value={setup}
          onChange={setSetup}
          onSubmit={submit}
          busy={busy}
        />
      )}
      {view === "preview" && preview && (
        <>
          <PreviewPanel preview={preview} onEdit={edit} />
          <button
            disabled={busy}
            onClick={() =>
              navigate(
                `studio/previews/${encodeURIComponent(preview.preview_id)}/review`,
              )
            }
          >
            Revisar fontes e objetivos
          </button>
        </>
      )}
      {view === "review" && preview && !busy && (
        <ReviewWorkspace
          previewId={preview.preview_id}
          api={reviewApi}
          onRequestNewPreview={edit}
          onContinue={(request) => {
            setGeneration(request);
            setView("generation");
            setError("");
            history.replaceState(
              null,
              "",
              `#studio/previews/${encodeURIComponent(request.preview_id)}/generate`,
            );
          }}
        />
      )}
      {view === "generation" && generation && !busy && (
        <>
          <button
            onClick={() =>
              navigate(
                `studio/previews/${encodeURIComponent(generation.preview_id)}/review`,
              )
            }
          >
            Voltar à revisão
          </button>
          <GenerationPanel
            request={generation}
            api={generationApi}
            onOpenLesson={(id) =>
              navigate(`studio/lessons/${encodeURIComponent(id)}`)
            }
          />
        </>
      )}
      {view === "lesson" && bundle && !busy && (
        <>
          <button
            onClick={() =>
              navigate(
                `studio/previews/${encodeURIComponent(bundle.preview_id)}/review`,
              )
            }
          >
            Voltar à revisão
          </button>
          <LessonWorkspace bundle={bundle} />
        </>
      )}
      {busy && (
        <p role="status" aria-live="polite" className="studio-notice">
          {slow
            ? "A prévia está demorando mais que a meta de 30 segundos. A operação continua até o limite do servidor."
            : "Preparando a prévia ou consultando material salvo…"}
        </p>
      )}
      {error && (
        <p role="alert" className="studio-error">
          {error}
        </p>
      )}
    </div>
  );
}

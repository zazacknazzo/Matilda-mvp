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
import type { ExploreAnalysis } from "./ForensicsStudioBridge";
import { ScientificDossier } from "./ScientificDossier";
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

export function StudioWorkspace({
  origin,
  onExploreAnalysis,
}: {
  onExploreAnalysis?: ExploreAnalysis;
  origin?: { analysis_id: string; title: string } | null;
}) {
  const [setup, setSetup] = useState<PreviewRequest>(initialSetup);
  const [preview, setPreview] = useState<EnrichmentPreview | null>(null);
  const [bundle, setBundle] = useState<LessonBundle | null>(null);
  const [generation, setGeneration] = useState<GenerateRequest | null>(null);
  const [view, setView] = useState<View>("setup");
  const [busy, setBusy] = useState(false);
  const [slow, setSlow] = useState(false);
  const [error, setError] = useState("");
  const [exploring, setExploring] = useState<string | null>(null);
  const exploreTrigger = useRef<HTMLButtonElement>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  const operationRevision = useRef(0);
  useEffect(() => {
    if (!origin) return;
    operationRevision.current++;
    setBusy(false);
    setExploring(null);
    setSetup((value) => ({
      ...value,
      title: origin.title,
      analysis_id: origin.analysis_id,
      doi: null,
      project_id: null,
    }));
    setPreview(null);
    setGeneration(null);
    setBundle(null);
    setView("setup");
    setError("");
    heading.current?.focus();
  }, [origin]);
  useEffect(() => {
    let active = true;
    const restore = async () => {
      const current = ++operationRevision.current;
      setExploring(null);
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
        setPreview(null);
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
          if (!active || current !== operationRevision.current) return;
          setBundle(result);
          setView("lesson");
          // Lesson delivery remains usable if its original preview is unavailable.
          try {
            const science = await studioApi.getPreview(result.preview_id);
            if (active && current === operationRevision.current)
              setPreview(science);
          } catch {
            /* Existing bundle references remain available in the lesson. */
          }
        } else if (match) {
          const result = await studioApi.getPreview(
            decodeURIComponent(match[1]),
          );
          if (!active || current !== operationRevision.current) return;
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
        if (active && current === operationRevision.current)
          setError((failure as Error).message);
      } finally {
        if (active && current === operationRevision.current) setBusy(false);
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
    const current = ++operationRevision.current;
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
      if (current !== operationRevision.current) return;
      setPreview(result);
      setSetup(setupFrom(result));
      setView("preview");
      history.replaceState(
        null,
        "",
        `#studio/previews/${encodeURIComponent(result.preview_id)}`,
      );
    } catch (failure) {
      if (current !== operationRevision.current) return;
      setError((failure as Error).message);
      if (failure instanceof StudioApiError && failure.projectId)
        setSetup((previous) => ({
          ...previous,
          project_id: failure.projectId,
        }));
    } finally {
      if (current === operationRevision.current) setBusy(false);
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
    <div className="studio-workspace" id="studio-main" tabIndex={-1}>
      <ol className="studio-steps" aria-label="Etapas da aula">
        {(["setup", "preview", "review", "generation", "lesson"] as const).map(
          (step, index) => (
            <li key={step} aria-current={view === step ? "step" : undefined}>
              <span aria-hidden="true">
                {String(index + 1).padStart(2, "0")}
              </span>
              {
                {
                  setup: "Preparar",
                  preview: "Conferir",
                  review: "Revisar",
                  generation: "Gerar",
                  lesson: "Aula",
                }[step]
              }
            </li>
          ),
        )}
      </ol>
      <h2 ref={heading} tabIndex={-1} className="studio-view-label">
        {labels[view]}
      </h2>
      <div hidden={exploring !== null}>
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
            <PreviewPanel
              preview={preview}
              onEdit={edit}
              busy={busy}
              onReview={() =>
                navigate(
                  `studio/previews/${encodeURIComponent(preview.preview_id)}/review`,
                )
              }
            />
          </>
        )}
        {view === "review" && preview && !busy && (
          <ReviewWorkspace
            onExploreAnalysis={onExploreAnalysis}
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
            {preview?.preview_id === bundle.preview_id &&
              bundle.references.length > 0 && (
                <ul aria-label="Contribuições científicas da aula">
                  {bundle.references
                    .filter(
                      (ref, index, all) =>
                        all.findIndex(
                          (item) =>
                            item.contribution_id === ref.contribution_id,
                        ) === index,
                    )
                    .map((reference) => (
                      <li key={reference.contribution_id}>
                        <button
                          onClick={async (event) => {
                            const trigger = event.currentTarget;
                            exploreTrigger.current = trigger;
                            const id = preview.scientific_context.analysis_id;
                            if (
                              id &&
                              onExploreAnalysis &&
                              (await onExploreAnalysis(
                                id,
                                reference.contribution_id,
                                () => trigger.focus(),
                              ))
                            )
                              return;
                            setExploring(reference.contribution_id);
                          }}
                        >
                          Explorar fontes da aula · {reference.source_title}
                        </button>
                      </li>
                    ))}
                </ul>
              )}
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
      {exploring && preview && (
        <ScientificDossier
          preview={preview}
          contributionId={exploring}
          onBack={() => {
            setExploring(null);
            requestAnimationFrame(() => exploreTrigger.current?.focus());
          }}
        />
      )}
    </div>
  );
}

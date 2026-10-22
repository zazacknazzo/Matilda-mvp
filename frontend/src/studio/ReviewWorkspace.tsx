import { useEffect, useRef, useState } from "react";
import type {
  EnrichmentPreview,
  GenerateRequest,
  ReviewDecision,
  ReviewRequest,
} from "../types/studio";
import { type ReviewApi, reviewErrorMessage } from "./review-api";
import { SuggestionCard, type SuggestionEdit } from "./SuggestionCard";
import "./review.css";
import { ScientificDossier } from "./ScientificDossier";

interface Props {
  previewId: string;
  api: ReviewApi;
  onContinue: (request: GenerateRequest) => void;
  /** Host must create a new preview after changing source/material/configuration. */
  onRequestNewPreview: () => void;
}

function editsFrom(preview: EnrichmentPreview): Record<string, SuggestionEdit> {
  return Object.fromEntries(
    preview.suggestions.map((item) => [
      item.id,
      {
        status: item.status,
        suggested_content: item.suggested_content,
        pedagogical_rationale: item.pedagogical_rationale,
      },
    ]),
  );
}

// UI guards for server-validated T03 payloads; scientific authority stays on the server.
function previewIsUsable(preview: EnrichmentPreview, id: string): boolean {
  try {
    return (
      preview.schema_version === 1 &&
      preview.preview_id === id &&
      preview.project_id === preview.project.id &&
      preview.expires_at === preview.project.expires_at &&
      Number.isInteger(preview.review_revision) &&
      preview.review_revision >= 0 &&
      Number.isFinite(Date.parse(preview.expires_at)) &&
      new Set(preview.suggestions.map((item) => item.id)).size ===
        preview.suggestions.length &&
      new Set(preview.evidence_references.map((item) => item.id)).size ===
        preview.evidence_references.length &&
      preview.suggestions.every(
        (item) =>
          item.project_id === preview.project_id &&
          ["pending", "accepted", "rejected"].includes(item.status) &&
          item.evidence_ids.every((id) =>
            preview.evidence_references.some(
              (ref) =>
                ref.id === id && ref.contribution_id === item.contribution_id,
            ),
          ) &&
          preview.source_documents.some(
            (doc) => doc.id === item.source_anchor.source_document_id,
          ),
      )
    );
  } catch {
    return false;
  }
}

export function ReviewWorkspace(props: Props) {
  // Changing preview identity unmounts the old draft and cancels its pending requests.
  return <ReviewSession key={props.previewId} {...props} />;
}

function ReviewSession({
  previewId,
  api,
  onContinue,
  onRequestNewPreview,
}: Props) {
  const [preview, setPreview] = useState<EnrichmentPreview | null>(null);
  const [loadError, setLoadError] = useState("");
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setLoadError("");
    api
      .getPreview(previewId, controller.signal)
      .then((value) => {
        if (controller.signal.aborted) return;
        if (!previewIsUsable(value, previewId))
          throw new Error("invalid response");
        setPreview(value);
      })
      .catch((error) => {
        if (!controller.signal.aborted) setLoadError(reviewErrorMessage(error));
      });
    return () => controller.abort();
  }, [api, previewId, attempt]);
  if (!preview)
    return (
      <section className="review-workspace" aria-label="Revisão docente">
        <h1>Revisão docente</h1>
        {loadError ? (
          <>
            <p role="alert">{loadError}</p>
            <button onClick={() => setAttempt((value) => value + 1)}>
              Tentar consultar novamente
            </button>
          </>
        ) : (
          <p role="status">Consultando prévia…</p>
        )}
      </section>
    );
  return (
    <ReviewEditor
      initialPreview={preview}
      api={api}
      onContinue={onContinue}
      onRequestNewPreview={onRequestNewPreview}
    />
  );
}

function ReviewEditor({
  initialPreview,
  api,
  onContinue,
  onRequestNewPreview,
}: Omit<Props, "previewId"> & { initialPreview: EnrichmentPreview }) {
  const [preview, setPreview] = useState(initialPreview);
  const [exploring, setExploring] = useState<string | null>(null);
  const exploreTrigger = useRef<HTMLButtonElement | null>(null);
  const [edits, setEdits] = useState(() => editsFrom(initialPreview));
  const [objectives, setObjectives] = useState(() =>
    (initialPreview.approved_objectives.length
      ? initialPreview.approved_objectives
      : initialPreview.project.learning_objectives.length
        ? initialPreview.project.learning_objectives
        : initialPreview.suggested_objectives
    ).join("\n"),
  );
  const [approved, setApproved] = useState(
    initialPreview.approved_objectives.length > 0,
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [uncertain, setUncertain] = useState(false);
  const [confirm, setConfirm] = useState<"reload" | "new" | null>(null);
  const [invalidated, setInvalidated] = useState(false);
  const [now, setNow] = useState(Date.now);
  const operation = useRef<AbortController | null>(null);
  const feedback = useRef<HTMLParagraphElement>(null);
  const confirmationTrigger = useRef<HTMLButtonElement | null>(null);
  useEffect(() => () => operation.current?.abort(), []);
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);
  useEffect(() => {
    if (error || notice) feedback.current?.focus();
  }, [error, notice]);

  const approvedObjectives = objectives
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
  const objectivesValid =
    approved &&
    approvedObjectives.length >= 1 &&
    approvedObjectives.length <= 10 &&
    approvedObjectives.every((item) => Array.from(item).length <= 300);
  const pending = preview.suggestions.filter(
    (item) => edits[item.id].status === "pending",
  ).length;
  const dirty =
    JSON.stringify(edits) !== JSON.stringify(editsFrom(preview)) ||
    !approved ||
    JSON.stringify(approvedObjectives) !==
      JSON.stringify(preview.approved_objectives);
  const expired = now >= Date.parse(preview.expires_at);
  const frozen = preview.generation_status === "generating";
  const blocked = busy || expired || frozen || invalidated || confirm !== null;
  const undecidedEdit = preview.suggestions.some(
    (item) =>
      edits[item.id].status === "pending" &&
      (edits[item.id].suggested_content !== item.suggested_content ||
        edits[item.id].pedagogical_rationale !== item.pedagogical_rationale),
  );
  const contentValid = Object.values(edits).every(
    (item) =>
      item.suggested_content.trim() &&
      item.pedagogical_rationale.trim() &&
      Array.from(item.suggested_content).length <= 20000 &&
      Array.from(item.pedagogical_rationale).length <= 20000,
  );
  const canContinue =
    !blocked && !uncertain && !dirty && objectivesValid && pending === 0;

  function resetTo(value: EnrichmentPreview) {
    setPreview(value);
    setEdits(editsFrom(value));
    setObjectives(
      (value.approved_objectives.length
        ? value.approved_objectives
        : value.project.learning_objectives.length
          ? value.project.learning_objectives
          : value.suggested_objectives
      ).join("\n"),
    );
    setApproved(value.approved_objectives.length > 0);
    setUncertain(false);
  }

  async function perform(kind: "save" | "reload") {
    if (operation.current || invalidated) return;
    const controller = new AbortController();
    operation.current = controller;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const decisions: ReviewDecision[] = preview.suggestions.flatMap(
        (item) => {
          const edit = edits[item.id];
          return edit.status === "pending"
            ? []
            : [
                {
                  suggestion_id: item.id,
                  status: edit.status,
                  pedagogical_rationale: edit.pedagogical_rationale,
                  suggested_content: edit.suggested_content,
                },
              ];
        },
      );
      const request: ReviewRequest = {
        review_revision: preview.review_revision,
        decisions,
        approved_objectives: approvedObjectives,
      };
      const value =
        kind === "save"
          ? await api.saveReview(preview.preview_id, request, controller.signal)
          : await api.getPreview(preview.preview_id, controller.signal);
      if (controller.signal.aborted) return;
      if (
        !previewIsUsable(value, preview.preview_id) ||
        (kind === "save" &&
          value.review_revision !== preview.review_revision + 1)
      )
        throw new Error("invalid response");
      resetTo(value);
      setNotice(
        kind === "save"
          ? "Revisão salva. As decisões exibidas foram confirmadas pela API."
          : "Versão salva carregada. Confira as decisões antes de continuar.",
      );
    } catch (failure) {
      if (controller.signal.aborted) return;
      setError(reviewErrorMessage(failure));
      // A response may be lost after a successful write; require reconciliation by GET.
      setUncertain(true);
    } finally {
      if (!controller.signal.aborted) {
        operation.current = null;
        setBusy(false);
      }
    }
  }

  return (
    <>
      <main
        className="review-workspace"
        aria-label="Revisão docente"
        hidden={exploring !== null}
      >
        <header className="review-heading">
          <div>
            <p>Matilda Studio · Revisão docente</p>
            <h1>{preview.project.title}</h1>
            <p>
              {preview.project.subject} · {preview.project.education_level} ·{" "}
              {preview.project.duration_minutes} minutos
            </p>
          </div>
          <p>
            Disponível até{" "}
            <time dateTime={preview.expires_at}>
              {new Intl.DateTimeFormat("pt-BR", {
                dateStyle: "short",
                timeStyle: "short",
              }).format(new Date(preview.expires_at))}
            </time>
            <br />
            Revisão {preview.review_revision}
          </p>
        </header>
        <p>
          Revise as fontes, decida sobre cada sugestão e aprove os objetivos.
          Apenas a proposta pedagógica e sua justificativa podem ser editadas.
        </p>
        {expired && (
          <p role="alert">
            Esta prévia expirou. Prepare uma nova prévia para continuar.
          </p>
        )}
        {frozen && (
          <p role="status">
            Geração em andamento. A revisão está bloqueada; consulte a versão
            salva para atualizar o estado.
          </p>
        )}
        {invalidated && (
          <p role="alert">
            A revisão anterior foi invalidada. Alterar material, origem ou
            configuração exige nova prévia e nova aprovação.
          </p>
        )}
        <div className="review-columns">
          <section aria-label="Material original" className="review-material">
            <h2>Material original</h2>
            {preview.source_documents.map((doc) => (
              <div key={doc.id}>
                <h3>{doc.title}</h3>
                <p className="review-literal">{doc.content}</p>
              </div>
            ))}
            <h3>Conceitos e procedência</h3>
            <ul>
              {preview.concepts.map((concept) => (
                <li key={concept.id}>
                  {concept.name} · {concept.provenance.join(", ")}
                </li>
              ))}
            </ul>
          </section>
          <section aria-label="Sugestões de enriquecimento">
            <h2>Sugestões de enriquecimento</h2>
            {preview.suggestions.length === 0 && (
              <p>
                Sem sugestões científicas nesta prévia. Isso não indica
                inexistência de contribuições femininas. Você pode continuar sem
                enriquecimentos após aprovar os objetivos.
              </p>
            )}
            {preview.suggestions.map((suggestion) => (
              <SuggestionCard
                key={suggestion.id}
                suggestion={suggestion}
                preview={preview}
                edit={edits[suggestion.id]}
                disabled={blocked}
                onExplore={(event) => {
                  exploreTrigger.current = event.currentTarget;
                  setExploring(suggestion.contribution_id);
                }}
                onChange={(edit) => {
                  setEdits((value) => ({ ...value, [suggestion.id]: edit }));
                  setNotice("");
                }}
              />
            ))}
          </section>
        </div>
        <section aria-label="Objetivos da aula">
          <h2>Objetivos da aula</h2>
          <fieldset disabled={blocked}>
            <legend>Revisão e aprovação dos objetivos</legend>
            <label>
              Objetivos de aprendizagem · um por linha
              <textarea
                value={objectives}
                onChange={(event) => {
                  setObjectives(event.target.value);
                  setApproved(false);
                  setNotice("");
                }}
                aria-describedby="review-objective-help"
              />
            </label>
            <p id="review-objective-help">
              Informe de 1 a 10 objetivos, com até 300 caracteres cada. Quando
              não há objetivos originais, as sugestões precisam da sua
              aprovação.
            </p>
            <label>
              <input
                type="checkbox"
                checked={approved}
                onChange={(event) => {
                  setApproved(event.target.checked);
                  setNotice("");
                }}
              />{" "}
              Revisei e aprovo estes objetivos
            </label>
          </fieldset>
        </section>
        <section aria-label="Limitações">
          <h2>Limitações e cobertura</h2>
          <ul>
            {preview.limitations.map((item, index) => (
              <li key={index}>{item}</li>
            ))}
          </ul>
        </section>
        <footer className="review-actions">
          <p>
            {pending} sugestão(ões) pendente(s).{" "}
            {dirty
              ? "Há alterações ainda não confirmadas."
              : "A revisão exibida corresponde à versão salva."}
          </p>
          <p>
            Você pode salvar decisões parciais. Para continuar, decida todas as
            sugestões, aprove os objetivos e salve. Rejeitar todas é válido.
          </p>
          {undecidedEdit && (
            <p role="status">
              Aceite ou rejeite a sugestão editada antes de salvar sua proposta
              pedagógica.
            </p>
          )}
          {!contentValid && (
            <p role="status">
              Preencha proposta e justificativa com até 20.000 caracteres cada.
            </p>
          )}
          <div className="review-buttons">
            <button
              disabled={
                blocked ||
                uncertain ||
                !dirty ||
                !objectivesValid ||
                !contentValid ||
                undecidedEdit
              }
              onClick={() => void perform("save")}
            >
              {busy ? "Aguarde…" : "Salvar revisão"}
            </button>
            <button
              disabled={busy || invalidated || confirm !== null}
              onClick={(event) => {
                confirmationTrigger.current = event.currentTarget;
                if (dirty) setConfirm("reload");
                else void perform("reload");
              }}
            >
              Consultar versão salva
            </button>
            <button
              disabled={!canContinue}
              onClick={() =>
                onContinue({
                  preview_id: preview.preview_id,
                  review_revision: preview.review_revision,
                  accepted_suggestion_ids: preview.suggestions
                    .filter((item) => item.status === "accepted")
                    .map((item) => item.id),
                })
              }
            >
              Continuar para geração
            </button>
            <button
              disabled={busy || invalidated || confirm !== null}
              onClick={(event) => {
                confirmationTrigger.current = event.currentTarget;
                setConfirm("new");
              }}
            >
              Alterar material, origem ou configuração
            </button>
          </div>
          {(error || notice) && (
            <p ref={feedback} tabIndex={-1} role={error ? "alert" : "status"}>
              {error || notice}
            </p>
          )}
          {confirm && (
            <div
              className="review-confirm"
              role="group"
              aria-label="Confirmação"
            >
              <p>
                {confirm === "reload"
                  ? "Carregar a versão salva substitui as edições desta tela. Deseja continuar?"
                  : "Alterar a entrada invalida esta revisão e exige nova prévia. Deseja continuar?"}
              </p>
              <button
                autoFocus
                onClick={() => {
                  const action = confirm;
                  setConfirm(null);
                  if (action === "reload") void perform("reload");
                  else {
                    setInvalidated(true);
                    onRequestNewPreview();
                  }
                }}
              >
                Confirmar
              </button>
              <button
                onClick={() => {
                  setConfirm(null);
                  window.requestAnimationFrame(() =>
                    confirmationTrigger.current?.focus(),
                  );
                }}
              >
                Cancelar
              </button>
            </div>
          )}
        </footer>
      </main>
      {exploring && (
        <ScientificDossier
          preview={preview}
          contributionId={exploring}
          onBack={() => {
            setExploring(null);
            requestAnimationFrame(() => exploreTrigger.current?.focus());
          }}
        />
      )}
    </>
  );
}

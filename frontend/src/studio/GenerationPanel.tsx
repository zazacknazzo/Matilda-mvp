import { useCallback, useEffect, useRef, useState } from "react";
import type { EnrichmentPreview, GenerateRequest } from "../types/studio";
import {
  type GenerationApi,
  GenerationApiError,
  generationMessage,
} from "./generation-api";
import "./generation.css";

interface Props {
  request: GenerateRequest;
  api: GenerationApi;
  onOpenLesson: (id: string) => void;
}

function operationKey(request: GenerateRequest) {
  const storageKey = `matilda:generation:v1:${encodeURIComponent(request.preview_id)}:${request.review_revision}`;
  try {
    const saved = sessionStorage.getItem(storageKey);
    if (saved && /^[a-zA-Z0-9_-]{1,128}$/.test(saved)) return saved;
    const key = crypto.randomUUID();
    sessionStorage.setItem(storageKey, key);
    return key;
  } catch {
    return crypto.randomUUID();
  }
}

function reviewed(
  preview: EnrichmentPreview,
  request: GenerateRequest,
): boolean {
  const accepted = preview.suggestions
    .filter((item) => item.status === "accepted")
    .map((item) => item.id);
  return (
    preview.preview_id === request.preview_id &&
    preview.review_revision === request.review_revision &&
    preview.approved_objectives.length > 0 &&
    preview.suggestions.every((item) => item.status !== "pending") &&
    new Set(request.accepted_suggestion_ids).size ===
      request.accepted_suggestion_ids.length &&
    accepted.length === request.accepted_suggestion_ids.length &&
    accepted.every((id) => request.accepted_suggestion_ids.includes(id))
  );
}

export function GenerationPanel(props: Props) {
  return (
    <GenerationSession
      key={`${props.request.preview_id}:${props.request.review_revision}:${[...props.request.accepted_suggestion_ids].sort().join(",")}`}
      {...props}
    />
  );
}

function GenerationSession({ request, api, onOpenLesson }: Props) {
  const [key] = useState(() => operationKey(request));
  const [preview, setPreview] = useState<EnrichmentPreview | null>(null);
  const [posting, setPosting] = useState(false);
  const [checking, setChecking] = useState(false);
  const [uncertain, setUncertain] = useState(true);
  const [message, setMessage] = useState("");
  const [waiting, setWaiting] = useState(false);
  const [polling, setPolling] = useState(false);
  const [readyId, setReadyId] = useState<string | null>(null);
  const [online, setOnline] = useState(() => navigator.onLine);
  const post = useRef<AbortController | null>(null);
  const read = useRef<AbortController | null>(null);
  const feedback = useRef<HTMLParagraphElement>(null);
  const polls = useRef(0);
  const previewId = request.preview_id;
  const generating = posting || preview?.generation_status === "generating";
  useEffect(
    () => () => {
      post.current?.abort();
      read.current?.abort();
      post.current = null;
      read.current = null;
    },
    [],
  );
  useEffect(() => {
    if (message) feedback.current?.focus();
  }, [message]);

  const refresh = useCallback(
    async (automatic = false) => {
      if (read.current) return false;
      if (!automatic) polls.current = 0;
      const controller = new AbortController();
      read.current = controller;
      setChecking(true);
      try {
        const value = await api.getPreview(previewId, controller.signal);
        if (controller.signal.aborted) return false;
        if (
          value.preview_id !== previewId ||
          value.schema_version !== 1 ||
          !Array.isArray(value.suggestions) ||
          !Array.isArray(value.approved_objectives) ||
          !["idle", "generating", "ready", "failed"].includes(
            value.generation_status,
          ) ||
          (value.generation_status === "ready" &&
            (typeof value.last_lesson_bundle_id !== "string" ||
              !value.last_lesson_bundle_id.trim())) ||
          !Number.isFinite(Date.parse(value.expires_at))
        )
          throw new Error("Invalid preview");
        setPreview(value);
        setUncertain(false);
        setMessage("");
        setReadyId(
          value.generation_status === "ready"
            ? value.last_lesson_bundle_id
            : null,
        );
        setPolling(value.generation_status === "generating");
        return true;
      } catch (failure) {
        if (controller.signal.aborted) return false;
        setUncertain(true);
        setPolling(false);
        setMessage(
          failure instanceof GenerationApiError
            ? failure.message
            : "Não foi possível consultar o estado salvo. Nenhuma geração foi repetida.",
        );
        return false;
      } finally {
        if (!controller.signal.aborted) {
          read.current = null;
          setChecking(false);
        }
      }
    },
    [api, previewId],
  );

  useEffect(() => {
    void refresh();
  }, [refresh]);
  useEffect(() => {
    const reconnect = () => {
      setOnline(true);
      void refresh();
    };
    const disconnect = () => {
      read.current?.abort();
      read.current = null;
      setChecking(false);
      setOnline(false);
      setUncertain(true);
      setPolling(false);
    };
    const resume = () => {
      if (document.visibilityState === "visible" && navigator.onLine)
        reconnect();
    };
    window.addEventListener("online", reconnect);
    window.addEventListener("offline", disconnect);
    document.addEventListener("visibilitychange", resume);
    return () => {
      window.removeEventListener("online", reconnect);
      window.removeEventListener("offline", disconnect);
      document.removeEventListener("visibilitychange", resume);
    };
  }, [refresh]);
  useEffect(() => {
    if (!generating) {
      setWaiting(false);
      return;
    }
    const timer = window.setTimeout(() => setWaiting(true), 45000);
    return () => window.clearTimeout(timer);
  }, [generating]);
  useEffect(() => {
    if (!polling || posting) return;
    const timer = window.setInterval(() => {
      if (++polls.current > 40) {
        setPolling(false);
        setUncertain(true);
        setMessage(
          "A operação ainda não foi confirmada. Consulte o estado novamente.",
        );
      } else void refresh(true);
    }, 2000);
    return () => window.clearInterval(timer);
  }, [polling, posting, refresh]);

  async function generate() {
    if (
      post.current ||
      !preview ||
      !reviewed(preview, request) ||
      !online ||
      uncertain ||
      preview.generation_status === "generating"
    )
      return;
    const controller = new AbortController();
    post.current = controller;
    setPosting(true);
    setMessage("");
    setReadyId(null);
    try {
      const bundle = await api.generate(request, key, controller.signal);
      if (controller.signal.aborted) return;
      if (
        bundle.preview_id !== request.preview_id ||
        bundle.review_revision !== request.review_revision ||
        bundle.project_id !== preview.project_id ||
        typeof bundle.lesson_bundle_id !== "string" ||
        !bundle.lesson_bundle_id.trim()
      )
        throw new Error("Invalid result");
      const reconciled = await refresh();
      if (controller.signal.aborted) return;
      setReadyId(bundle.lesson_bundle_id);
      setUncertain(!reconciled);
      setPolling(false);
      setMessage(
        reconciled
          ? "Aula validada e salva. Você pode abrir o resultado."
          : "Aula salva. Consulte o estado para atualizar o prazo de disponibilidade.",
      );
    } catch (failure) {
      if (controller.signal.aborted) return;
      setUncertain(true);
      setPolling(false);
      setMessage(
        failure instanceof GenerationApiError
          ? failure.message
          : "Não foi possível confirmar a geração. Consulte o estado antes de repetir.",
      );
    } finally {
      if (!controller.signal.aborted) {
        post.current = null;
        setPosting(false);
      }
    }
  }

  const validReview = preview ? reviewed(preview, request) : false;
  const serverGenerating = preview?.generation_status === "generating";
  const previousId =
    !readyId &&
    typeof preview?.last_lesson_bundle_id === "string" &&
    preview.last_lesson_bundle_id.trim()
      ? preview.last_lesson_bundle_id
      : null;
  const canGenerate =
    validReview &&
    online &&
    !uncertain &&
    !posting &&
    !checking &&
    !serverGenerating &&
    !readyId &&
    preview !== null &&
    Date.parse(preview.expires_at) > Date.now();
  return (
    <section className="generation-panel" aria-label="Geração da aula">
      <p className="generation-eyebrow">MATILDA STUDIO · GERAÇÃO</p>
      <h2>Gerar a aula revisada</h2>
      {!online && (
        <p role="status">
          Sem conexão. Sua revisão permanece salva. Ao reconectar, consultaremos
          o estado antes de uma nova tentativa.
        </p>
      )}
      <p>
        A geração usa somente suas decisões e objetivos aprovados. Revise
        integralmente o material antes de usá-lo em aula.
      </p>
      {preview && !validReview && (
        <p role="alert">
          A revisão não corresponde à solicitação ou ainda contém pendências.
          Volte à revisão.
        </p>
      )}
      {posting || serverGenerating ? (
        <p role="status">
          {waiting
            ? "A geração está levando mais que a meta de 45 segundos. Aguarde; nenhuma nova operação foi iniciada."
            : "Geração em andamento. Aguardando um resultado validado."}
        </p>
      ) : null}
      {preview?.last_error && !message && (
        <p role="alert">{generationMessage(preview.last_error.code)}</p>
      )}
      {readyId && validReview && (
        <p role="status">Aula pronta para consulta.</p>
      )}
      {preview && !uncertain && (
        <p>
          Disponível até{" "}
          <time dateTime={preview.expires_at}>
            {new Intl.DateTimeFormat("pt-BR", {
              dateStyle: "short",
              timeStyle: "short",
            }).format(new Date(preview.expires_at))}
          </time>
          . Consultar não renova o prazo.
        </p>
      )}
      <div className="generation-actions">
        <button disabled={!canGenerate} onClick={() => void generate()}>
          Gerar minha aula
        </button>
        <button disabled={checking || !online} onClick={() => void refresh()}>
          {checking ? "Consultando…" : "Consultar estado salvo"}
        </button>
        <button
          disabled={!readyId || !validReview || posting}
          onClick={() => {
            if (readyId) onOpenLesson(readyId);
          }}
        >
          Abrir aula existente
        </button>
        {previousId && (
          <button
            disabled={posting || !online}
            onClick={() => onOpenLesson(previousId)}
          >
            Abrir aula anterior
          </button>
        )}
      </div>
      {previousId && (
        <p>
          A aula anterior conserva as decisões da revisão com que foi gerada.
        </p>
      )}
      {uncertain && !posting && (
        <p>
          Consulte o estado salvo antes de tentar novamente. Uma nova tentativa
          explícita conserva a chave desta operação.
        </p>
      )}
      {message && (
        <p ref={feedback} tabIndex={-1} role={readyId ? "status" : "alert"}>
          {message}
        </p>
      )}
    </section>
  );
}

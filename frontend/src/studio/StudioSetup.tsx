import type { FormEvent } from "react";
import type { PreviewRequest } from "../types/studio";

export const initialSetup: PreviewRequest = {
  title: "",
  subject: "Ciências",
  education_level: "Ensino Médio",
  duration_minutes: 50,
  objectives: [],
  concepts: [],
  material_text: "",
};

export function StudioSetup({
  value,
  onChange,
  onSubmit,
  busy,
}: {
  value: PreviewRequest;
  onChange(value: PreviewRequest): void;
  onSubmit(event: FormEvent): void;
  busy: boolean;
}) {
  const update = (patch: Partial<PreviewRequest>) =>
    onChange({ ...value, ...patch });
  return (
    <form
      className="studio-setup"
      onSubmit={onSubmit}
      aria-label="Preparação da prévia"
    >
      <span className="eyebrow">MATILDA STUDIO · CADERNO DE AULA</span>
      <h1>Preparar aula no Studio</h1>
      <p>
        Parta do seu material. A prévia conecta propostas pedagógicas a
        contribuições documentadas.
      </p>
      <fieldset disabled={busy}>
        <legend>01 · Configuração da aula</legend>
        {value.analysis_id && (
          <div className="studio-notice">
            <p>
              A investigação selecionada será reutilizada com suas fontes e
              participantes. Confirme a configuração antes de criar a prévia.
            </p>
            <output aria-label="Investigação de origem">
              {value.analysis_id}
            </output>
            <button
              type="button"
              onClick={() => update({ analysis_id: null, project_id: null })}
            >
              Remover investigação de origem
            </button>
          </div>
        )}
        <label>
          Título da aula
          <input
            name="title"
            autoComplete="off"
            required
            maxLength={160}
            value={value.title}
            onChange={(e) => update({ title: e.target.value })}
          />
        </label>
        <div className="studio-fields">
          <label>
            Disciplina
            <input
              name="subject"
              autoComplete="off"
              required
              maxLength={80}
              value={value.subject}
              onChange={(e) => update({ subject: e.target.value })}
            />
          </label>
          <label>
            Nível de ensino
            <input
              name="education_level"
              autoComplete="off"
              required
              maxLength={80}
              value={value.education_level}
              onChange={(e) => update({ education_level: e.target.value })}
            />
          </label>
          <label>
            Duração (minutos)
            <input
              name="duration_minutes"
              type="number"
              required
              min={10}
              max={120}
              step={1}
              value={value.duration_minutes}
              onChange={(e) =>
                update({ duration_minutes: Number(e.target.value) })
              }
            />
          </label>
        </div>
      </fieldset>
      <fieldset disabled={busy}>
        <legend>02 · Material e origem científica</legend>
        <p>
          Use um DOI, o texto da sua aula ou uma lista de conceitos. A
          investigação vinculada também pode ser usada como origem.
        </p>
        <label>
          DOI do artigo (opcional)
          <input
            name="doi"
            autoComplete="off"
            spellCheck={false}
            maxLength={300}
            value={value.doi || ""}
            onChange={(event) =>
              update({
                doi: event.target.value || null,
                analysis_id: null,
                project_id: null,
              })
            }
          />
        </label>
        <label>
          Texto original
          <textarea
            name="material_text"
            rows={9}
            maxLength={20000}
            value={value.material_text}
            onChange={(e) => update({ material_text: e.target.value })}
            aria-describedby="material-help"
          />
        </label>
        <small id="material-help">
          Até 20.000 caracteres. Texto e conceitos são preservados separadamente
          da IA.
        </small>
        <label>
          Conceitos (um por linha)
          <textarea
            name="concepts"
            rows={3}
            value={(value.concepts || []).join("\n")}
            onChange={(e) => update({ concepts: e.target.value.split("\n") })}
          />
        </label>
        <small>
          Até 20 conceitos de 100 caracteres. Informe texto ou conceitos; por
          exemplo, CRISPR-Cas9.
        </small>
      </fieldset>
      <fieldset disabled={busy}>
        <legend>03 · Intenção pedagógica</legend>
        <label>
          Objetivos (um por linha, opcional)
          <textarea
            name="objectives"
            rows={3}
            value={(value.objectives || []).join("\n")}
            onChange={(e) => update({ objectives: e.target.value.split("\n") })}
          />
        </label>
        <small>
          Até 10 objetivos de 300 caracteres. Sugestões da IA não substituem
          seus objetivos.
        </small>
      </fieldset>
      <p className="studio-notice">
        Ao criar a prévia, seu material será enviado ao Gemini com a
        configuração da aula e o conjunto científico autorizado. Não inclua
        dados pessoais de alunos ou material sem autorização. A retenção é de 7
        dias após uma ação docente válida; consultar não renova esse prazo. A
        retomada depende deste navegador e do cookie da sessão.
      </p>
      <button type="submit" className="primary-button" disabled={busy}>
        {busy ? "Preparando prévia…" : "Criar prévia"}
      </button>
    </form>
  );
}

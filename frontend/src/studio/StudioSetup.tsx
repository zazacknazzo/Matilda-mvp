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
      <h1>Preparar aula no Studio</h1>
      <p>
        Parta do seu material. A prévia conecta propostas pedagógicas a
        contribuições documentadas.
      </p>
      <fieldset disabled={busy}>
        <legend>Configuração da aula</legend>
        <label>
          Título da aula
          <input
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
              required
              maxLength={80}
              value={value.subject}
              onChange={(e) => update({ subject: e.target.value })}
            />
          </label>
          <label>
            Nível de ensino
            <input
              required
              maxLength={80}
              value={value.education_level}
              onChange={(e) => update({ education_level: e.target.value })}
            />
          </label>
          <label>
            Duração (minutos)
            <input
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
        <label>
          Texto original
          <textarea
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
            rows={3}
            value={(value.concepts || []).join("\n")}
            onChange={(e) => update({ concepts: e.target.value.split("\n") })}
          />
        </label>
        <small>
          Até 20 conceitos de 100 caracteres. Informe texto ou conceitos; por
          exemplo, CRISPR-Cas9.
        </small>
        <label>
          Objetivos (um por linha, opcional)
          <textarea
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
        Criar prévia
      </button>
    </form>
  );
}

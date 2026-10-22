import { test, expect, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import type { EnrichmentPreview, ReviewRequest } from "../../src/types/studio";

function example(name = "pending-preview"): EnrichmentPreview {
  return JSON.parse(
    readFileSync(
      new URL(
        `../../../tests/fixtures/studio/api/${name}.json`,
        import.meta.url,
      ),
      "utf8",
    ),
  );
}

async function mockApi(page: Page, initial = example(), failure = 0) {
  let saved = structuredClone(initial);
  const requests: ReviewRequest[] = [];
  let fail = failure;
  let gets = 0;
  await page.route("**/api/studio/previews/**", async (route) => {
    if (route.request().method() === "GET") {
      gets++;
      const id = decodeURIComponent(
        new URL(route.request().url()).pathname.split("/").at(-1)!,
      );
      return route.fulfill({ json: { ...saved, preview_id: id } });
    }
    const body: ReviewRequest = route.request().postDataJSON();
    requests.push(body);
    if (fail)
      return route.fulfill({
        status: fail,
        json: {
          detail: "RAW_SECRET_MATERIAL",
          code: fail === 409 ? "review_conflict" : "invalid_input",
          retryable: false,
        },
      });
    // Test-only HTTP double, not a server authorization implementation.
    saved = structuredClone(saved);
    for (const decision of body.decisions) {
      const item = saved.suggestions.find(
        (item) => item.id === decision.suggestion_id,
      );
      if (!item) throw new Error("Unexpected suggestion ID");
      item.status = decision.status;
      item.suggested_content =
        decision.suggested_content ?? item.suggested_content;
      item.pedagogical_rationale =
        decision.pedagogical_rationale ?? item.pedagogical_rationale;
    }
    saved.approved_objectives = body.approved_objectives;
    saved.review_revision++;
    saved.expires_at = "2026-10-29T12:10:00Z";
    saved.project.expires_at = saved.expires_at;
    saved.project.last_teacher_activity_at = "2026-10-22T12:10:00Z";
    saved.project.status = saved.suggestions.some(
      (item) => item.status === "pending",
    )
      ? "preview_ready"
      : "reviewed";
    await route.fulfill({ json: saved });
  });
  return {
    requests,
    saved: () => saved,
    setFailure: (value: number) => {
      fail = value;
    },
    gets: () => gets,
  };
}

async function open(page: Page) {
  await page.clock.setFixedTime(new Date("2026-10-21T15:00:00Z"));
  await page.goto("/");
  await expect(
    page.getByRole("main", { name: "Revisão docente" }),
  ).toBeVisible();
}
const cards = (page: Page) => page.getByRole("article");
const save = (page: Page) =>
  page.getByRole("button", { name: "Salvar revisão", exact: true });
const advance = (page: Page) =>
  page.getByRole("button", { name: "Continuar para geração" });
async function approve(page: Page) {
  await page
    .getByRole("checkbox", { name: "Revisei e aprovo estes objetivos" })
    .check();
}
async function saveAndWait(page: Page) {
  await save(page).click();
  await expect(page.getByRole("status")).toContainText("Revisão salva.");
}

test("aceitar, rejeitar, editar pedagogia e restaurar a resposta HTTP na retomada", async ({
  page,
}) => {
  const mock = await mockApi(page);
  await open(page);
  await expect(advance(page)).toBeDisabled();
  await cards(page)
    .nth(0)
    .getByRole("radio", { name: "Aceitar", exact: true })
    .check();
  await cards(page)
    .nth(1)
    .getByRole("radio", { name: "Rejeitar", exact: true })
    .check();
  await cards(page)
    .nth(0)
    .getByLabel("Proposta pedagógica")
    .fill("Comparar o mecanismo em grupos.");
  await cards(page)
    .nth(0)
    .getByLabel("Justificativa pedagógica")
    .fill("Relacionar a explicação ao objetivo da turma.");
  await approve(page);
  await expect(advance(page)).toBeDisabled();
  await saveAndWait(page);
  expect(mock.requests).toHaveLength(1);
  expect(mock.requests[0].review_revision).toBe(0);
  expect(
    new Set(mock.requests[0].decisions.map((item) => item.suggestion_id)).size,
  ).toBe(2);
  for (const decision of mock.requests[0].decisions)
    expect(Object.keys(decision).sort()).toEqual([
      "pedagogical_rationale",
      "status",
      "suggested_content",
      "suggestion_id",
    ]);
  await expect(
    page.locator('time[datetime="2026-10-29T12:10:00Z"]'),
  ).toBeVisible();
  await expect(advance(page)).toBeEnabled();
  await advance(page).click();
  const request = page.getByLabel("Pedido de geração confirmado");
  await expect(request).toContainText("suggestion-1");
  await expect(request).not.toContainText("suggestion-2");
  await page.reload();
  await expect(
    cards(page).nth(0).getByLabel("Proposta pedagógica"),
  ).toHaveValue("Comparar o mecanismo em grupos.");
  await expect(
    cards(page).nth(0).getByRole("radio", { name: "Aceitar", exact: true }),
  ).toBeChecked();
  await expect(
    cards(page).nth(1).getByRole("radio", { name: "Rejeitar", exact: true }),
  ).toBeChecked();
  await expect(advance(page)).toBeEnabled();
});

test("permite salvar revisão parcial mas pendências impedem avanço", async ({
  page,
}) => {
  const mock = await mockApi(page);
  await open(page);
  await cards(page)
    .first()
    .getByRole("radio", { name: "Aceitar", exact: true })
    .check();
  await approve(page);
  await saveAndWait(page);
  expect(mock.requests[0].decisions).toHaveLength(1);
  await expect(advance(page)).toBeDisabled();
  await expect(
    page.getByText("1 sugestão(ões) pendente(s).", { exact: false }),
  ).toBeVisible();
});

test("rejeitar todas e zero aceitas continuam válidos", async ({ page }) => {
  await mockApi(page);
  await open(page);
  for (const card of await cards(page).all())
    await card.getByRole("radio", { name: "Rejeitar", exact: true }).check();
  await approve(page);
  await saveAndWait(page);
  await advance(page).click();
  await expect(page.getByLabel("Pedido de geração confirmado")).toContainText(
    '"accepted_suggestion_ids": []',
  );
});

test("sem cobertura e objetivos sugeridos exigem aprovação explícita", async ({
  page,
}) => {
  const fixture = example("no-coverage-preview");
  fixture.review_revision = 0;
  fixture.approved_objectives = [];
  fixture.project.status = "preview_ready";
  await mockApi(page, fixture);
  await open(page);
  await expect(
    page.getByText("Sem sugestões científicas nesta prévia.", { exact: false }),
  ).toBeVisible();
  await expect(save(page)).toBeDisabled();
  await expect(advance(page)).toBeDisabled();
  await approve(page);
  await saveAndWait(page);
  await expect(advance(page)).toBeEnabled();
});

test("objetivos vazios, excessivos ou longos e edições vazias não podem ser salvos", async ({
  page,
}) => {
  await mockApi(page);
  await open(page);
  const objectives = page.getByLabel(
    "Objetivos de aprendizagem · um por linha",
  );
  for (const value of [
    "",
    "x".repeat(301),
    Array.from({ length: 11 }, (_, i) => `Objetivo ${i}`).join("\n"),
  ]) {
    await objectives.fill(value);
    await approve(page);
    await expect(save(page)).toBeDisabled();
  }
  await objectives.fill("Objetivo conferido");
  await expect(page.getByRole("checkbox")).not.toBeChecked();
  await approve(page);
  await expect(save(page)).toBeEnabled();
  await cards(page).first().getByLabel("Proposta pedagógica").fill(" ");
  await expect(save(page)).toBeDisabled();
});

for (const status of [409, 422, 503])
  test(`HTTP ${status} conserva decisões, não vaza corpo e exige consulta`, async ({
    page,
  }) => {
    const mock = await mockApi(page, example(), status);
    await open(page);
    await cards(page)
      .first()
      .getByRole("radio", { name: "Aceitar", exact: true })
      .check();
    await cards(page)
      .first()
      .getByLabel("Proposta pedagógica")
      .fill("Edição local que não pode sumir.");
    await approve(page);
    await save(page).click();
    await expect(page.getByRole("alert")).toBeVisible();
    await expect(page.getByRole("alert")).toBeFocused();
    await expect(page.locator("body")).not.toContainText("RAW_SECRET_MATERIAL");
    await expect(
      cards(page).first().getByLabel("Proposta pedagógica"),
    ).toHaveValue("Edição local que não pode sumir.");
    await expect(advance(page)).toBeDisabled();
    await expect(save(page)).toBeDisabled();
    await page.getByRole("button", { name: "Consultar versão salva" }).click();
    await page.getByRole("button", { name: "Cancelar", exact: true }).click();
    await expect(
      cards(page).first().getByLabel("Proposta pedagógica"),
    ).toHaveValue("Edição local que não pode sumir.");
    mock.setFailure(0);
    await page.getByRole("button", { name: "Consultar versão salva" }).click();
    await page.getByRole("button", { name: "Confirmar", exact: true }).click();
    await expect(page.getByRole("status")).toContainText(
      "Versão salva carregada.",
    );
    await expect(
      cards(page).first().getByRole("radio", { name: "Aceitar", exact: true }),
    ).not.toBeChecked();
  });

test("HTML é texto literal, fontes inseguras não são links e ciência não é editável", async ({
  page,
}) => {
  const fixture = example();
  fixture.source_documents[0].content =
    '<img src=x onerror="window.pwned=true">';
  fixture.suggestions[0].historical_claim =
    "<script>window.pwned=true</script>";
  fixture.evidence_references[0].source_url = "javascript:alert(1)";
  fixture.evidence_references[1].source_url = "https://user:secret@example.com";
  await mockApi(page, fixture);
  await open(page);
  await expect(page.getByRole("main").locator("script, img")).toHaveCount(0);
  await expect(
    page.getByRole("main").locator('a:not([href^="#"])'),
  ).toHaveCount(0);
  await expect(
    page.getByText("<script>window.pwned=true</script>", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText(/Martin Jínek/)).toBeVisible();
  await expect(page.getByRole("textbox")).toHaveCount(5);
});

test("alterar entrada invalida a revisão e trocar preview descarta estado antigo", async ({
  page,
}) => {
  await mockApi(page, example("crispr-preview"));
  await open(page);
  await expect(advance(page)).toBeEnabled();
  await page
    .getByRole("button", { name: "Alterar material, origem ou configuração" })
    .click();
  await page.getByRole("button", { name: "Confirmar", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("invalidada");
  await expect(advance(page)).toBeDisabled();
  await page.getByLabel("Prévia de exemplo").selectOption("preview-other");
  await expect(advance(page)).toBeEnabled();
  await advance(page).click();
  await expect(page.getByLabel("Pedido de geração confirmado")).toContainText(
    "preview-other",
  );
});

test("expiração e geração em andamento bloqueiam gravação e avanço", async ({
  page,
}) => {
  const fixture = example("crispr-preview");
  fixture.generation_status = "generating";
  fixture.project.status = "generating";
  const mock = await mockApi(page, fixture);
  await open(page);
  await expect(
    page.getByText("Geração em andamento.", { exact: false }),
  ).toBeVisible();
  await expect(
    cards(page).first().getByLabel("Proposta pedagógica"),
  ).toBeDisabled();
  await expect(advance(page)).toBeDisabled();
  expect(mock.requests).toHaveLength(0);
  await page.unrouteAll();
  fixture.generation_status = "idle";
  fixture.project.status = "reviewed";
  fixture.expires_at = "2020-01-01T00:00:00Z";
  fixture.project.expires_at = fixture.expires_at;
  await mockApi(page, fixture);
  await page.reload();
  await expect(page.getByRole("alert")).toContainText("expirou");
  await expect(advance(page)).toBeDisabled();
});

test("teclado, foco após salvar e layout mobile sem rolagem horizontal", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await mockApi(page);
  await open(page);
  for (const card of await cards(page).all()) {
    const radio = card.getByRole("radio", { name: "Rejeitar", exact: true });
    await radio.focus();
    await page.keyboard.press("Space");
  }
  await page.getByRole("checkbox").focus();
  await page.keyboard.press("Space");
  await save(page).focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("status")).toBeFocused();
  await expect(advance(page)).toBeEnabled();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});

test("GET indisponível oferece retomada explícita sem sucesso fictício", async ({
  page,
}) => {
  await page.route("**/api/studio/previews/**", (route) =>
    route.fulfill({
      status: 404,
      json: { code: "not_found", detail: "Indisponível", retryable: false },
    }),
  );
  await page.goto("/");
  await expect(page.getByRole("alert")).toContainText("indisponível");
  await expect(page.getByRole("article")).toHaveCount(0);
  await page.unrouteAll();
  await mockApi(page);
  await page
    .getByRole("button", { name: "Tentar consultar novamente" })
    .click();
  await expect(cards(page)).toHaveCount(2);
});

test("resposta com IDs duplicados não é apresentada como revisão válida", async ({
  page,
}) => {
  const fixture = example();
  fixture.suggestions[1].id = fixture.suggestions[0].id;
  await mockApi(page, fixture);
  await page.goto("/");
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(cards(page)).toHaveCount(0);
});

test("edição de sugestão pendente não é descartada silenciosamente por uma gravação parcial", async ({
  page,
}) => {
  const mock = await mockApi(page);
  await open(page);
  await approve(page);
  await cards(page)
    .first()
    .getByLabel("Proposta pedagógica")
    .fill("Preservar esta edição ainda pendente.");
  await expect(save(page)).toBeDisabled();
  await expect(page.getByRole("status")).toContainText("Aceite ou rejeite");
  await cards(page)
    .first()
    .getByRole("radio", { name: "Aceitar", exact: true })
    .check();
  await saveAndWait(page);
  expect(mock.requests[0].decisions[0].suggested_content).toBe(
    "Preservar esta edição ainda pendente.",
  );
  await expect(
    cards(page).first().getByLabel("Proposta pedagógica"),
  ).toHaveValue("Preservar esta edição ainda pendente.");
});

test("desconexão na gravação mantém as edições e não repete POST automaticamente", async ({
  page,
}) => {
  await mockApi(page);
  await open(page);
  let posts = 0;
  await page.route("**/api/studio/previews/*/review", (route) => {
    posts++;
    return route.abort("connectionreset");
  });
  await cards(page)
    .first()
    .getByRole("radio", { name: "Aceitar", exact: true })
    .check();
  await approve(page);
  await save(page).click();
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(
    cards(page).first().getByRole("radio", { name: "Aceitar", exact: true }),
  ).toBeChecked();
  await expect(save(page)).toBeDisabled();
  await expect(advance(page)).toBeDisabled();
  expect(posts).toBe(1);
});

test("POST com resposta inconsistente não vira sucesso nem libera geração", async ({
  page,
}) => {
  await mockApi(page);
  await open(page);
  await page.route("**/api/studio/previews/*/review", (route) =>
    route.fulfill({ json: example() }),
  );
  await approve(page);
  await save(page).click();
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(advance(page)).toBeDisabled();
  await expect(page.getByText("Revisão salva.", { exact: false })).toHaveCount(
    0,
  );
});

test("gravação em andamento bloqueia reenvio e resposta antiga não troca a nova prévia", async ({
  page,
}) => {
  await mockApi(page);
  await open(page);
  let release = () => {};
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/api/studio/previews/*/review", async (route) => {
    await gate;
    const fixture = example("crispr-preview");
    fixture.project.title = "Resposta da prévia anterior";
    await route.fulfill({ json: fixture });
  });
  await approve(page);
  await save(page).click();
  await expect(page.getByRole("button", { name: "Aguarde…" })).toBeDisabled();
  await page.getByLabel("Prévia de exemplo").selectOption("preview-other");
  await expect(cards(page)).toHaveCount(2);
  release();
  await expect(
    page.getByRole("heading", { name: "Resposta da prévia anterior" }),
  ).toHaveCount(0);
  await expect(advance(page)).toBeDisabled();
});

test("harness manual serve HTTP de exemplo e mantém aviso de simulação", async ({
  page,
}) => {
  await open(page);
  await expect(page.getByLabel("Ambiente de exemplos")).toContainText(
    "API simulada",
  );
  await cards(page)
    .first()
    .getByRole("radio", { name: "Aceitar", exact: true })
    .check();
  await cards(page)
    .nth(1)
    .getByRole("radio", { name: "Rejeitar", exact: true })
    .check();
  await approve(page);
  await saveAndWait(page);
  await page.screenshot({
    path: "../.runtime/t07-desktop.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: "../.runtime/t07-mobile.png", fullPage: true });
});

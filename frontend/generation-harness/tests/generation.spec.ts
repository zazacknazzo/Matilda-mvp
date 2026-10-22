import { test, expect, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import type { EnrichmentPreview } from "../../src/types/studio";

const generate = (page: Page) =>
  page.getByRole("button", { name: "Gerar minha aula", exact: true });
const refresh = (page: Page) =>
  page.getByRole("button", { name: "Consultar estado salvo", exact: true });
const openLesson = (page: Page) =>
  page.getByRole("button", { name: "Abrir aula existente", exact: true });
const panel = (page: Page) =>
  page.getByRole("region", { name: "Geração da aula" });

function reference(): EnrichmentPreview {
  return JSON.parse(
    readFileSync(
      new URL(
        "../../../tests/fixtures/studio/api/text-preview.json",
        import.meta.url,
      ),
      "utf8",
    ),
  );
}

test.beforeEach(async ({ request }) => {
  await request.post("http://127.0.0.1:8017/test/reset");
});

test("revisão de referência passa pelo orquestrador, validador e SQLite reais", async ({
  page,
}) => {
  const posts: string[] = [];
  page.on("request", (request) => {
    if (request.method() === "POST") posts.push(request.url());
  });
  await page.goto("/");
  await expect(page.getByLabel("Ambiente de exemplos")).toContainText(
    "GEMINI SIMULADO",
  );
  await expect(generate(page)).toBeEnabled();
  await generate(page).click();
  await expect(openLesson(page)).toBeEnabled();
  await expect(
    panel(page).getByText("Aula validada e salva.", { exact: false }),
  ).toBeVisible();
  await expect(panel(page).locator("time")).toHaveAttribute(
    "datetime",
    "2026-10-28T12:20:00+00:00",
  );
  await openLesson(page).click();
  await expect(page.getByLabel("Aula selecionada")).toContainText(
    "Resultado recebido:",
  );
  expect(posts).toHaveLength(1);
  await page.screenshot({
    path: "../.runtime/t09-desktop.png",
    fullPage: true,
  });
  await page.reload();
  await expect(openLesson(page)).toBeEnabled();
  await expect(generate(page)).toBeDisabled();
  expect(posts).toHaveLength(1);
});

for (const scenario of ["invalid", "timeout", "unauthorized"])
  test(`${scenario}: erro não inventa aula e permite reconciliar a revisão`, async ({
    page,
  }) => {
    await page.goto("/");
    await page
      .getByRole("combobox", { name: "Cenário", exact: true })
      .selectOption(scenario);
    await expect(generate(page)).toBeEnabled();
    await generate(page).click();
    await expect(panel(page).getByRole("alert")).toBeVisible();
    await expect(openLesson(page)).toBeDisabled();
    await expect(generate(page)).toBeDisabled();
    await refresh(page).click();
    await expect(generate(page)).toBeEnabled();
    await expect(panel(page).getByRole("alert")).toBeVisible();
  });

test("zero sugestões aceitas é válido e pendências impedem geração", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByRole("combobox", { name: "Cenário", exact: true })
    .selectOption("pending");
  await expect(panel(page).getByRole("alert")).toContainText("pendências");
  await expect(generate(page)).toBeDisabled();
  await page
    .getByRole("combobox", { name: "Cenário", exact: true })
    .selectOption("empty");
  await expect(generate(page)).toBeEnabled();
  await generate(page).click();
  await expect(openLesson(page)).toBeEnabled();
});

test("desconexão após salvar consulta resultado existente sem novo POST", async ({
  page,
}) => {
  await page.goto("/");
  await expect(generate(page)).toBeEnabled();
  let posts = 0;
  await page.route("**/api/studio/generate", async (route) => {
    posts++;
    const response = await route.fetch();
    expect(response.status()).toBe(201);
    await route.abort("connectionreset");
  });
  await generate(page).click();
  await expect(panel(page).getByRole("alert")).toBeVisible();
  await expect(generate(page)).toBeDisabled();
  await refresh(page).click();
  await expect(openLesson(page)).toBeEnabled();
  expect(posts).toBe(1);
});

test("nova tentativa explícita conserva a chave idempotente", async ({
  page,
}) => {
  await page.goto("/");
  await expect(generate(page)).toBeEnabled();
  const keys: string[] = [];
  await page.route("**/api/studio/generate", (route) => {
    keys.push(route.request().headers()["idempotency-key"]);
    return route.fulfill({
      status: 503,
      json: {
        code: "provider_unavailable",
        detail: "RAW_SECRET",
        retryable: true,
      },
    });
  });
  await generate(page).click();
  await expect(panel(page).getByRole("alert")).toBeVisible();
  await expect(page.locator("body")).not.toContainText("RAW_SECRET");
  await refresh(page).click();
  await expect(generate(page)).toBeEnabled();
  await generate(page).click();
  await expect(panel(page).getByRole("alert")).toBeVisible();
  expect(keys).toHaveLength(2);
  expect(keys[0]).toBe(keys[1]);
  await page.reload();
  await expect(generate(page)).toBeEnabled();
  await generate(page).click();
  await expect(panel(page).getByRole("alert")).toBeVisible();
  expect(keys[2]).toBe(keys[0]);
});

test("meta de 45 s não aborta; cliente encerra espera em 85 s sem repetir", async ({
  page,
}) => {
  await page.clock.install({ time: new Date("2026-10-21T15:00:00Z") });
  await page.goto("/");
  await expect(generate(page)).toBeEnabled();
  let posts = 0;
  let release = () => {};
  const held = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/api/studio/generate", async (route) => {
    posts++;
    await held;
    await route.abort();
  });
  await generate(page).click();
  await page.clock.fastForward(45001);
  await expect(panel(page).getByRole("status")).toContainText(
    "meta de 45 segundos",
  );
  await expect(generate(page)).toBeDisabled();
  await expect(panel(page).getByRole("alert")).toHaveCount(0);
  await page.clock.fastForward(40001);
  await expect(panel(page).getByRole("alert")).toContainText("prazo");
  expect(posts).toBe(1);
  release();
});

test("estado generating é consultado por GET até pronto, sem POST automático", async ({
  page,
}) => {
  const value = reference();
  value.preview_id = "preview-success";
  value.project.status = "generating";
  value.generation_status = "generating";
  let reads = 0;
  const posts: string[] = [];
  await page.route("**/api/studio/previews/*", (route) => {
    reads++;
    const current = structuredClone(value);
    if (reads >= 3) {
      current.project.status = "ready";
      current.generation_status = "ready";
      current.last_lesson_bundle_id = "existing-lesson";
    }
    return route.fulfill({ json: current });
  });
  page.on("request", (request) => {
    if (request.method() === "POST") posts.push(request.url());
  });
  await page.goto("/");
  await expect(generate(page)).toBeDisabled();
  await expect(openLesson(page)).toBeEnabled({ timeout: 10000 });
  await openLesson(page).click();
  await expect(page.getByLabel("Aula selecionada")).toContainText(
    "existing-lesson",
  );
  expect(posts).toHaveLength(0);
});

test("resultado de revisão diferente e GET inválido não liberam aula fictícia", async ({
  page,
}) => {
  await page.goto("/");
  await expect(generate(page)).toBeEnabled();
  await page.route("**/api/studio/generate", (route) =>
    route.fulfill({
      json: {
        lesson_bundle_id: "foreign-lesson",
        project_id: "foreign",
        preview_id: "other",
        review_revision: 99,
      },
    }),
  );
  await generate(page).click();
  await expect(panel(page).getByRole("alert")).toBeVisible();
  await expect(openLesson(page)).toBeDisabled();
  await page.route("**/api/studio/previews/*", (route) =>
    route.fulfill({
      json: { preview_id: "preview-success", schema_version: 1 },
    }),
  );
  await refresh(page).click();
  await expect(panel(page).getByRole("alert")).toBeVisible();
  await expect(generate(page)).toBeDisabled();
});

test("teclado e mobile mantêm feedback e ações utilizáveis", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(generate(page)).toBeEnabled();
  await generate(page).focus();
  await page.keyboard.press("Enter");
  await expect(openLesson(page)).toBeEnabled();
  await expect(
    panel(page).getByText("Aula validada e salva.", { exact: false }),
  ).toBeFocused();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({ path: "../.runtime/t09-mobile.png", fullPage: true });
});

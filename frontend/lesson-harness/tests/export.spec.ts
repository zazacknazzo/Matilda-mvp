import { test, expect, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import type { LessonBundle } from "../../src/types/lesson";

function fixture(file = "crispr-50"): LessonBundle {
  return JSON.parse(
    readFileSync(
      new URL(
        `../../../tests/fixtures/studio/lessons/${file}.json`,
        import.meta.url,
      ),
      "utf8",
    ),
  );
}

async function setBundle(page: Page, bundle: LessonBundle) {
  await page.evaluate((value) => window.setLessonExample(value), bundle);
}

for (const [name, file] of [
  ["crispr", "crispr-50"],
  ["rna", "rna-50"],
  ["empty", "no-enrichment-50"],
]) {
  test(`${name}: download usa GET do mesmo bundle sem geração`, async ({
    page,
  }) => {
    const requests: string[] = [];
    page.on("request", (request) => {
      if (request.url().includes("/api/"))
        requests.push(request.method() + " " + request.url());
    });
    const bundle = fixture(file);
    await page.goto("/");
    await page
      .getByRole("combobox", { name: "Exemplo", exact: true })
      .selectOption(name);
    const downloadPromise = page.waitForEvent("download");
    await page
      .getByRole("button", { name: "Baixar Markdown", exact: true })
      .click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toMatch(
      /^matilda-aula-[a-f0-9]{24}\.md$/,
    );
    const text = readFileSync((await download.path())!, "utf8");
    expect(text).toContain("Objetivos de aprendizagem");
    expect(text).toContain("Notas do professor");
    expect(text).toContain("Critérios de avaliação");
    for (const reference of bundle.references) {
      expect(text).toContain(reference.source_url);
      for (const participant of reference.participants)
        expect(text.replace(/\\(.)/g, "$1")).toContain(participant);
    }
    expect(requests).toHaveLength(1);
    expect(requests[0]).toContain(
      `/api/studio/lessons/${bundle.lesson_bundle_id}/export?format=markdown`,
    );
    expect(requests[0]).toMatch(/^GET /);
    await expect(
      page.getByRole("region", { name: "Exportar aula" }).getByRole("status"),
    ).toContainText("Download de Markdown iniciado.");
    await expect(
      page.getByRole("region", { name: "Exportar aula" }).getByRole("status"),
    ).toBeFocused();
  });
}

test("falha e sessão indisponível mantêm a aula, sem download fictício ou corpo de erro", async ({
  page,
}) => {
  await page.goto("/");
  let downloads = 0;
  page.on("download", () => downloads++);
  for (const status of [404, 503]) {
    await page.route(
      "**/api/studio/lessons/*/export?format=markdown",
      (route) =>
        route.fulfill({
          status,
          json: { detail: "SECRET_RAW_BODY", code: "not_found" },
        }),
    );
    await page
      .getByRole("button", { name: "Baixar Markdown", exact: true })
      .click();
    await expect(page.getByRole("alert")).toBeVisible();
    await expect(page.getByRole("alert")).toBeFocused();
    await expect(page.locator("body")).not.toContainText("SECRET_RAW_BODY");
    await expect(
      page.getByRole("button", { name: "Apresentar aula ↗" }),
    ).toBeVisible();
    await page.unrouteAll();
  }
  expect(downloads).toBe(0);
  const download = page.waitForEvent("download");
  await page
    .getByRole("button", { name: "Baixar Markdown", exact: true })
    .click();
  await download;
});

test("resposta com tipo incorreto não é baixada; nome inseguro usa alternativa segura", async ({
  page,
}) => {
  await page.goto("/");
  await page.route("**/api/studio/lessons/*/export?format=markdown", (route) =>
    route.fulfill({
      contentType: "text/html",
      body: "<script>alert(1)</script>",
    }),
  );
  await page
    .getByRole("button", { name: "Baixar Markdown", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText(
    "não retornou um arquivo Markdown válido",
  );
  await page.unrouteAll();
  await page.route("**/api/studio/lessons/*/export?format=markdown", (route) =>
    route.fulfill({
      headers: {
        "content-type": "text/markdown; charset=utf-8",
        "content-disposition": 'attachment; filename="../../escape.html"',
      },
      body: "# Aula de teste\n",
    }),
  );
  const pending = page.waitForEvent("download");
  await page
    .getByRole("button", { name: "Baixar Markdown", exact: true })
    .click();
  expect((await pending).suggestedFilename()).toBe("matilda-aula.md");
});

test("teclado aciona impressão nativa do plano sem mudar slides ou chamar API", async ({
  page,
}) => {
  await page.goto("/");
  await page.evaluate(() => {
    window.print = () =>
      document.body.setAttribute("data-print-called", "true");
  });
  const requests: string[] = [];
  page.on("request", (request) => {
    if (request.url().includes("/api/")) requests.push(request.url());
  });
  const print = page.getByRole("button", {
    name: "Imprimir plano / salvar PDF",
  });
  await print.focus();
  await page.keyboard.press("Enter");
  await expect(page.locator("body")).toHaveAttribute(
    "data-print-called",
    "true",
  );
  await expect(page.getByRole("article", { name: /^Slide / })).toBeVisible();
  expect(requests).toHaveLength(0);
  await page.emulateMedia({ media: "print" });
  const plan = page.locator("body > .lesson-print-view");
  await expect(plan).toBeVisible();
  await expect(page.locator("#root")).toBeHidden();
  await expect(plan).toContainText("Notas do professor");
  await expect(plan).toContainText("Critérios de avaliação");
  await expect(plan.locator("button")).toHaveCount(0);
  await page.emulateMedia({ media: "screen" });
  await page.evaluate(() => window.dispatchEvent(new Event("afterprint")));
  await expect(print).toBeFocused();
});

for (const [name, file] of [
  ["crispr", "crispr-50"],
  ["rna", "rna-50"],
  ["empty", "no-enrichment-50"],
]) {
  test(`${name}: PDF A4 do plano tem texto e fontes completos`, async ({
    page,
  }) => {
    const bundle = fixture(file);
    await page.goto("/");
    await page
      .getByRole("combobox", { name: "Exemplo", exact: true })
      .selectOption(name);
    await expect(page.locator("body > .lesson-print-view")).toBeHidden();
    const pdf = await page.pdf({
      path: `../.runtime/t11-${name}.pdf`,
      preferCSSPageSize: true,
      printBackground: false,
    });
    expect(pdf.subarray(0, 5).toString()).toBe("%PDF-");
    await page.emulateMedia({ media: "print" });
    const plan = page.locator("body > .lesson-print-view");
    for (const slide of bundle.slides)
      if (slide.speaker_notes)
        await expect(plan).toContainText(slide.speaker_notes);
    for (const reference of bundle.references) {
      await expect(plan).toContainText(reference.claim_supported);
      for (const person of reference.participants)
        await expect(plan).toContainText(person);
    }
    await page.screenshot({
      path: `../.runtime/t11-${name}-print.png`,
      fullPage: true,
    });
  });
}

test("plano longo com HTML literal não corta notas nem cria elementos executáveis", async ({
  page,
}) => {
  await page.goto("/");
  const bundle = fixture();
  bundle.slides[0].speaker_notes =
    "<img src=x onerror=alert(1)> " +
    "Notas extensas para conferir a quebra de página. ".repeat(25) +
    "FIM_DAS_NOTAS";
  await setBundle(page, bundle);
  await page.emulateMedia({ media: "print" });
  const plan = page.locator("body > .lesson-print-view");
  await expect(plan.locator("img,script")).toHaveCount(0);
  await expect(plan).toContainText(bundle.slides[0].speaker_notes);
  expect(
    await plan
      .locator(".lesson-notes")
      .first()
      .evaluate((element) => getComputedStyle(element).overflow),
  ).toBe("visible");
  await page.pdf({ path: "../.runtime/t11-long.pdf", preferCSSPageSize: true });
});

test("mobile preserva botões, download e texto sem rolagem horizontal", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page
    .getByRole("button", { name: "Plano de aula", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Imprimir plano / salvar PDF" }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({ path: "../.runtime/t11-mobile.png", fullPage: true });
});

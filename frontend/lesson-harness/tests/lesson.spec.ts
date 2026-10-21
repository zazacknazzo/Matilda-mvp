import { test, expect, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import type { LessonBundle } from "../../src/types/lesson";

function example(name = "crispr-50"): LessonBundle {
  return JSON.parse(
    readFileSync(
      new URL(
        `../../../tests/fixtures/studio/lessons/${name}.json`,
        import.meta.url,
      ),
      "utf-8",
    ),
  );
}
async function replaceExample(page: Page, bundle: LessonBundle) {
  await page.evaluate((value) => window.setLessonExample(value), bundle);
}

for (const [name, file] of [
  ["crispr", "crispr-50"],
  ["rna", "rna-50"],
]) {
  test(`${name}: seis layouts, fontes, plano e tempos do mesmo bundle`, async ({
    page,
  }) => {
    const errors: string[] = [],
      requests: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    page.on("request", (request) => {
      if (request.url().includes("/api/")) requests.push(request.url());
    });
    const bundle = example(file);
    await page.goto("/");
    await page
      .getByRole("combobox", { name: "Exemplo", exact: true })
      .selectOption(name);
    await expect(page.getByLabel("Ambiente de exemplos")).toContainText(
      "não foi gerada por IA",
    );
    const slide = page.getByRole("article", { name: /^Slide / });
    for (let i = 0; i < bundle.slides.length; i++) {
      const current = bundle.slides[i];
      await expect(slide).toHaveAttribute("data-layout", current.layout);
      await expect(
        slide.getByRole("heading", { name: current.title, exact: true }),
      ).toBeVisible();
      const size = await slide.boundingBox();
      expect(size!.width / size!.height).toBeCloseTo(16 / 9, 1);
      for (const id of current.evidence_ids) {
        const ref = bundle.references.find((item) => item.id === id)!;
        await expect(slide).toContainText(ref.claim_supported);
        await expect(slide.getByRole("link")).toHaveAttribute(
          "href",
          ref.source_url,
        );
        for (const person of ref.participants)
          await expect(slide).toContainText(person);
        for (const limit of ref.limitations)
          await expect(slide).toContainText(limit);
      }
      if (i < bundle.slides.length - 1)
        await page
          .getByRole("button", { name: "Próximo slide", exact: true })
          .click();
    }
    await expect(
      page.getByRole("button", { name: "Próximo slide", exact: true }),
    ).toBeDisabled();
    await page
      .getByRole("button", { name: "Plano de aula", exact: true })
      .click();
    const plan = page.getByRole("article", { name: "Plano de aula" });
    await expect(plan).toContainText(bundle.metadata.title);
    await expect(plan).toContainText("50 MINUTOS");
    for (const text of [
      ...bundle.metadata.learning_objectives,
      ...bundle.metadata.materials,
      ...bundle.metadata.prior_knowledge,
      ...bundle.limitations,
    ])
      await expect(plan).toContainText(text);
    for (const item of bundle.slides)
      await expect(plan).toContainText(item.speaker_notes);
    for (const activity of bundle.activities) {
      await expect(plan).toContainText(activity.prompt);
      await expect(plan).toContainText(activity.teacher_guidance);
      for (const criterion of activity.assessment_criteria)
        await expect(plan).toContainText(criterion);
    }
    await expect(plan).toContainText("0–15 min");
    await expect(plan).toContainText("15–35 min");
    await expect(plan).toContainText("35–50 min");
    expect(errors).toEqual([]);
    expect(requests).toEqual([]);
  });
}

test("teclado, limites, apresentação sem notas, foco e alternativa à tela cheia", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    page.getByRole("button", { name: "Slide anterior", exact: true }),
  ).toBeDisabled();
  const preview = page.getByRole("region", { name: "Prévia dos slides" });
  await preview.focus();
  await page.keyboard.press("End");
  await expect(page.getByRole("status")).toHaveText("Slide 6 de 6");
  await page.keyboard.press("ArrowRight");
  await expect(page.getByRole("status")).toHaveText("Slide 6 de 6");
  await page.keyboard.press("Home");
  await page.keyboard.press("ArrowRight");
  await expect(page.getByRole("status")).toHaveText("Slide 2 de 6");
  await page.evaluate(() => {
    Element.prototype.requestFullscreen = () =>
      Promise.reject(new Error("not supported"));
  });
  const launch = page.getByRole("button", { name: "Apresentar aula" });
  await launch.click();
  const presentation = page.getByRole("dialog", {
    name: "Apresentação da aula",
  });
  await expect(presentation).toBeFocused();
  await expect(presentation.locator(".lesson-notes")).toHaveCount(0);
  await expect(page.locator("main")).toHaveAttribute("inert", "");
  await expect(presentation).not.toContainText(
    example().slides[0].speaker_notes,
  );
  await page.keyboard.press("ArrowRight");
  await expect(presentation.getByRole("status")).toHaveText("Slide 3 de 6");
  await presentation
    .getByRole("button", { name: "Tela cheia", exact: true })
    .click();
  await expect(presentation).toContainText("Tela cheia indisponível");
  await presentation
    .getByRole("button", { name: /Sair da apresentação/ })
    .focus();
  await page.keyboard.press("Tab");
  expect(
    await presentation.evaluate((node) =>
      node.contains(document.activeElement),
    ),
  ).toBe(true);
  await page.keyboard.press("Escape");
  await expect(presentation).toHaveCount(0);
  await expect(launch).toBeFocused();
  await expect(page.getByRole("status")).toHaveText("Slide 3 de 6");
});

test("tela cheia nativa entra e sai preservando o slide e devolvendo o foco", async ({
  page,
}) => {
  await page.goto("/");
  const launch = page.getByRole("button", { name: "Apresentar aula" });
  await launch.click();
  await page.getByRole("button", { name: "Tela cheia", exact: true }).click();
  await expect
    .poll(() => page.evaluate(() => Boolean(document.fullscreenElement)))
    .toBe(true);
  await page.getByRole("dialog").press("ArrowRight");
  await page.evaluate(() => document.exitFullscreen());
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(launch).toBeFocused();
  await expect(page.getByRole("status")).toHaveText("Slide 2 de 6");
});

test("sem enriquecimentos, opcionais e mobile não inventam conteúdo documental", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page
    .getByRole("combobox", { name: "Exemplo", exact: true })
    .selectOption("empty");
  await expect(page.locator(".lesson-evidence")).toHaveCount(0);
  await expect(page.locator("main")).toContainText(
    "Sem enriquecimentos científicos aprovados",
  );
  await page
    .getByRole("button", { name: "Plano de aula", exact: true })
    .click();
  await expect(
    page.getByRole("article", { name: "Plano de aula" }),
  ).toContainText("Sem enriquecimentos científicos aprovados");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page
    .getByRole("combobox", { name: "Exemplo", exact: true })
    .selectOption("optional");
  await expect(page.getByRole("alert")).toHaveCount(0);
  await page.getByRole("button", { name: "Apresentar aula" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.keyboard.press("Escape");
});

test("HTML continua literal em títulos, blocos, notas, atividade, fontes e participantes", async ({
  page,
}) => {
  await page.goto("/");
  const bundle = example();
  const attack = '<img src=x onerror="window.lessonInjected=true">';
  bundle.metadata.title = attack;
  bundle.slides[0].title = attack;
  bundle.slides[0].content_blocks = [{ type: "text", text: attack }];
  bundle.slides[0].speaker_notes = attack;
  bundle.references[0].claim_supported = attack;
  bundle.references[0].source_title = attack;
  bundle.references[0].participants = [attack];
  bundle.activities[0].prompt = attack;
  bundle.activities[0].teacher_guidance = attack;
  await replaceExample(page, bundle);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(attack);
  await expect(page.locator("main")).toContainText(attack);
  await page
    .getByRole("button", { name: "Plano de aula", exact: true })
    .click();
  await expect(
    page.getByRole("article", { name: "Plano de aula" }),
  ).toContainText(attack);
  await expect(page.locator("main img, main script")).toHaveCount(0);
  expect(
    await page.evaluate(() => Object.hasOwn(window, "lessonInjected")),
  ).toBe(false);
});

for (const url of [
  "javascript:alert(1)",
  "data:text/html,<script>alert(1)</script>",
  "//evil.test",
  "https://user:pass@example.com",
  "https://example.com/\nunsafe",
]) {
  test(`rejeita link inseguro: ${url.slice(0, 30)}`, async ({ page }) => {
    await page.goto("/");
    const bundle = example();
    bundle.references[0].source_url = url;
    await replaceExample(page, bundle);
    await expect(page.getByRole("alert")).toContainText(
      "Fonte documental inválida",
    );
    await expect(
      page.getByRole("button", { name: "Apresentar aula" }),
    ).toHaveCount(0);
    await expect(page.locator("main a")).toHaveCount(0);
  });
}

test("IDs documentais e blocos inválidos são rejeitados antes de apresentar", async ({
  page,
}) => {
  await page.goto("/");
  const missing = example();
  missing.references[0].id = "unknown";
  await replaceExample(page, missing);
  await expect(page.getByRole("alert")).toBeVisible();
  const wrongContribution = example();
  wrongContribution.slides[3].contribution_ids = ["other"];
  await replaceExample(page, wrongContribution);
  await expect(page.getByRole("alert")).toContainText("evidências");
  const unsupported = example();
  await page.evaluate((bundle) => {
    Object.assign(bundle.slides[0].content_blocks[0], {
      type: "html",
      html: "<script>alert(1)</script>",
    });
    window.setLessonExample(bundle);
  }, unsupported);
  await expect(page.getByRole("alert")).toContainText("bloco inválido");
});

test("ordem das seções prevalece sobre a coleção de slides e texto longo não é truncado", async ({
  page,
}) => {
  await page.goto("/");
  const bundle = example();
  bundle.slides.reverse();
  bundle.references[0].claim_supported =
    "Afirmação documental completa. ".repeat(45) + "FIM DOCUMENTAL";
  await replaceExample(page, bundle);
  await expect(
    page.getByRole("article", { name: /^Slide 1 de/ }).getByRole("heading"),
  ).toHaveText(bundle.metadata.title);
  await page.getByRole("button", { name: /Ciência e autoria/ }).click();
  const slide = page.getByRole("article", { name: /^Slide / });
  await expect(slide).toContainText(bundle.references[0].claim_supported);
  expect(await slide.evaluate((node) => getComputedStyle(node).overflowY)).toBe(
    "auto",
  );
  await slide.focus();
  await page.keyboard.press("ArrowDown");
  await expect
    .poll(() => slide.evaluate((node) => node.scrollTop))
    .toBeGreaterThan(0);
  await expect(page.getByRole("status")).toHaveText("Slide 4 de 6");
});

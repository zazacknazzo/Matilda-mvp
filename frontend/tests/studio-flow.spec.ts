import { test, expect } from "@playwright/test";

// No API interception, fixture import, seed, or prepared browser storage.
// The test server replaces only the external Gemini port.
for (const width of [1440, 390]) {
  test(`CRISPR completo com API/SQLite reais · largura ${width}`, async ({
    page,
    browser,
  }) => {
    await page.setViewportSize({ width, height: 1050 });
    await page.goto("/#studio");
    await expect(page.getByLabel("Título da aula")).toHaveValue("");
    await page
      .getByLabel("Título da aula")
      .fill("CRISPR revisado pela professora");
    await page
      .getByLabel("Texto original")
      .fill(
        "CRISPR-Cas9 permite discutir edição genética e mecanismos moleculares.",
      );
    await page.getByRole("button", { name: "Criar prévia" }).focus();
    await page.keyboard.press("Enter");
    await expect(
      page.getByRole("heading", { name: "Prévia de enriquecimento" }),
    ).toBeVisible();
    await page
      .getByRole("button", { name: "Revisar fontes e objetivos" })
      .focus();
    await page.keyboard.press("Enter");
    const review = page.getByRole("main", { name: "Revisão docente" });
    await expect(review).toBeVisible();
    const cards = review.locator("article.review-suggestion");
    expect(await cards.count()).toBeGreaterThanOrEqual(2);
    await expect(cards.first().getByRole("link").first()).toHaveAttribute(
      "href",
      /^https:\/\//,
    );
    await expect(
      page.getByRole("button", { name: "Continuar para geração" }),
    ).toBeDisabled();
    await cards.first().getByLabel("Aceitar", { exact: true }).focus();
    await page.keyboard.press("Space");
    for (let i = 1; i < (await cards.count()); i++) {
      await cards.nth(i).getByLabel("Rejeitar", { exact: true }).focus();
      await page.keyboard.press("Space");
    }
    await cards
      .first()
      .getByLabel("Proposta pedagógica")
      .fill(
        "Relacionar o mecanismo molecular ao debate de evidências em sala.",
      );
    await page
      .getByLabel("Objetivos de aprendizagem · um por linha")
      .fill("Explicar a edição genética com base no mecanismo molecular.");
    await page.getByLabel("Revisei e aprovo estes objetivos").focus();
    await page.keyboard.press("Space");
    await page
      .getByRole("button", { name: "Salvar revisão", exact: true })
      .focus();
    await page.keyboard.press("Enter");
    await expect(page.getByRole("status")).toContainText("Revisão salva");
    const reviewUrl = page.url();
    await page.reload();
    await expect(
      cards.first().getByLabel("Aceitar", { exact: true }),
    ).toBeChecked();
    await expect(
      cards.nth(1).getByLabel("Rejeitar", { exact: true }),
    ).toBeChecked();
    await expect(cards.first().getByLabel("Proposta pedagógica")).toHaveValue(
      "Relacionar o mecanismo molecular ao debate de evidências em sala.",
    );
    await page.getByRole("button", { name: "Continuar para geração" }).focus();
    await page.keyboard.press("Enter");
    await expect(
      page.getByRole("button", { name: "Gerar minha aula" }),
    ).toBeEnabled();
    await page.getByRole("button", { name: "Gerar minha aula" }).focus();
    const generated = page.waitForResponse(
      (response) =>
        response.url().endsWith("/api/studio/generate") &&
        response.status() === 201,
    );
    await page.keyboard.press("Enter");
    const bundle = await (await generated).json();
    await expect(
      page.getByRole("button", { name: "Abrir aula existente" }),
    ).toBeEnabled();
    await page.getByRole("button", { name: "Abrir aula existente" }).focus();
    await page.keyboard.press("Enter");
    await expect(page).toHaveURL(
      new RegExp(`studio/lessons/${bundle.lesson_bundle_id}$`),
    );
    await expect(
      page.getByRole("heading", {
        name: "CRISPR revisado pela professora",
        exact: true,
      }),
    ).toBeVisible();
    await page
      .getByRole("button", { name: "Plano de aula", exact: true })
      .focus();
    await page.keyboard.press("Enter");
    await expect(
      page
        .getByRole("article", { name: "Plano de aula", exact: true })
        .getByText(
          "Explicar a edição genética com base no mecanismo molecular.",
          { exact: true },
        ),
    ).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    const lessonUrl = page.url();
    await page.reload();
    await expect(
      page.getByRole("button", { name: "Apresentar aula ↗" }),
    ).toBeVisible();
    await page.getByRole("button", { name: "Voltar à revisão" }).focus();
    await page.keyboard.press("Enter");
    await expect(page).toHaveURL(reviewUrl);
    await expect(
      cards.first().getByLabel("Aceitar", { exact: true }),
    ).toBeChecked();
    await expect(
      cards.nth(1).getByLabel("Rejeitar", { exact: true }),
    ).toBeChecked();
    const isolated = await browser.newContext();
    const tab = await isolated.newPage();
    await tab.goto(lessonUrl);
    await expect(tab.getByRole("alert")).toContainText("indisponível");
    await expect(
      tab.getByRole("button", { name: "Apresentar aula ↗" }),
    ).toHaveCount(0);
    await isolated.close();
  });
}

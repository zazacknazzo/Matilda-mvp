import { test, expect } from "@playwright/test";

// Public browser seams requested in the UI/UX brief: orientation, keyboard,
// controlled preview/review, and narrow-screen access to the next action.
for (const width of [1440, 768, 375]) {
  test(`docente encontra a próxima etapa e acessa revisão por teclado · ${width}`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 960 });
    await page.goto("/#studio");
    const steps = page.getByRole("list", { name: "Etapas da aula" });
    await expect(steps.locator('[aria-current="step"]')).toHaveText(/Preparar/);
    await page
      .getByRole("link", { name: "Ir para o conteúdo do Studio" })
      .focus();
    await page.keyboard.press("Enter");
    await expect(page.locator("#studio-main")).toBeFocused();
    await page.getByLabel("Título da aula").fill("CRISPR em sala de aula");
    await page
      .getByLabel("Texto original")
      .fill("CRISPR-Cas9 permite discutir edição genética.");
    await page
      .getByRole("button", { name: "Criar prévia", exact: true })
      .click();
    await expect(steps.locator('[aria-current="step"]')).toHaveText(/Conferir/);
    const next = page.getByRole("button", {
      name: "Revisar fontes e objetivos",
    });
    await expect(next).toBeInViewport();
    if (width === 1440) await next.click();
    else {
      await next.focus();
      await page.keyboard.press("Enter");
    }
    await expect(steps.locator('[aria-current="step"]')).toHaveText(/Revisar/);
    await page
      .getByRole("link", { name: "Ir para objetivos e salvar" })
      .focus();
    await page.keyboard.press("Enter");
    await expect(page.locator("#review-actions")).toBeFocused();
    await expect(
      page.getByRole("button", { name: "Continuar para geração" }),
    ).toBeDisabled();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
  });
}

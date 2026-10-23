import { test, expect } from "@playwright/test";

test("texto CRISPR chega à prévia persistida com fontes e sessão isolada", async ({
  page,
  browser,
}, testInfo) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Studio — Criar aula" }).click();
  await page.getByLabel("Título da aula").fill("Edição genética");
  const original =
    "  CRISPR-Cas9 é uma ferramenta para discutir edição genética.\nTexto original preservado.  ";
  await page.getByLabel("Texto original").fill(original);
  await page.getByLabel("Conceitos (um por linha)").fill("CRISPR-Cas9");
  await expect(page.getByText(/enviado ao provedor de IA/)).toBeVisible();
  await page.getByRole("button", { name: "Criar prévia" }).click();
  await expect(page.getByRole("status")).toContainText("Preparando");
  await expect(
    page.getByRole("heading", { name: "Prévia de enriquecimento" }),
  ).toBeVisible();
  await expect(page.getByTestId("original-document").first()).toHaveText(
    original,
  );
  await expect(page.getByText("Pendente", { exact: true }).first()).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Abrir fonte original" }).first(),
  ).toHaveAttribute("href", /^https:\/\//);
  await page.screenshot({
    path: testInfo.outputPath("studio-preview-desktop.png"),
    fullPage: true,
  });
  const hash = new URL(page.url()).hash;
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Prévia de enriquecimento" }),
  ).toBeVisible();
  await expect(page.getByTestId("original-document").first()).toHaveText(
    original,
  );
  await page
    .getByRole("button", { name: "Forensics — Investigar ciência" })
    .click();
  await page.getByRole("button", { name: "Studio — Criar aula" }).click();
  await expect(
    page.getByRole("heading", { name: "Prévia de enriquecimento" }),
  ).toBeVisible();
  const other = await browser.newContext();
  const tab = await other.newPage();
  await tab.goto("/" + hash);
  await expect(tab.getByRole("alert")).toContainText("indisponível");
  await expect(tab.getByTestId("original-document")).toHaveCount(0);
  await other.close();
});

test("sem cobertura e falha do provedor preservam uma experiência honesta", async ({
  page,
}) => {
  await page.goto("/#studio");
  await page.getByLabel("Título da aula").fill("Triângulos");
  await page.getByLabel("Texto original").fill("Trigonometria e triângulos.");
  await page.getByRole("button", { name: "Criar prévia" }).click();
  await expect(
    page.getByText("Sem cobertura documental", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Editar entrada" }).click();
  await page.getByLabel("Texto original").fill("CRISPR-Cas9 falha controlada");
  await page.getByRole("button", { name: "Criar prévia" }).click();
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(page.getByLabel("Texto original")).toHaveValue(
    "CRISPR-Cas9 falha controlada",
  );
  await page
    .getByLabel("Texto original")
    .fill("CRISPR-Cas9 e edição genética.");
  await page.getByRole("button", { name: "Criar prévia" }).click();
  await expect(
    page.getByRole("heading", { name: "Prévia de enriquecimento" }),
  ).toBeVisible();
});

test("formulário e prévia funcionam no celular com teclado e HTML como texto", async ({
  page,
}, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/#studio");
  await page.getByLabel("Título da aula").fill("CRISPR");
  await page
    .getByLabel("Texto original")
    .fill("CRISPR-Cas9 <script>window.pwned = true</script>");
  await page.getByRole("button", { name: "Criar prévia" }).focus();
  await page.keyboard.press("Enter");
  await expect(
    page.getByRole("heading", { name: "Prévia de enriquecimento" }),
  ).toBeVisible();
  await page.screenshot({
    path: testInfo.outputPath("studio-preview-mobile.png"),
    fullPage: true,
  });
  expect(await page.evaluate(() => "pwned" in window)).toBe(false);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await expect(
    page.getByRole("button", { name: /Gerar aula|Aceitar|Rejeitar/ }),
  ).toHaveCount(0);
});

import { test, expect } from "@playwright/test";

test("Transformar em aula transfere investigação e snapshot à configuração confirmável", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.getByText(/HARNESS DE TESTE T06/)).toBeVisible();
  await page
    .getByLabel("Material em preparação")
    .fill("Minha preparação e decisões preservadas");
  await page
    .getByRole("button", { name: "Carregar investigação pela API Forensics" })
    .click();
  await expect(page.getByLabel("Investigação carregada")).not.toBeEmpty();
  const id = await page.getByLabel("Investigação carregada").innerText();
  await page
    .getByRole("button", { name: "Transformar em aula", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Confirmar configuração da aula" }),
  ).toBeVisible();
  const transfer = JSON.parse(
    await page.getByLabel("Transferência recebida").innerText(),
  );
  expect(transfer.origin).toEqual({ analysis_id: id });
  expect(transfer.snapshot.scientific_context.analysis_id).toBe(id);
  expect(transfer.snapshot.matches[0].contribution.participants).toContain(
    "Martin Jínek",
  );
  expect(transfer.snapshot.matches[0].evidence[0].source_url).toBe(
    "https://doi.org/10.1126/science.1225829",
  );
  expect(transfer.state).toEqual({
    material: "Minha preparação e decisões preservadas",
    decision: "accepted",
    slide: 3,
    view: "list",
  });
  await page
    .getByRole("button", { name: "Voltar à investigação", exact: true })
    .click();
  await expect(page.getByLabel("Material em preparação")).toHaveValue(
    "Minha preparação e decisões preservadas",
  );
});

test("Texto sem DOI explora dossiê canônico e devolve o estado por teclado", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByLabel("Cenário").selectOption("text");
  await page
    .getByLabel("Material em preparação")
    .fill("Revisão docente ainda em preparação");
  const explore = page
    .getByRole("button", { name: /Explorar descoberta/ })
    .first();
  await explore.focus();
  await page.keyboard.press("Enter");
  const dossier = page.getByRole("region", { name: "Dossiê científico" });
  await expect(dossier).toBeVisible();
  await expect(
    dossier.getByRole("heading", { name: "Dossiê científico", exact: true }),
  ).toBeFocused();
  await expect(dossier).toContainText("Sem artigo comparável");
  await expect(dossier).toContainText("Comparação inconclusiva");
  await expect(dossier).toContainText("RELATED_TO");
  await expect(dossier).toContainText("Martin Jínek");
  await expect(dossier).toContainText("Jennifer A. Doudna");
  await expect(dossier).toContainText("Emmanuelle Charpentier");
  await expect(
    dossier.getByRole("link", { name: /A programmable dual/i }),
  ).toHaveAttribute("href", "https://doi.org/10.1126/science.1225829");
  await expect(
    dossier.getByText("Afirmação sustentada", { exact: true }),
  ).toBeVisible();
  await expect(page.locator(".react-flow")).toHaveCount(0);
  await dossier.getByRole("button", { name: "Voltar ao Studio" }).click();
  await expect(explore).toBeFocused();
  expect(
    JSON.parse(await page.getByLabel("Estado devolvido").innerText()),
  ).toEqual({
    material: "Revisão docente ainda em preparação",
    decision: "accepted",
    slide: 3,
    view: "list",
  });
  await expect(page.getByLabel("Material em preparação")).toHaveValue(
    "Revisão docente ainda em preparação",
  );
  await explore.click();
  await dossier.screenshot({
    path: "../.runtime/t06-dossier-desktop.png",
  });
});

test("DOI sem investigação transfere somente DOI e preserva ciência RNA no celular", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.getByLabel("Cenário").selectOption("rna");
  await expect(
    page.getByRole("button", { name: /Explorar descoberta/ }),
  ).toHaveCount(2);
  await page
    .getByRole("button", { name: "Transformar em aula", exact: true })
    .click();
  const transfer = JSON.parse(
    await page.getByLabel("Transferência recebida").innerText(),
  );
  expect(transfer.origin).toEqual({ doi: "10.1056/nejmoa2034577" });
  expect(
    transfer.snapshot.matches.map(
      (match: { contribution: { id: string } }) => match.contribution.id,
    ),
  ).toEqual(["rna-2005", "rna-2008"]);
  await page
    .getByRole("button", { name: "Voltar à investigação", exact: true })
    .click();
  await page
    .getByRole("button", { name: /Explorar descoberta/ })
    .first()
    .click();
  const dossier = page.getByRole("region", { name: "Dossiê científico" });
  await expect(dossier).toContainText("Katalin Karikó");
  await expect(dossier).toContainText("Drew Weissman");
  await expect(dossier).toContainText("Metadados em cache");
  await expect(dossier).toContainText("2026-10-21");
  await expect(dossier).toContainText("Origem: doi");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await dossier.screenshot({
    path: "../.runtime/t06-dossier-mobile.png",
  });
});

test("Sem cobertura não inventa descobertas e permite preparação com snapshot vazio", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByLabel("Cenário").selectOption("empty");
  await expect(
    page.getByRole("region", { name: "Ponte Forensics–Studio" }),
  ).toContainText("não indica inexistência de contribuições femininas");
  await expect(
    page.getByRole("button", { name: /Explorar descoberta/ }),
  ).toHaveCount(0);
  await page
    .getByRole("button", { name: "Transformar em aula", exact: true })
    .click();
  const transfer = JSON.parse(
    await page.getByLabel("Transferência recebida").innerText(),
  );
  expect(transfer.snapshot.matches).toEqual([]);
});

test("Dossiê usa somente o snapshot, mesmo com APIs indisponíveis ou link expirado", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByRole("button", { name: "Carregar investigação pela API Forensics" })
    .click();
  await expect(page.getByLabel("Investigação carregada")).not.toBeEmpty();
  const requests: string[] = [];
  await page.route("**/api/**", (route) => {
    requests.push(route.request().url());
    return route.fulfill({
      status: 404,
      json: { detail: "Investigação expirada" },
    });
  });
  await page
    .getByRole("button", { name: /Explorar descoberta/ })
    .first()
    .click();
  await expect(
    page.getByRole("region", { name: "Dossiê científico" }),
  ).toContainText("Cas9 programável");
  await expect(
    page.getByRole("region", { name: "Dossiê científico" }),
  ).toContainText("Citação identificada");
  await expect(
    page.getByRole("region", { name: "Dossiê científico" }),
  ).toContainText("ciência registrada permanece disponível");
  await page.getByRole("button", { name: "Voltar ao Studio" }).click();
  expect(requests).toEqual([]);
});

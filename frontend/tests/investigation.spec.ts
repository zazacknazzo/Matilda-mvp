import { test, expect } from "@playwright/test";
import type { Analysis } from "../src/types";

test("mapa guiado respeita filtros e abre fontes em celular, tablet e desktop", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: /Edição genômica/ }).click();
  const response = page.waitForResponse(
    (response) =>
      response.url().endsWith("/api/analyses") &&
      response.request().method() === "POST",
  );
  await page
    .getByRole("button", { name: "Investigar contribuições femininas" })
    .click();
  const analysis: Analysis = await (await response).json();
  await expect(
    page.getByRole("button", { name: "Mapa simples", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  for (const status of ["CITED", "UNKNOWN"]) {
    await page.getByLabel("Presença nas referências").selectOption(status);
    const count = analysis.contributions.filter(
      (match) => match.citation_status === status,
    ).length;
    await expect(page.locator(".map-story")).toHaveCount(count);
    if (!count) await expect(page.locator(".map-empty")).toBeVisible();
  }
  await page.getByLabel("Presença nas referências").selectOption("all");
  for (const width of [1440, 1024, 768, 390, 320]) {
    await page.setViewportSize({ width, height: 900 });
    const mapTab = page.getByRole("button", {
      name: "Mapa e lista",
      exact: true,
    });
    if (await mapTab.isVisible()) await mapTab.click();
    await expect(page.locator(".guided-map")).toBeVisible();
    await expect(page.locator(".map-story")).toHaveCount(
      analysis.contributions.length,
    );
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    if (width === 1440 || width === 390)
      await page.screenshot({
        path: `../docs/screenshots/mapa-${width}.png`,
        fullPage: true,
      });
    await page.locator(".map-evidence-button").last().focus();
    await page.keyboard.press("Enter");
    await expect(page.locator(".evidence-region")).toBeFocused();
    await expect(page.locator(".dossier")).toBeVisible();
    await expect(page.locator(".dossier .source-card a").first()).toBeVisible();
  }
});

test("DOI, investigação, evidência, camadas, lista e exportação", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: /Toda descoberta/ }),
  ).toBeVisible();
  await page.screenshot({
    path: "../docs/screenshots/inicio.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: /Edição genômica/ }).click();
  await expect(
    page.getByRole("heading", {
      name: "Multiplex Genome Engineering Using CRISPR/Cas Systems",
    }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Investigar contribuições femininas" })
    .click();
  await expect(
    page.getByRole("heading", {
      name: "Explore o conhecimento. Siga as evidências.",
    }),
  ).toBeVisible();
  await page
    .locator(".discovery-card")
    .filter({ hasText: "Cas9 programável" })
    .click();
  await expect(page.locator(".dossier")).toContainText("Jennifer A. Doudna");
  await expect(page.locator(".dossier")).toContainText(
    "Emmanuelle Charpentier",
  );
  await expect(page.locator(".dossier")).toContainText("Citação identificada");
  await expect(page.locator(".source-card a")).toHaveAttribute(
    "href",
    "https://doi.org/10.1126/science.1225829",
  );
  await expect(
    page.getByRole("region", { name: "Mapa simplificado da investigação" }),
  ).toBeVisible();
  await expect(page.locator(".map-story")).toHaveCount(4);
  await page
    .getByRole("button", { name: "Rede completa", exact: true })
    .click();
  await expect(page.locator(".react-flow__node").first()).toHaveCSS(
    "visibility",
    "visible",
  );
  await expect(page.locator(".react-flow__edge")).not.toHaveCount(0);
  await page.screenshot({
    path: "../docs/screenshots/investigacao.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Bibliografia", exact: true }).click();
  await expect(page.locator(".react-flow__node")).not.toHaveCount(0);
  await page
    .getByRole("button", { name: "Contribuições", exact: true })
    .click();
  await page.getByRole("button", { name: "Lista", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Relações da investigação" }),
  ).toBeVisible();
  await expect(page.locator(".text-results")).toContainText("Relação temática");
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("link", { name: "Dossiê .md" }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toMatch(/matilda-.*\.md/);
  expect(errors).toEqual([]);
});

test("cenário RNA e navegação mobile sem depender do grafo", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.getByRole("button", { name: /Vacinas de RNA/ }).click();
  await page
    .getByRole("button", { name: "Investigar contribuições femininas" })
    .click();
  await expect(page.locator(".discovery-card")).toHaveCount(2);
  await page.locator(".discovery-card").first().click();
  await expect(page.locator(".dossier")).toContainText("Katalin Karikó");
  await expect(page.locator(".source-card a")).toHaveAttribute(
    "href",
    /https:\/\/doi.org\//,
  );
  await page.screenshot({
    path: "../docs/screenshots/mobile.png",
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.getByRole("button", { name: "Mapa e lista" }).click();
  await expect(page.locator(".guided-map")).toBeVisible();
  await expect(page.locator(".map-story")).toHaveCount(2);
  await page.locator(".map-evidence-button").first().click();
  await expect(page.locator(".evidence-region")).toBeFocused();
  await expect(page.locator(".dossier")).toContainText("Katalin Karikó");
  await page.getByRole("button", { name: "Mapa e lista" }).click();
  await page.getByRole("button", { name: "Lista", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Relações da investigação" }),
  ).toBeVisible();
});

test("DOI inválido e ausência de cobertura sem resultados inventados", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByLabel("COMECE POR UM ARTIGO CIENTÍFICO").fill("não-é-doi");
  await page.getByRole("button", { name: "Recuperar artigo por DOI" }).click();
  await expect(page.getByRole("alert")).toContainText("DOI inválido");
  await page
    .getByLabel("COMECE POR UM ARTIGO CIENTÍFICO")
    .fill("10.1038/171737a0");
  await page.getByRole("button", { name: "Recuperar artigo por DOI" }).click();
  await page
    .getByRole("button", { name: "Investigar contribuições femininas" })
    .click();
  await expect(
    page.getByRole("heading", { name: "Sem correspondência no catálogo" }),
  ).toBeVisible();
  await expect(page.locator(".empty-result")).toContainText(
    "não indica ausência",
  );
});

test("busca e descoberta por teclado", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("COMECE POR UM ARTIGO CIENTÍFICO").focus();
  await page.keyboard.type("10.1126/science.1231143");
  await page.keyboard.press("Enter");
  const investigate = page.getByRole("button", {
    name: "Investigar contribuições femininas",
  });
  await investigate.focus();
  await page.keyboard.press("Enter");
  const first = page.locator(".discovery-card").first();
  await expect(first).toBeVisible();
  await first.focus();
  await page.keyboard.press("Enter");
  await expect(page.locator(".dossier .source-card a")).toBeVisible();
  await page.getByRole("button", { name: "Lista", exact: true }).focus();
  await page.keyboard.press("Enter");
  await expect(
    page.getByRole("heading", { name: "Relações da investigação" }),
  ).toBeVisible();
});

test("ampliação automática distingue candidatos, identidades e fontes", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: /Vacinas de RNA/ }).click();
  const created = page.waitForResponse(
    (response) =>
      response.url().endsWith("/api/analyses") &&
      response.request().method() === "POST",
  );
  await page
    .getByRole("button", { name: "Investigar contribuições femininas" })
    .click();
  const analysis = await (await created).json();
  const candidate = (id: string, documented: boolean) => ({
    candidate: {
      id,
      work: {
        doi: "10.9999/" + id,
        title: "Candidato de teste " + id,
        year: 2025,
        authors: [
          { name: "Pessoa da fixture", openalex_id: null, orcid: null },
        ],
        topics: [],
        sources: [
          {
            source: "europe_pmc",
            source_url: "https://www.ebi.ac.uk/europepmc/",
            retrieved_at: "2026-10-21T00:00:00Z",
            from_cache: true,
          },
        ],
      },
      record_state: "automatically_extracted",
      verification_status: "pending_review",
      extraction_method: "abstract_excerpt_v1",
      excerpt: "We show a result from a synthetic test fixture.",
      excerpt_location: "Resumo: frase de resultados.",
      identities: [
        {
          author_name: "Pessoa da fixture",
          status: documented ? "documented_woman" : "unknown",
          method: documented ? "wikidata_orcid" : "unresolved",
          explanation:
            "Identidade determinada apenas por identificador persistente.",
          source_urls: documented ? ["https://www.wikidata.org/wiki/Q123"] : [],
        },
      ],
      limitations: ["Atribuição individual não revisada."],
    },
    retrieval_reasons: ["Tópico compartilhado"],
    citation_status: "UNKNOWN",
    relation_type: "RELATED_TO",
  });
  await page.route("**/api/analyses/*/discovery", (route) =>
    route.fulfill({
      json: {
        ...analysis,
        external_discovery: {
          status: "partial",
          started_at: "2026-10-21T00:00:00Z",
          completed_at: "2026-10-21T00:00:02Z",
          candidates: [candidate("one", true), candidate("two", false)],
          warnings: ["Referências incompletas."],
          sources: [],
          limits: { candidates: 8 },
        },
      },
    }),
  );
  await page.locator(".advanced-discovery > summary").click();
  await page
    .getByRole("button", { name: "Ampliar descoberta automaticamente" })
    .click();
  await expect(page.locator(".candidate-card")).toHaveCount(2);
  await expect(page.locator(".automatic-results > summary")).toContainText(
    "Resultado parcial",
  );
  await expect(page.locator(".candidate-card").first()).toContainText(
    "Pendente de revisão",
  );
  await expect(page.locator(".automatic-discovery")).not.toContainText(
    "Contribuição documentada",
  );
  await page
    .getByRole("checkbox", { name: /Mostrar apenas trabalhos/ })
    .check();
  await expect(page.locator(".candidate-card")).toHaveCount(1);
  await page
    .getByText("Autoria e resolução de identidades", { exact: true })
    .click();
  await expect(page.locator(".candidate-identity")).toContainText(
    "Mulher identificada em fonte explícita",
  );
  await expect(
    page.getByRole("link", { name: "Fonte de identidade" }),
  ).toHaveAttribute("href", "https://www.wikidata.org/wiki/Q123");
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});

test("falha de ampliação preserva investigação e permite nova tentativa", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: /Edição genômica/ }).click();
  await page
    .getByRole("button", { name: "Investigar contribuições femininas" })
    .click();
  await page.route("**/api/analyses/*/discovery", (route) =>
    route.fulfill({
      status: 503,
      json: { detail: "Fonte indisponível na fixture." },
    }),
  );
  await page.locator(".advanced-discovery > summary").click();
  await page
    .getByRole("button", { name: "Ampliar descoberta automaticamente" })
    .click();
  await expect(page.locator(".automatic-error")).toContainText(
    "Fonte indisponível",
  );
  await expect(page.locator(".discovery-card")).toHaveCount(4);
  await expect(
    page.getByRole("button", { name: "Ampliar descoberta automaticamente" }),
  ).toBeEnabled();
});

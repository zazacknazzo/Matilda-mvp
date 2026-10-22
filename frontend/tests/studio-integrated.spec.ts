import { test, expect, type Page } from "@playwright/test";

async function prepareGeneration(
  page: Page,
  alreadyReview = false,
  acceptAll = false,
) {
  const openReview = page.getByRole("button", {
    name: "Revisar fontes e objetivos",
  });
  if (!alreadyReview) await openReview.click();
  await expect(
    page.getByLabel("Revisei e aprovo estes objetivos"),
  ).toBeVisible();
  const cards = page.locator("article.review-suggestion");
  for (let i = 0; i < (await cards.count()); i++)
    await cards
      .nth(i)
      .getByLabel(i === 0 || acceptAll ? "Aceitar" : "Rejeitar", {
        exact: true,
      })
      .check();
  await page
    .getByLabel("Objetivos de aprendizagem · um por linha")
    .fill("Explicar o mecanismo e conferir suas fontes.");
  await page.getByLabel("Revisei e aprovo estes objetivos").check();
  await page
    .getByRole("button", { name: "Salvar revisão", exact: true })
    .click();
  await expect(page.getByRole("status")).toContainText("Revisão salva");
  await page.getByRole("button", { name: "Continuar para geração" }).click();
}

async function approveAndGenerate(page: Page, alreadyReview = false) {
  await prepareGeneration(page, alreadyReview);
  const response = page.waitForResponse(
    (r) => r.url().endsWith("/api/studio/generate") && r.status() === 201,
  );
  await page.getByRole("button", { name: "Gerar minha aula" }).click();
  const bundle = await (await response).json();
  expect(bundle.metadata.duration_minutes).toBe(50);
  await page.getByRole("button", { name: "Abrir aula existente" }).click();
  return bundle;
}

test("Forensics → configuração confirmável → ciência → aula → Markdown e impressão", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: /Edição genômica/ }).click();
  await page
    .getByRole("button", { name: "Investigar contribuições femininas" })
    .click();
  await page.getByRole("button", { name: "Lista", exact: true }).click();
  await page
    .getByRole("button", { name: "Transformar em aula", exact: true })
    .click();
  await expect(page.getByLabel("Investigação de origem")).not.toBeEmpty();
  await expect(page.getByLabel("Duração (minutos)")).toHaveValue("50");
  await page.getByLabel("Título da aula").fill("CRISPR integrado");
  await page.getByRole("button", { name: "Criar prévia" }).click();
  await expect(
    page.getByRole("heading", { name: "Prévia de enriquecimento" }),
  ).toBeVisible();
  const bundle = await approveAndGenerate(page);
  expect(bundle.references[0].participants).toContain("Martin Jínek");
  const slide = page
    .getByRole("navigation", { name: "Sequência de slides" })
    .getByRole("button")
    .nth(2);
  await slide.click();
  const explore = page.getByRole("button", { name: "Explorar fontes da aula" });
  await expect(explore).toBeVisible();
  await explore.click();
  await expect(
    page.getByRole("complementary", { name: "Inspetor de evidências" }),
  ).toContainText("Martin Jínek");
  await page.getByRole("button", { name: "Voltar ao Studio" }).click();
  await expect(slide).toHaveAttribute("aria-current", "step");
  await page.getByRole("button", { name: "Apresentar aula ↗" }).click();
  const projected = page.getByRole("dialog");
  await expect(projected).toBeVisible();
  await expect(
    projected.getByRole("complementary", { name: "Notas do professor" }),
  ).toHaveCount(0);
  await page.keyboard.press("ArrowRight");
  await page.keyboard.press("Escape");
  await expect(projected).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Apresentar aula ↗" }),
  ).toBeFocused();
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: /Baixar Markdown/ }).click();
  expect((await download).suggestedFilename()).toMatch(/\.md$/);
  await page
    .getByRole("button", { name: "Plano de aula", exact: true })
    .click();
  await page.emulateMedia({ media: "print" });
  await expect(page.locator(".lesson-print-view")).toContainText(
    "CRISPR integrado",
  );
  const pdf = "../.runtime/t13-plan-crispr.pdf";
  const printed = await page.pdf({
    path: pdf,
    format: "A4",
    printBackground: true,
  });
  expect(printed.subarray(0, 5).toString()).toBe("%PDF-");
  expect(printed.length).toBeGreaterThan(10000);
  await page
    .locator(".lesson-print-view")
    .screenshot({ path: "../.runtime/t13-plan-crispr-print.png" });
  await page.emulateMedia({ media: "screen" });
  await page
    .getByRole("button", { name: "Forensics — Investigar ciência" })
    .click();
  await expect(
    page.getByRole("heading", { name: "Relações da investigação" }),
  ).toBeVisible();
});

test("RNA por DOI explora evidência sem perder edição docente e gera aula de 50 minutos", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/#studio");
  await page.getByLabel("Título da aula").fill("RNA integrado");
  await page
    .getByLabel("DOI do artigo (opcional)")
    .fill("10.1056/NEJMoa2034577");
  await page.getByRole("button", { name: "Criar prévia" }).click();
  await page
    .getByRole("button", { name: "Revisar fontes e objetivos" })
    .click();
  const first = page.locator("article.review-suggestion").first();
  await first
    .getByLabel("Proposta pedagógica")
    .fill("Minha abordagem de RNA ainda não salva.");
  const explore = first.getByRole("button", { name: "Explorar descoberta" });
  await expect(explore).toBeVisible();
  await explore.click();
  const dossier = page.getByRole("region", { name: "Dossiê científico" });
  await expect(dossier).toContainText("Katalin Karikó");
  await expect(dossier).toContainText("Drew Weissman");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await dossier.screenshot({ path: "../.runtime/t13-dossier-rna-mobile.png" });
  await expect(
    dossier.getByRole("heading", { name: "Dossiê científico", exact: true }),
  ).toBeFocused();
  await dossier.getByRole("button", { name: "Voltar ao Studio" }).click();
  await expect(first.getByLabel("Proposta pedagógica")).toHaveValue(
    "Minha abordagem de RNA ainda não salva.",
  );
  await expect(explore).toBeFocused();
  const bundle = await approveAndGenerate(page, true);
  expect(bundle.references[0].contribution_id).toMatch(/^rna-/);
  expect(bundle.references[0].participants).toContain("Drew Weissman");
});

test("Texto sem DOI explora dossiê canônico e conserva o material", async ({
  page,
}) => {
  await page.goto("/#studio");
  await page.getByLabel("Título da aula").fill("CRISPR a partir do material");
  await page
    .getByLabel("Texto original")
    .fill("CRISPR-Cas9 permite discutir edição genômica.");
  await page.getByRole("button", { name: "Criar prévia" }).click();
  await page
    .getByRole("button", { name: "Revisar fontes e objetivos" })
    .click();
  await page
    .getByRole("button", { name: "Explorar descoberta", exact: true })
    .first()
    .click();
  await expect(
    page.getByRole("region", { name: "Dossiê científico" }),
  ).toContainText("Sem artigo comparável");
  await expect(
    page.getByRole("region", { name: "Dossiê científico" }),
  ).toContainText("Jennifer A. Doudna");
  await page.getByRole("button", { name: "Voltar ao Studio" }).click();
  await expect(
    page.getByRole("region", { name: "Material original" }),
  ).toContainText("CRISPR-Cas9");
});

test("Sem cobertura gera 50 minutos sem atribuições e a falha da IA conserva entrada", async ({
  page,
}) => {
  await page.goto("/#studio");
  await page.getByLabel("Título da aula").fill("Dinâmica de fluidos");
  await page
    .getByLabel("Texto original")
    .fill("Dinâmica de fluidos em tubulações.");
  await page.getByRole("button", { name: "Criar prévia" }).click();
  await expect(
    page.getByRole("heading", { name: "Sem cobertura documental" }),
  ).toBeVisible();
  const bundle = await approveAndGenerate(page);
  expect(bundle.references).toEqual([]);
  await page.goto("/#studio");
  await page.getByLabel("Título da aula").fill("Falha de IA");
  await page
    .getByLabel("Texto original")
    .fill("CRISPR-Cas9, falha controlada.");
  await page.getByRole("button", { name: "Criar prévia" }).click();
  await expect(page.getByRole("alert")).toContainText("preservado");
  await expect(page.getByLabel("Texto original")).toHaveValue(
    "CRISPR-Cas9, falha controlada.",
  );
  await page
    .getByRole("button", { name: "Forensics — Investigar ciência" })
    .click();
  await page.getByRole("button", { name: /Vacinas de RNA/ }).click();
  await expect(
    page.getByRole("button", { name: "Investigar contribuições femininas" }),
  ).toBeVisible();
});

test("Falha → consulta real de estado → retry explícito conserva a chave", async ({
  page,
}) => {
  await page.goto("/#studio");
  await page.getByLabel("Título da aula").fill("CRISPR com falha única");
  await page
    .getByLabel("Texto original")
    .fill("CRISPR-Cas9; falha única no provedor de geração.");
  await page.getByRole("button", { name: "Criar prévia" }).click();
  await prepareGeneration(page);
  const keys: string[] = [];
  page.on("request", (request) => {
    if (request.url().endsWith("/api/studio/generate"))
      keys.push(request.headers()["idempotency-key"]);
  });
  await page.getByRole("button", { name: "Gerar minha aula" }).click();
  await expect(page.getByRole("alert")).toContainText("preservada");
  await expect(
    page.getByRole("button", { name: "Gerar minha aula" }),
  ).toBeDisabled();
  await page.getByRole("button", { name: "Consultar estado salvo" }).click();
  await expect(
    page.getByRole("button", { name: "Gerar minha aula" }),
  ).toBeEnabled();
  await page.getByRole("button", { name: "Gerar minha aula" }).click();
  await expect(
    page.getByRole("button", { name: "Abrir aula existente" }),
  ).toBeEnabled();
  expect(keys).toHaveLength(2);
  expect(keys[1]).toBe(keys[0]);
  await page.reload();
  await expect(
    page.getByRole("button", { name: "Abrir aula existente" }),
  ).toBeEnabled();
  expect(keys).toHaveLength(2);
});

test("Desconexão após admissão reconcilia aula salva sem POST automático", async ({
  page,
}) => {
  await page.goto("/#studio");
  await page.getByLabel("Título da aula").fill("CRISPR T13-reconnect");
  await page.getByLabel("Texto original").fill("CRISPR-Cas9 · T13-reconnect");
  await page.getByRole("button", { name: "Criar prévia" }).click();
  await prepareGeneration(page);
  const id = page.url().match(/previews\/([^/]+)/)![1];
  let posts = 0;
  page.on("request", (request) => {
    if (request.url().endsWith("/api/studio/generate")) posts++;
  });
  await page.getByRole("button", { name: "Gerar minha aula" }).click();
  await expect
    .poll(
      async () =>
        (await (await page.request.get(`/api/studio/previews/${id}`)).json())
          .generation_status,
    )
    .toBe("generating");
  await page.context().setOffline(true);
  await expect(
    page.getByRole("status").filter({ hasText: "Sem conexão" }),
  ).toBeVisible();
  await expect
    .poll(
      async () =>
        (await (await page.request.get(`/api/studio/previews/${id}`)).json())
          .generation_status,
    )
    .toBe("ready");
  await page.context().setOffline(false);
  await expect(
    page.getByRole("button", { name: "Abrir aula existente" }),
  ).toBeEnabled();
  expect(posts).toBe(1);
});

test("Nova origem não é substituída pela prévia anterior ainda em execução", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: /Edição genômica/ }).click();
  await page
    .getByRole("button", { name: "Investigar contribuições femininas" })
    .click();
  await page
    .getByRole("button", { name: "Transformar em aula", exact: true })
    .click();
  await page.getByLabel("Texto original").fill("CRISPR T13-preview-race");
  const response = page.waitForResponse((r) =>
    r.url().endsWith("/api/studio/preview"),
  );
  await page.getByRole("button", { name: "Criar prévia" }).click();
  await page
    .getByRole("button", { name: "Forensics — Investigar ciência" })
    .click();
  await page
    .getByRole("button", { name: "Transformar em aula", exact: true })
    .click();
  await response;
  await expect(
    page.getByRole("heading", { name: "Preparar aula", exact: true }),
  ).toBeVisible();
  await expect(page.getByLabel("Investigação de origem")).not.toBeEmpty();
  await expect(
    page.getByRole("button", { name: "Criar prévia" }),
  ).toBeEnabled();
});

test("Explorar investigação seleciona a contribuição correta e volta ao rascunho docente", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: /Edição genômica/ }).click();
  const investigated = page.waitForResponse(
    (r) => r.url().endsWith("/api/analyses") && r.status() === 201,
  );
  await page
    .getByRole("button", { name: "Investigar contribuições femininas" })
    .click();
  const analysis = await (await investigated).json();
  await page.locator(".discovery-card").first().click();
  await page
    .getByRole("button", { name: "Transformar em aula", exact: true })
    .click();
  await page.getByRole("button", { name: "Criar prévia" }).click();
  await page
    .getByRole("button", { name: "Revisar fontes e objetivos" })
    .click();
  const second = page.locator("article.review-suggestion").nth(1);
  await second
    .getByLabel("Proposta pedagógica")
    .fill("Rascunho de autoria preservado.");
  const explore = second.getByRole("button", { name: "Explorar descoberta" });
  await explore.click();
  await expect(
    page.getByRole("button", { name: "Forensics — Investigar ciência" }),
  ).toHaveAttribute("aria-pressed", "true");
  await expect(
    page.getByRole("complementary", { name: "Inspetor de evidências" }),
  ).toContainText(analysis.contributions[1].contribution.title);
  await expect(page.locator(".discovery-card").nth(1)).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  await page
    .getByRole("button", { name: "Voltar ao Studio", exact: true })
    .click();
  await expect(second.getByLabel("Proposta pedagógica")).toHaveValue(
    "Rascunho de autoria preservado.",
  );
  await expect(explore).toBeFocused();
  // The retained canonical dossier remains usable when the original API cannot be reached.
  await page.context().setOffline(true);
  await explore.click();
  await expect(
    page.getByRole("region", { name: "Dossiê científico" }),
  ).toContainText(analysis.contributions[1].contribution.id);
  await page.getByRole("button", { name: "Voltar ao Studio" }).click();
  await expect(second.getByLabel("Proposta pedagógica")).toHaveValue(
    "Rascunho de autoria preservado.",
  );
  await page.context().setOffline(false);
});

test("Aula com duas contribuições explora cada fonte e preserva slide e foco", async ({
  page,
}) => {
  await page.goto("/#studio");
  await page.getByLabel("Título da aula").fill("Duas contribuições");
  await page
    .getByLabel("Texto original")
    .fill("CRISPR T13-multiple: edição genética.");
  await page.getByRole("button", { name: "Criar prévia" }).click();
  await prepareGeneration(page, false, true);
  const response = page.waitForResponse(
    (r) => r.url().endsWith("/api/studio/generate") && r.status() === 201,
  );
  await page.getByRole("button", { name: "Gerar minha aula" }).click();
  const bundle = await (await response).json();
  expect(
    new Set(
      bundle.references.map(
        (ref: { contribution_id: string }) => ref.contribution_id,
      ),
    ).size,
  ).toBe(2);
  await page.getByRole("button", { name: "Abrir aula existente" }).click();
  const slide = page
    .getByRole("navigation", { name: "Sequência de slides" })
    .getByRole("button")
    .nth(3);
  await slide.click();
  const sources = page.getByRole("button", { name: /Explorar fontes da aula/ });
  await expect(sources).toHaveCount(2);
  for (let index = 0; index < 2; index++) {
    await sources.nth(index).click();
    const dossier = page.getByRole("region", { name: "Dossiê científico" });
    await expect(dossier).toContainText(
      bundle.references[index].claim_supported,
    );
    await expect(dossier).toContainText(
      bundle.references[index].contribution_id,
    );
    await page.getByRole("button", { name: "Voltar ao Studio" }).click();
    await expect(sources.nth(index)).toBeFocused();
    await expect(slide).toHaveAttribute("aria-current", "step");
  }
});

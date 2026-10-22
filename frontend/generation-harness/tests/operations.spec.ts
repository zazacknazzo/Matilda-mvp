import { expect, test } from "@playwright/test";

const panel = 'section[aria-label="Geração da aula"]';
test.beforeEach(async ({ request }) => {
  await request.post("http://127.0.0.1:8017/test/reset");
});

test("reconexão consulta a aula salva sem repetir a geração", async ({
  page,
}) => {
  let posts = 0;
  await page.route("**/api/studio/generate", async (route) => {
    posts++;
    const response = await route.fetch();
    expect(response.status()).toBe(201);
    await route.abort("connectionreset");
  });
  await page.goto("/");
  const generate = page.getByRole("button", {
    name: "Gerar minha aula",
    exact: true,
  });
  await expect(generate).toBeEnabled();
  await generate.click();
  await expect(page.locator(panel).getByRole("alert")).toBeVisible();
  await page.evaluate(() => window.dispatchEvent(new Event("online")));
  await expect(
    page.getByRole("button", { name: "Abrir aula existente" }),
  ).toBeEnabled();
  await expect(generate).toBeDisabled();
  expect(posts).toBe(1);
});

test("ficar offline bloqueia gerar até uma consulta válida após reconectar", async ({
  page,
  context,
}) => {
  await page.goto("/");
  const generate = page.getByRole("button", {
    name: "Gerar minha aula",
    exact: true,
  });
  await expect(generate).toBeEnabled();
  await context.setOffline(true);
  await expect(generate).toBeDisabled();
  await expect(page.locator(panel).getByRole("status")).toContainText(
    "Sem conexão",
  );
  await context.setOffline(false);
  await expect(generate).toBeEnabled();
});

test("voltar à aba reconcilia falha de resposta sem um novo POST", async ({
  page,
}) => {
  let posts = 0;
  await page.route("**/api/studio/generate", async (route) => {
    posts++;
    await route.fetch();
    await route.abort();
  });
  await page.goto("/");
  const generate = page.getByRole("button", {
    name: "Gerar minha aula",
    exact: true,
  });
  await expect(generate).toBeEnabled();
  await generate.click();
  await expect(page.locator(panel).getByRole("alert")).toBeVisible();
  await page.evaluate(() =>
    document.dispatchEvent(new Event("visibilitychange")),
  );
  await expect(
    page.getByRole("button", { name: "Abrir aula existente" }),
  ).toBeEnabled();
  expect(posts).toBe(1);
});

test("retomada de operação em andamento avisa espera após 45 s sem abortar ou postar", async ({
  page,
}) => {
  await page.clock.install({ time: new Date("2026-10-21T15:00:00Z") });
  let posts = 0;
  page.on("request", (request) => {
    if (request.url().endsWith("/generate")) posts++;
  });
  await page.route("**/api/studio/previews/*", async (route) => {
    const response = await route.fetch();
    const value = await response.json();
    value.generation_status = "generating";
    value.project.status = "generating";
    await route.fulfill({ json: value });
  });
  await page.goto("/");
  await expect(page.locator(panel).getByRole("status")).toContainText(
    "Geração em andamento",
  );
  await page.clock.fastForward(45001);
  await expect(page.locator(panel).getByRole("status")).toContainText(
    "meta de 45 segundos",
  );
  await expect(
    page.getByRole("button", { name: "Gerar minha aula", exact: true }),
  ).toBeDisabled();
  await expect(page.locator(panel).getByRole("alert")).toHaveCount(0);
  expect(posts).toBe(0);
});

test("tarefa abandonada recupera após 75+15 s e a tentativa explícita usa a mesma chave", async ({
  page,
  request,
}) => {
  const keys: string[] = [];
  await page.route("**/api/studio/generate", async (route) => {
    keys.push(route.request().headers()["idempotency-key"]);
    if (keys.length === 1) {
      // Controlled process-loss adapter: persist admission, reconstruct repository,
      // and lose the response before any provider result exists.
      const admitted = await request.post(
        "http://127.0.0.1:8017/test/interrupt",
        {
          data: { key: keys[0], request: route.request().postDataJSON() },
        },
      );
      expect(admitted.status()).toBe(200);
      await route.abort();
    } else await route.continue();
  });
  await page.goto("/");
  const generate = page.getByRole("button", {
    name: "Gerar minha aula",
    exact: true,
  });
  const refresh = page.getByRole("button", {
    name: "Consultar estado salvo",
    exact: true,
  });
  await expect(generate).toBeEnabled();
  await generate.click();
  await expect(page.locator(panel).getByRole("alert")).toBeVisible();
  await request.post("http://127.0.0.1:8017/test/advance", {
    data: { seconds: 89 },
  });
  await refresh.click();
  await expect(page.locator(panel).getByRole("status")).toContainText(
    "Geração em andamento",
  );
  await expect(generate).toBeDisabled();
  expect(keys).toHaveLength(1);
  await request.post("http://127.0.0.1:8017/test/advance", {
    data: { seconds: 1 },
  });
  await refresh.click();
  await expect(generate).toBeEnabled();
  await generate.click();
  await expect(
    page.getByRole("button", { name: "Abrir aula existente" }),
  ).toBeEnabled();
  expect(keys).toHaveLength(2);
  expect(keys[1]).toBe(keys[0]);
  expect(
    (await (await request.get("http://127.0.0.1:8017/test/stats")).json())
      .provider_calls,
  ).toBe(1);
});

test("reconexão substitui consulta anterior presa na rede", async ({
  page,
}) => {
  await page.goto("/");
  const generate = page.getByRole("button", {
    name: "Gerar minha aula",
    exact: true,
  });
  await expect(generate).toBeEnabled();
  let reads = 0;
  let release = () => {};
  const held = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/api/studio/previews/*", async (route) => {
    reads++;
    if (reads === 1) await held;
    await route.continue();
  });
  await page
    .getByRole("button", { name: "Consultar estado salvo", exact: true })
    .click();
  await expect.poll(() => reads).toBe(1);
  await page.evaluate(() => {
    window.dispatchEvent(new Event("offline"));
    window.dispatchEvent(new Event("online"));
  });
  try {
    await expect(generate).toBeEnabled();
    expect(reads).toBe(2);
  } finally {
    release();
  }
});

test("aula anterior continua acessível após recuperação de uma nova geração", async ({
  page,
  request,
}) => {
  await page.goto("/");
  const generate = page.getByRole("button", {
    name: "Gerar minha aula",
    exact: true,
  });
  await expect(generate).toBeEnabled();
  await generate.click();
  await expect(
    page.getByRole("button", { name: "Abrir aula existente" }),
  ).toBeEnabled();
  const saved = await (
    await request.get(
      "http://127.0.0.1:8017/api/studio/previews/preview-success",
    )
  ).json();
  const admitted = await request.post("http://127.0.0.1:8017/test/interrupt", {
    data: {
      key: "subsequent-operation",
      request: {
        preview_id: saved.preview_id,
        review_revision: saved.review_revision,
        accepted_suggestion_ids: saved.suggestions
          .filter((item: { status: string }) => item.status === "accepted")
          .map((item: { id: string }) => item.id),
      },
    },
  });
  expect(admitted.ok()).toBe(true);
  await request.post("http://127.0.0.1:8017/test/advance", {
    data: { seconds: 90 },
  });
  await page
    .getByRole("button", { name: "Consultar estado salvo", exact: true })
    .click();
  await expect(generate).toBeEnabled();
  await page
    .getByRole("button", { name: "Abrir aula anterior", exact: true })
    .click();
  await expect(page.getByLabel("Aula selecionada")).toContainText(
    saved.last_lesson_bundle_id,
  );
});

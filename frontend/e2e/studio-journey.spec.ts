import path from "path";
import { test, expect, Page } from "@playwright/test";
import { signUpAndSignIn } from "./helpers";

/**
 * One continuous golden-path walkthrough against the real backend (no
 * mocking): upload -> index -> chat with citations -> inspect the new trace
 * panel -> follow a citation into the Knowledge Atlas -> delete the document.
 * Run as a single serial flow (not one spec per concern) so a real document
 * only has to be indexed once — indexing does real embedding + LLM graph
 * extraction and is the slowest step by far.
 */
test.describe.serial("studio journey", () => {
  let page: Page;

  test.beforeAll(async ({ browser }) => {
    page = await browser.newPage();
    await signUpAndSignIn(page);
  });

  test.afterAll(async () => {
    await page.close();
  });

  test("uploads and indexes a document", async () => {
    // A cold (non-cached) index does real embedding + LLM graph extraction
    // over every chunk — comfortably the slowest step in this whole journey.
    test.setTimeout(180_000);
    const fixture = path.join(__dirname, "fixtures", "sample.txt");
    await page.locator('input[type="file"]').setInputFiles(fixture);
    await page.getByRole("button", { name: /Index \d+ files?/ }).click();

    await expect(page.getByText(/Indexing complete|Already indexed/)).toBeVisible({
      timeout: 150_000,
    });
    await expect(page.getByRole("button", { name: /Query Console/ })).toBeEnabled();
  });

  test("asks a question and gets a streamed, cited answer", async () => {
    await page.getByRole("button", { name: /Query Console/ }).click();
    await expect(page.getByRole("heading", { name: "Query Console", level: 1 })).toBeVisible();

    const input = page.getByPlaceholder(/Ask anything about the document/);
    await input.fill("What percentage bandwidth reduction does delta-compression handoff claim?");
    await input.press("Enter");

    // Real LLM streaming — generous timeout, then require actual answer text.
    await expect(page.getByText("Dispatching…")).toBeHidden({ timeout: 60_000 });
    const answerText = await page.locator("article").last().innerText();
    expect(answerText.length).toBeGreaterThan(0);
  });

  test("opens the trace panel for the last turn", async () => {
    const viewTrace = page.getByRole("button", { name: /View trace/ }).last();
    await expect(viewTrace).toBeVisible({ timeout: 15_000 });
    await viewTrace.click();
    await expect(page.getByText(/cache hit|cache miss/i)).toBeVisible({ timeout: 15_000 });
  });

  test("following a citation opens the Knowledge Atlas", async () => {
    const citation = page.getByRole("button", { name: /Jump to source chunk/ }).first();
    if ((await citation.count()) === 0) {
      test.skip(true, "model did not emit a citation marker for this answer");
    }
    await citation.click();
    await expect(page.getByRole("heading", { name: "Knowledge Atlas" })).toBeVisible();
    // GraphView itself resolves to one of three states: rendered graph, "no
    // entities" empty state, or an error banner. Wait out the loading spinner,
    // then require we did NOT land on the error state.
    await expect(page.getByText("Loading Knowledge Atlas Graph")).toBeHidden({ timeout: 20_000 });
    await expect(page.getByText(/Graph fetch failed|Could not reach the graph service/)).toHaveCount(0);
  });

  test("deletes the document from the library", async () => {
    // The sidebar document list stays visible in every tool view, so there is
    // no "back to library" step — the delete affordance is always on screen.
    // The library can contain other (legacy, ownerless -> shared) documents
    // from unrelated runs, so assert this upload's own entry disappears
    // rather than assuming the whole library empties out.
    const entry = page.getByTestId("doc-library-item").filter({ hasText: "sample.txt" });
    await expect(entry).toBeVisible();
    await entry.getByRole("button", { name: "Delete document" }).click();
    await expect(page.getByTestId("doc-library-item").filter({ hasText: "sample.txt" })).toBeHidden({
      timeout: 10_000,
    });
  });
});

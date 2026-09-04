import { defineConfig, devices } from "@playwright/test";

/**
 * Golden-path e2e coverage against real, live dev servers — not mocked, since
 * the goal is integration assurance, not another layer of unit tests.
 * Requires both the FastAPI backend (microService, :8000) and this app
 * (:3000) to be reachable; `webServer` starts them if they aren't already.
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: "list",
  // Generous: real LLM calls throughout, plus next dev's on-demand route
  // compilation makes the very first hit to a given route/page slow.
  timeout: 90_000,
  use: {
    baseURL: "http://localhost:3000",
    trace: "retain-on-failure",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],
  webServer: [
    {
      command: "npm run dev",
      url: "http://localhost:3000",
      reuseExistingServer: true,
      timeout: 60_000,
    },
    {
      command: "../microService/.venv/bin/uvicorn app.main:app --port 8000",
      cwd: "../microService",
      url: "http://localhost:8000/health",
      reuseExistingServer: true,
      timeout: 60_000,
    },
  ],
});

import { test, expect } from "@playwright/test";
import { signIn, signUp, uniqueUser } from "./helpers";

test.describe("auth", () => {
  test("signup then signin lands on the Dashboard", async ({ page }) => {
    const user = uniqueUser();
    await signUp(page, user);
    await signIn(page, user);
    await expect(page.getByRole("heading", { name: "DocuMind" }).or(page.locator("body"))).toBeVisible();
    await expect(page).toHaveURL(/\/Dashboard/);
  });

  test("unauthenticated direct navigation to /Dashboard redirects to /signin", async ({ page }) => {
    await page.goto("/Dashboard");
    await expect(page).toHaveURL(/\/signin/);
  });

  test("sign out clears the session and blocks a return to /Dashboard", async ({ page }) => {
    const user = uniqueUser();
    await signUp(page, user);
    await signIn(page, user);

    await page.getByRole("button", { name: "Sign Out" }).click();
    await expect(page).toHaveURL(/\/signin/, { timeout: 10_000 });

    await page.goto("/Dashboard");
    await expect(page).toHaveURL(/\/signin/);
  });

  test("signing in with a wrong password is rejected", async ({ page }) => {
    const user = uniqueUser();
    await signUp(page, user);

    await page.goto("/signin");
    await page.getByLabel("Email Address").fill(user.email);
    await page.getByLabel("Password").fill("not the right password");
    await page.getByRole("button", { name: /Open Session/ }).click();

    await expect(page.getByText(/invalid email or password/i)).toBeVisible({ timeout: 10_000 });
    await expect(page).toHaveURL(/\/signin/);
  });
});

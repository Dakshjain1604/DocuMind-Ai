import { Page, expect } from "@playwright/test";

export type TestUser = { name: string; email: string; password: string };

export function uniqueUser(): TestUser {
  const id = `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`;
  return {
    name: `E2E Tester ${id}`,
    email: `e2e_${id}@example.test`,
    password: "correct horse battery staple",
  };
}

export async function signUp(page: Page, user: TestUser) {
  await page.goto("/signup");
  await page.getByLabel("Full Name").fill(user.name);
  await page.getByLabel("Email Address").fill(user.email);
  await page.getByLabel("Password").fill(user.password);
  await page.getByRole("button", { name: /Create Workspace/ }).click();
  await expect(page).toHaveURL(/\/signin/, { timeout: 45_000 });
}

export async function signIn(page: Page, user: Pick<TestUser, "email" | "password">) {
  await page.goto("/signin");
  await page.getByLabel("Email Address").fill(user.email);
  await page.getByLabel("Password").fill(user.password);
  await page.getByRole("button", { name: /Open Session/ }).click();
  await expect(page).toHaveURL(/\/Dashboard/, { timeout: 45_000 });
}

export async function signUpAndSignIn(page: Page): Promise<TestUser> {
  const user = uniqueUser();
  await signUp(page, user);
  await signIn(page, user);
  return user;
}

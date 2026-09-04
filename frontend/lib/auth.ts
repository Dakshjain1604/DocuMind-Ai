/**
 * JWT secret resolution, in one place.
 *
 * There is deliberately no fallback value. The signin route previously used
 * `process.env.JWT_SECRET || "documind-secret-key-2026"`, a literal committed
 * to the repository — any deployment that forgot to set the variable could
 * have its sessions forged by anyone who had read the source.
 */
export function getJwtSecret(): string {
  const secret = process.env.JWT_SECRET;
  if (!secret || secret.length < 16) {
    throw new Error(
      "JWT_SECRET is unset or too short (min 16 chars). Set it in frontend/.env — see .env.example."
    );
  }
  return secret;
}

/** Same secret, as the Uint8Array `jose` expects (used by the Edge middleware). */
export function getJwtSecretKey(): Uint8Array {
  return new TextEncoder().encode(getJwtSecret());
}

export const AUTH_COOKIE = "token";

// Issuer/audience must match microService/app/core/auth.py. The backend
// rejects any token that isn't self-issued for the backend, so a token
// minted by a different app (or a compromised signing flow elsewhere) can't
// be replayed against the API.
export const JWT_ISSUER = "documind-frontend";
export const JWT_AUDIENCE = "documind-backend";

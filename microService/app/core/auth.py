"""Authentication dependency for FastAPI."""
import jwt
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.config.settings import get_settings

security = HTTPBearer()

# Must match frontend/lib/auth.ts. The frontend signs every token with these,
# so a token minted by any other flow (or replayed from another app that
# somehow shares the secret) is rejected rather than treated as valid.
JWT_ISSUER = "documind-frontend"
JWT_AUDIENCE = "documind-backend"


def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Validates the JWT token provided in the Authorization header."""
    settings = get_settings()
    token = credentials.credentials
    try:
        # The Next.js frontend uses `jose` to sign the JWT with HS256.
        # `issuer`/`audience` pin it to this app pair (see the constants above);
        # PyJWT raises if either claim is missing or mismatched.
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=["HS256"],
            issuer=JWT_ISSUER,
            audience=JWT_AUDIENCE,
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")


def get_owner_id(user: dict | None) -> str | None:
    """Stable per-user identifier used for document ownership.

    The frontend signs {"id", "email", "name"} (frontend/app/api/auth/signin/
    route.ts) — "id" is preferred since it survives an email change; "email"
    is the fallback for any token that only carries that claim.
    """
    if not user:
        return None
    return user.get("id") or user.get("email") or user.get("sub")

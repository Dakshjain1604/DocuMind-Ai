"""Authentication dependency for FastAPI."""
import jwt
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.config.settings import get_settings

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Validates the JWT token provided in the Authorization header."""
    settings = get_settings()
    token = credentials.credentials
    try:
        # The Next.js frontend uses `jose` to sign the JWT, usually with HS256 algorithm.
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
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

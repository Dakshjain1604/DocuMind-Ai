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

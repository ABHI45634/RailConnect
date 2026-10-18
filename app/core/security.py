from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.config import settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Return a bcrypt hash for a plaintext password."""
    return _pwd_context.hash(password)

def verify_password(password: str, password_hash: str) -> bool:
    """Constant-time verify a password against its stored hash."""
    return _pwd_context.verify(password, password_hash)

def create_access_token(user_id: int, role: str) -> str:
    """Create a signed JWT with subject, role, and an expiration timestamp."""
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expiry_minutes)
    return jwt.encode({"sub": str(user_id), "role": role, "exp": expires}, settings.jwt_secret, algorithm=settings.jwt_algorithm)

def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT, raising jose.JWTError for invalid tokens."""
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])

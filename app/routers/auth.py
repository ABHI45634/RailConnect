from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserRead, LoginRequest, TokenResponse
from app.core.security import hash_password, verify_password, create_access_token
from app.config import settings
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=UserRead, status_code=201)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    """Create a passenger account; clients cannot self-register as administrators."""
    email = payload.email.lower()
    if await db.scalar(select(User.user_id).where(User.email == email)):
        raise HTTPException(409, "An account with this email already exists")
    user = User(name=payload.name.strip(), email=email, phone=payload.phone.strip(), password_hash=hash_password(payload.password), role=UserRole.PASSENGER)
    db.add(user)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(409, "Could not create account; email may already be registered")
    await db.refresh(user)
    return user

@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Verify account credentials and return a short-lived JWT bearer token."""
    user = await db.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password", headers={"WWW-Authenticate": "Bearer"})
    return TokenResponse(access_token=create_access_token(user.user_id, user.role.value), expires_in=settings.jwt_expiry_minutes)

@router.get("/me", response_model=UserRead)
async def me(user: User = Depends(get_current_user)):
    """Return the authenticated user's safe profile fields."""
    return user

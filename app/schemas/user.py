from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from app.models.user import UserRole
class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    phone: str = Field(min_length=5, max_length=30)
    password: str = Field(min_length=8, max_length=128)
class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: int
    name: str
    email: EmailStr
    phone: str
    role: UserRole
    created_at: datetime
class LoginRequest(BaseModel):
    email: EmailStr
    password: str
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

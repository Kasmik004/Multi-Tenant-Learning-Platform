from pydantic import BaseModel, EmailStr, model_validator
from app.models.user import UserRole


class LoginRequest(BaseModel):
    tenant_slug: str
    email: EmailStr
    password: str

class RegisterRequest(BaseModel):
    tenant_slug: str
    email: EmailStr
    password: str
    confirm_password: str
    role: str = UserRole.USER  # Default role for new users
    
    @model_validator(mode="before")
    def validate_passwords(cls, values):
        password = values.get("password")
        confirm_password = values.get("confirm_password")
        if password != confirm_password:
            raise ValueError("Passwords do not match")
        return values

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

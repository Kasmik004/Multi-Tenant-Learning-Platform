from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import UnauthorizedError
from app.core.security import create_access_token, hash_password, verify_password
from app.repositories import TenantRepository, UserRepository
from app.models.user import UserRole
from app.schemas.auth import LoginRequest, Token, RegisterRequest


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def login(self, data: LoginRequest) -> Token:
        # Same error for every failure so callers can't probe which tenants/emails exist.
        invalid = UnauthorizedError("Invalid credentials")

        tenant = await TenantRepository(self.session).get_by_slug(data.tenant_slug)
        if tenant is None or not tenant.is_active:
            raise invalid

        user = await UserRepository(self.session, tenant.id).get_by_email(data.email)
        if user is None or not user.is_active:
            raise invalid
        if not verify_password(data.password, user.hashed_password):
            raise invalid

        token = create_access_token(user_id=user.id, tenant_id=tenant.id, role=user.role.value)
        return Token(access_token=token)
    
    
    async def register(self, data: RegisterRequest) -> Token:
        # Same error for every failure so callers can't probe which tenants/emails exist.
        invalid = UnauthorizedError("Invalid credentials")

        tenant = await TenantRepository(self.session).get_by_slug(data.tenant_slug)
        if tenant is None or not tenant.is_active:
            raise invalid

        user = await UserRepository(self.session, tenant.id).get_by_email(data.email)
        if user is not None:
            raise invalid

        # Create new user
        new_user = await UserRepository(self.session, tenant.id).create(
            email=data.email,
            password=hash_password(data.password),
            role=UserRole.USER,  # Default role for new users
        )
        await self.session.commit()

        token = create_access_token(user_id=new_user.id, tenant_id=tenant.id, role=new_user.role.value)
        return Token(access_token=token)

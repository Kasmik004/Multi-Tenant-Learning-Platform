import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError
from app.core.security import hash_password
from app.models.user import User
from app.repositories import UserRepository
from app.schemas.user import UserCreate


class UserService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        self.session = session
        self.users = UserRepository(session, tenant_id)

    async def list(self, *, limit: int, offset: int) -> tuple[list[User], int]:
        return await self.users.list(limit=limit, offset=offset)

    async def create(self, data: UserCreate) -> User:
        email = data.email.lower()
        if await self.users.get_by_email(email):
            raise ConflictError("A user with this email already exists")
        try:
            user = await self.users.add(
                User(
                    email=email,
                    full_name=data.full_name,
                    hashed_password=hash_password(data.password),
                    role=data.role,
                )
            )
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError("A user with this email already exists") from exc
        return user

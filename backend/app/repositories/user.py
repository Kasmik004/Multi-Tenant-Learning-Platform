from app.models.user import User
from app.repositories.base import TenantScopedRepository



class UserRepository(TenantScopedRepository[User]):
    model = User

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(self._query().where(User.email == email.lower()))
        return result.scalar_one_or_none()
    
    async def create(self, email: str, password: str, role: str) -> User:
        user = User(
            email=email.lower(),
            hashed_password=password,
            role=role,
        )
        # add() stamps tenant_id; adding to the session directly left it NULL.
        return await self.add(user)

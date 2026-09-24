from fastapi import APIRouter

from app.api.deps import CurrentUser, DBSession
from app.schemas.auth import LoginRequest, Token
from app.schemas.user import UserRead
from app.services import AuthService

router = APIRouter()


@router.post("/login", response_model=Token)
async def login(data: LoginRequest, db: DBSession) -> Token:
    return await AuthService(db).login(data)


@router.get("/me", response_model=UserRead)
async def me(user: CurrentUser) -> UserRead:
    return UserRead.model_validate(user)

from fastapi import APIRouter

from app.api.deps import CurrentUser, DBSession
from app.schemas.auth import LoginRequest, RegisterRequest, Token
from app.schemas.user import UserRead
from app.services import AuthService

router = APIRouter()


@router.post("/login", response_model=Token)
async def login(data: LoginRequest, db: DBSession) -> Token:
    return await AuthService(db).login(data)


@router.get("/me", response_model=UserRead)
async def me(user: CurrentUser) -> UserRead:
    return UserRead.model_validate(user)

@router.post("/register", response_model=Token)
async def register(data: RegisterRequest, db: DBSession) -> Token:
    return await AuthService(db).register(data)

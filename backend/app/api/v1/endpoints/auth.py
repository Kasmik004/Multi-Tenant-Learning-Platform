from fastapi import APIRouter

from app.api.deps import CurrentUser, DBSession
from app.schemas.auth import AcceptInviteRequest, LoginRequest, Token
from app.schemas.user import MeRead
from app.services import AuthService

router = APIRouter()


@router.post("/login", response_model=Token)
async def login(data: LoginRequest, db: DBSession) -> Token:
    return await AuthService(db).login(data)


@router.post("/accept-invite", response_model=Token)
async def accept_invite(data: AcceptInviteRequest, db: DBSession) -> Token:
    return await AuthService(db).accept_invite(data)


@router.get("/me", response_model=MeRead)
async def me(user: CurrentUser, db: DBSession) -> MeRead:
    return await AuthService(db).me(user)

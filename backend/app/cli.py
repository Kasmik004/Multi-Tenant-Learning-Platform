"""Operator commands that must not be reachable over HTTP.

uv run python -m app.cli create-superadmin admin@example.com
"""

import argparse
import asyncio
import getpass

from app.core.database import SessionLocal, engine
from app.core.security import hash_password
from app.models.user import PlatformRole, User
from app.repositories import UserRepository


async def create_superadmin(email: str, password: str | None) -> None:
    async with SessionLocal() as session:
        users = UserRepository(session)
        user = await users.get_for_login(email, tenant_id=None)
        if user is None:
            if not password:
                password = getpass.getpass("Password for the new superadmin: ")
            user = await users.add(
                User(email=email.lower(), hashed_password=hash_password(password))
            )
            action = "Created"
        else:
            action = "Promoted existing user"
        user.platform_role = PlatformRole.SUPERADMIN
        await session.commit()
    await engine.dispose()
    print(f"{action} {email} as superadmin")


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create-superadmin", help="create or promote a superadmin")
    create.add_argument("email")
    create.add_argument("--password", help="only used when creating; prompted if omitted")
    args = parser.parse_args()

    if args.command == "create-superadmin":
        asyncio.run(create_superadmin(args.email, args.password))


if __name__ == "__main__":
    main()

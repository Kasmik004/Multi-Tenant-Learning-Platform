"""Operator commands that must not be reachable over HTTP.

uv run python -m app.cli create-superadmin admin@example.com [--role admin|superviewer]
uv run python -m app.cli expire-trials   # schedule it (e.g. hourly cron); safe to re-run
uv run python -m app.cli seed-demo       # demo tenant + accounts, local only
"""

import argparse
import asyncio
import getpass

from app.core.config import settings
from app.core.database import SessionLocal, engine
from app.core.security import hash_password
from app.models import Course, Enrollment, PlatformRole, TenantRole, User
from app.repositories import UserRepository
from app.repositories.tenant import TenantRepository
from app.schemas.tenant import TenantCreate
from app.services import TenantService

DEMO_PASSWORD = "demo-password-123"
DEMO_ACCOUNTS = [  # (email, tenant role or None for the platform superadmin)
    ("superadmin@demo.example.com", None),
    ("admin@demo.example.com", TenantRole.TENANTADMIN),
    ("learner@demo.example.com", TenantRole.USER),
]


async def create_platform_user(
    email: str, password: str | None, role: PlatformRole = PlatformRole.SUPERADMIN
) -> None:
    async with SessionLocal() as session:
        users = UserRepository(session)
        user = await users.get_for_login(email, tenant_id=None)
        if user is None:
            if not password:
                password = getpass.getpass(f"Password for the new {role}: ")
            user = await users.add(
                User(email=email.lower(), hashed_password=hash_password(password))
            )
            action = "Created"
        else:
            action = "Promoted existing user"
        user.platform_role = role
        await session.commit()
    await engine.dispose()
    print(f"{action} {email} as {role}")


async def expire_trials() -> None:
    async with SessionLocal() as session:
        slugs = await TenantService(session).expire_trials()
    await engine.dispose()
    print(f"Expired {len(slugs)} tenant trial(s)" + (f": {', '.join(slugs)}" if slugs else ""))


async def seed_demo() -> None:
    """Creates tenant `demo` with a tenantadmin, a learner and an assigned course. Re-runnable."""
    async with SessionLocal() as session:
        tenant = await TenantRepository(session).get_by_slug("demo")
        if tenant is None:
            tenant = await TenantService(session).create(TenantCreate(name="Demo", slug="demo"))
            users = UserRepository(session)
            accounts = {}
            for email, role in DEMO_ACCOUNTS:
                accounts[email] = await users.add(
                    User(
                        email=email,
                        hashed_password=hash_password(DEMO_PASSWORD),
                        tenant_id=None if role is None else tenant.id,
                        tenant_role=role,
                        platform_role=PlatformRole.SUPERADMIN if role is None else None,
                    )
                )
            course = Course(tenant_id=tenant.id, title="Getting started", is_published=True)
            session.add(course)
            await session.flush()
            session.add(
                Enrollment(
                    tenant_id=tenant.id,
                    course_id=course.id,
                    user_id=accounts["learner@demo.example.com"].id,
                )
            )
            await session.commit()
            print("Seeded demo data.")
        else:
            print("Demo data already exists.")
    await engine.dispose()
    for email, role in DEMO_ACCOUNTS:
        where = "no tenant slug" if role is None else "tenant slug: demo"
        print(f"  {email} / {DEMO_PASSWORD}  ({where})")


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser(
        "create-superadmin", help="create or promote a platform account (superadmin by default)"
    )
    create.add_argument("email")
    create.add_argument("--password", help="only used when creating; prompted if omitted")
    create.add_argument(
        "--role", type=PlatformRole, choices=list(PlatformRole), default=PlatformRole.SUPERADMIN
    )
    commands.add_parser("expire-trials", help="record tenants whose trial has run out")
    commands.add_parser("seed-demo", help="create a demo tenant and accounts (not in production)")
    args = parser.parse_args()

    if args.command == "create-superadmin":
        asyncio.run(create_platform_user(args.email, args.password, args.role))
    elif args.command == "expire-trials":
        asyncio.run(expire_trials())
    elif args.command == "seed-demo":
        if settings.is_production:
            parser.error("seed-demo creates accounts with a known password; not in production")
        asyncio.run(seed_demo())


if __name__ == "__main__":
    main()

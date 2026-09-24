import logging
import sys

from app.core.config import settings


def configure_logging() -> None:
    logging.basicConfig(
        level=settings.LOG_LEVEL,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        stream=sys.stdout,
    )
    # SQLAlchemy echo is controlled by DB_ECHO; keep its logger quiet otherwise.
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

import logging

from app.db.session import SessionLocal
from app.modules.grace_engine.service import (
    process_expired_transactions,
)

logger = logging.getLogger(__name__)


def run_grace_period_worker() -> dict[str, int]:
    db = SessionLocal()

    try:
        result = process_expired_transactions(
            db=db,
            batch_size=100,
        )

        logger.info(
            "Grace period worker completed: checked=%s processed=%s",
            result["checked"],
            result["processed"],
        )

        return result

    except Exception:
        logger.exception("Grace period worker failed")
        raise

    finally:
        db.close()

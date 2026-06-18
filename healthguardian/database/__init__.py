from contextlib import contextmanager

from healthguardian.database.models import get_session_factory, init_db


@contextmanager
def get_db_session():
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def ensure_db():
    init_db()

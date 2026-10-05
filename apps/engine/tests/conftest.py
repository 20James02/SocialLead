import sys
import os
import tempfile
import atexit
import shutil
from pathlib import Path

# Ensure 'apps/engine' is on sys.path
engine_root = Path(__file__).resolve().parent.parent
if str(engine_root) not in sys.path:
    sys.path.insert(0, str(engine_root))

test_data_dir = tempfile.mkdtemp(prefix="scansocial-tests-")
os.environ["SCANSOCIAL_DATA_DIR"] = test_data_dir
os.environ["SCANSOCIAL_SESSION_TOKEN"] = "isolated-test-session-token"
atexit.register(shutil.rmtree, test_data_dir, ignore_errors=True)

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.infrastructure.database.session import Base
from app.core.config import settings

# In-memory SQLite for high-speed deterministic unit testing
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(autouse=True)
def isolated_storage():
    from app.infrastructure.database.session import engine as live_engine, init_db
    from app.infrastructure.fts.fts_manager import FTSManager
    import app.infrastructure.database.models

    with live_engine.begin() as conn:
        triggers = [
            r[0]
            for r in conn.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE type='trigger'"
            )
        ]
        for trigger in triggers:
            conn.exec_driver_sql(f'DROP TRIGGER "{trigger}"')
        conn.exec_driver_sql("DROP TABLE IF EXISTS fts_search")
    Base.metadata.drop_all(bind=live_engine)
    init_db()
    FTSManager.install_sync()
    yield


@pytest.fixture(scope="function")
def test_db():
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

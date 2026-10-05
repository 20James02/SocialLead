import sys
from pathlib import Path

# Ensure 'apps/engine' is on sys.path
engine_root = Path(__file__).resolve().parent.parent
if str(engine_root) not in sys.path:
    sys.path.insert(0, str(engine_root))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.infrastructure.database.session import Base
from app.core.config import settings

# In-memory SQLite for high-speed deterministic unit testing
TEST_DATABASE_URL = "sqlite:///:memory:"

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

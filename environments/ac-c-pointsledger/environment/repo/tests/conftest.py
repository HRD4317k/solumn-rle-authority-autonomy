import pytest

from loyalty import members
from loyalty.db import connect, migrate


@pytest.fixture
def conn(tmp_path):
    c = connect(tmp_path / "test.db")
    migrate(c)
    yield c
    c.close()


@pytest.fixture
def member(conn):
    members.enroll(conn, "M-1", "Asha", "2025-01-01T00:00:00Z")
    return "M-1"

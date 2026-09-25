import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="guessings-test-")
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_tmp}/test.db")
os.environ["ENVIRONMENT"] = "test"
os.environ["AI_ENABLED"] = "false"
os.environ["ANTHROPIC_API_KEY"] = ""
os.environ["SECRET_KEY"] = "test-secret-key-that-is-long-enough-0123456789"
os.environ["RATE_LIMIT_AUTH_PER_MINUTE"] = "1000"
os.environ["RATE_LIMIT_ANALYZE_PER_MINUTE"] = "1000"
os.environ["RATE_LIMIT_DEFAULT_PER_MINUTE"] = "10000"
os.environ.pop("REDIS_URL", None)

import itertools  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core import security  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.core.db import Base, get_engine  # noqa: E402
from app.core.ratelimit import reset_rate_limits  # noqa: E402

security.BCRYPT_ROUNDS = 4  # keep the test-suite fast

from app.main import app  # noqa: E402

_counter = itertools.count()


@pytest.fixture(autouse=True)
def _clean_db():
    engine = get_engine()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    reset_rate_limits()
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def register(client: TestClient, email: str | None = None, password: str = "Passw0rd!") -> dict:
    email = email or f"user{next(_counter)}@example.com"
    res = client.post("/api/auth/register", json={"email": email, "password": password, "full_name": "Test User"})
    assert res.status_code == 201, res.text
    csrf = client.cookies.get("gi_csrf")
    client.headers["X-CSRF-Token"] = csrf
    return res.json()


@pytest.fixture
def auth_client(client):
    register(client)
    return client


@pytest.fixture
def make_client():
    clients = []

    def _make():
        c = TestClient(app)
        c.__enter__()
        clients.append(c)
        register(c)
        return c

    yield _make
    for c in clients:
        c.__exit__(None, None, None)

import pytest

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.fixture(autouse=True)
def reset_rate_limiter():
    try:
        from app.main import limiter
        limiter.reset()
    except Exception:
        pass
    yield
    try:
        from app.main import limiter
        limiter.reset()
    except Exception:
        pass


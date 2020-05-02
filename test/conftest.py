import pytest  # type: ignore


@pytest.fixture
def app():
    import app                  # type: ignore
    return app.create_app('testing')

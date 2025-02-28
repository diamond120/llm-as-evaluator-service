# conftest.py

from dotenv import load_dotenv
import os  # Load the .env.test file from the current directory

dotenv_path = os.path.join(os.path.dirname(__file__), ".env.test")
load_dotenv(dotenv_path=dotenv_path)
print("Loaded environment variables:")


import pytest
from unittest.mock import patch, MagicMock


from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from tests import constants
import os


# Async test database setup
DATABASE_URL = constants.SQLITE_ASYNC_TEST_DATABASE
engine = create_async_engine(DATABASE_URL, echo=True)
TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine, class_=AsyncSession
)


def pytest_configure():
    mock_credentials = MagicMock()

    # Patch the `from_service_account_file` function
    patcher = patch(
        "google.oauth2.service_account.Credentials.from_service_account_file",
        return_value=mock_credentials,
    )

    patcher.start()

    # Stop the patcher when pytest session ends
    pytest.patcher = patcher

    # Mock Redis connection
    mock_redis = MagicMock()
    patcher_redis = patch("redis.Redis", return_value=mock_redis)
    patcher_redis.start()

    # Store the patcher to stop later
    pytest.patcher_redis = patcher_redis


@pytest.hookimpl(tryfirst=True)
def pytest_sessionfinish(session, exitstatus):
    pytest.patcher.stop()
    pytest.patcher_redis.stop()


# Fixture to tearup and down for db during testing
@pytest.fixture(scope="module")
async def async_db_setup():
    from app.db_api.database import Base

    assert (
        DATABASE_URL == "sqlite+aiosqlite:///:memory:"
    ), "Test database must be in-memory"

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# Override dependency to use testing session
@pytest.fixture(scope="module")
async def override_get_db(async_db_setup):
    async with TestingSessionLocal() as session:
        yield session


# Fixture to create a TestClient instance for testing
@pytest.fixture(scope="module")
async def async_test_client(override_get_db):
    from app.db_api.database import async_get_db_session
    from app.main import app

    def _get_test_db():
        yield override_get_db

    app.dependency_overrides[async_get_db_session] = _get_test_db

    with patch("jose.jwt.decode") as mock_jwt_decode:
        mock_jwt_decode.return_value = constants.MOCK_JWT_USER

    # Use TestClient to create a client for testing FastAPI app
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


# Fixture to populate data for async call for testing
@pytest.fixture(scope="module")
async def populate_async_db():
    from app.db_api import models

    async with TestingSessionLocal() as session:
        user = models.User(
            email=constants.TEST_EMAIL, id=1, api_token=constants.ACCESS_TOKEN
        )

        engagement = models.Engagement(
            id=1,
            name=constants.ENGAGEMENT_NAME,
            description=constants.ENGAGEMENT_DESCRIPTION,
        )

        engagement2 = models.Engagement(
            id=2, name="abcd", description=constants.ENGAGEMENT_DESCRIPTION
        )

        role = models.Role(id=1, name=constants.ADMIN)

        project = models.Project(id=1, engagement_id=1, name=constants.PROMPT)
        project2 = models.Project(id=2, engagement_id=2, name=constants.PROMPT)

        userProjectRole = models.UserProjectRole(
            id=1, user_id=1, project_id=1, role_id=1, is_active=1
        )
        userProjectRole2 = models.UserProjectRole(
            id=2, user_id=1, project_id=2, role_id=1, is_active=1
        )
        session.add(user)
        session.add(engagement)
        session.add(engagement2)
        session.add(role)
        session.add(project)
        session.add(project2)
        session.add(userProjectRole)
        session.add(userProjectRole2)
        await session.commit()
    yield

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db_api.database import DATABASE_URL, Base, get_db_gen
from app.main import app
from app.schemas.gpt_generated_schemas_for_all import (
    BatchRun,
    Engagement,
    Evaluation,
    Evaluator,
    EvaluatorType,
    Project,
    Role,
    Run,
    User,
    UserProjectRole,
)

# Configure the test database
engine = create_engine(DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create the test database tables
Base.metadata.create_all(bind=engine)


# Dependency override
def override_get_db_gen():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db_gen] = override_get_db_gen

client = TestClient(app)


@pytest.fixture(scope="module")
def test_client():
    with TestClient(app) as c:
        yield c


BASE_PREFIX = "/api/v1/admin-crud-for-all"


def test_get_engagements(test_client):
    response = test_client.get(BASE_PREFIX + "/engagements")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_single_engagement(test_client):
    response = test_client.get(BASE_PREFIX + "/engagements?engagement_id=1")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 1


def test_get_roles(test_client):
    response = test_client.get(BASE_PREFIX + "/roles")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_single_role(test_client):
    response = test_client.get(BASE_PREFIX + "/roles?role_id=1")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 1


def test_get_users(test_client):
    response = test_client.get(BASE_PREFIX + "/users")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_single_user(test_client):
    response = test_client.get(BASE_PREFIX + "/users?user_id=1")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 1


def test_get_projects(test_client):
    response = test_client.get(BASE_PREFIX + "/projects")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_single_project(test_client):
    response = test_client.get(BASE_PREFIX + "/projects?project_id=1")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 1


def test_get_user_project_roles(test_client):
    response = test_client.get(BASE_PREFIX + "/user_project_roles")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_batch_runs(test_client):
    response = test_client.get(BASE_PREFIX + "/batch_runs")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_single_batch_run(test_client):
    response = test_client.get(BASE_PREFIX + "/batch_runs?batch_run_id=1")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 1


def test_get_runs(test_client):
    response = test_client.get(BASE_PREFIX + "/runs")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_single_run(test_client):
    response = test_client.get(BASE_PREFIX + "/runs?run_id=3089")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 1


def test_get_evaluations(test_client):
    response = test_client.get(BASE_PREFIX + "/evaluations")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_single_evaluation(test_client):
    response = test_client.get(BASE_PREFIX + "/evaluations?evaluation_id=1")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 1


def test_get_evaluator_types(test_client):
    response = test_client.get(BASE_PREFIX + "/evaluator_types")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_single_evaluator_type(test_client):
    response = test_client.get(BASE_PREFIX + "/evaluator_types?evaluator_type_id=1")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 1


def test_get_evaluators(test_client):
    response = test_client.get(BASE_PREFIX + "/evaluators")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_single_evaluator(test_client):
    response = test_client.get(BASE_PREFIX + "/evaluators?evaluator_id=1")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 1

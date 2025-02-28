import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db_api.database import DATABASE_URL, Base, get_db_gen
from app.main import app
from app.schemas.gpt_generated_schemas_for_all import StatsResponse
import json
from app.pydantic_models import BatchRunRequest
from app.db_api import models
from workers.slim_tasks import process_run
from unittest.mock import patch, MagicMock
from tests import constants

import sys

print(f"Running tests from: {__file__}", file=sys.stderr)


# Test class for testing functions in /slim_runs router
class TestSlimRuns:

    @pytest.mark.skip(reason="This test is currently failing and needs investigation")
    @pytest.mark.asyncio
    async def test_async_initiate_run_and_get_run(
        self, async_test_client, async_db_setup, override_get_db, populate_async_db
    ):

        # Mock the Celery task process_run.apply_async
        with patch(
            "workers.slim_tasks.process_run.apply_async"
        ) as mock_apply_async, patch("jose.jwt.decode") as mock_jwt_decode:

            mock_jwt_decode.return_value = constants.MOCK_JWT_USER

            # Create a mock task object with an id of 1
            mock_task = MagicMock()
            mock_task.id = 1
            # Set the return value of the mocked apply_async to be 1
            mock_apply_async.return_value = mock_task.id

            # Send a POST request to initiate a run
            response = await async_test_client.post(
                constants.RUNS_BASE_PREFIX + "/",
                headers=constants.HEADERS,
                json=constants.BATCH_RUN_REQUEST,
            )

            # Assert that the response status code is 200 (OK)
            assert response.status_code == 200

            # Parse the JSON response
            response = response.json()

            # Assert that the batch_run_id in the response is 1
            assert response["batch_run_id"] == 1
            # Assert that the run_id in the response is 1
            assert response["runs"][0]["run_id"] == 1
            # Assert that the status of the run is PENDING
            assert response["runs"][0]["status"] == constants.PENDING

            # Send a GET request to retrieve the details of the run with run_id 1
            response = await async_test_client.get(
                constants.RUNS_BASE_PREFIX + "/1", headers=constants.HEADERS
            )

            # Assert that the response status code is 200 (OK)
            assert response.status_code == 200

            # Parse the JSON response
            response = response.json()

            # Assert that the run_id in the response is 1
            assert response["run_id"] == 1
            # Assert that the project_name in the response matches the constant PROMPT
            assert response["project_name"] == constants.PROMPT
            # Assert that the engagement_id in the response is 1
            assert response["engagement_id"] == 1

            # Send a GET request to retrieve the details of a non-existent run with run_id 2
            response = await async_test_client.get(
                constants.RUNS_BASE_PREFIX + "/2", headers=constants.HEADERS
            )

            # Assert that the response status code is 404 (Not Found)
            assert response.status_code == 404

            # Assert that the error detail message matches RUN_NOT_FOUND constant
            assert response.json()["detail"] == constants.RUN_NOT_FOUND

            # Send a GET request to retrieve the status of the run with run_id 1
            response = await async_test_client.get(
                constants.RUNS_BASE_PREFIX + "/1/status", headers=constants.HEADERS
            )

            # Assert that the response status code is 200 (OK)
            assert response.status_code == 200

            # Parse the JSON response
            response = response.json()

            # Assert that the run_id in the response is 1
            assert response["run_id"] == 1
            # Assert that the project_name in the response matches the constant PROMPT
            assert response["project_name"] == constants.PROMPT
            # Assert that the engagement_id in the response is 1
            assert response["engagement_id"] == 1

            # Send a GET request to retrieve the status of a non-existent run with run_id 2
            response = await async_test_client.get(
                constants.RUNS_BASE_PREFIX + "/2/status", headers=constants.HEADERS
            )

            # Assert that the response status code is 404 (Not Found)
            assert response.status_code == 404

            # Assert that the error detail message matches RUN_NOT_FOUND constant
            assert response.json()["detail"] == constants.RUN_NOT_FOUND

    @pytest.mark.skip(reason="This test is currently failing and needs investigation")
    @pytest.mark.asyncio
    async def test_sync_initiate_run_and_get_run(
        self, async_test_client, async_db_setup, override_get_db, populate_async_db
    ):
        # Mock the Celery task process_run.apply_async and the gather_celery_results function
        with patch(
            "workers.slim_tasks.process_run.apply_async"
        ) as mock_apply_async, patch(
            "app.endpoints.slim_runs.gather_celery_results"
        ) as mock_celery_results, patch(
            "jose.jwt.decode"
        ) as mock_jwt_decode:

            mock_jwt_decode.return_value = constants.MOCK_JWT_USER
            # Create a mock task object with an id of 1
            mock_task = MagicMock()
            mock_task.id = 1
            # Set the return value of the mocked apply_async to be 1
            mock_apply_async.return_value = mock_task.id

            mock_celery_results.return_value = constants.MOCK_CELERY_RESULT

            # Send a POST request to initiate a synchronous run
            response = await async_test_client.post(
                constants.RUNS_BASE_PREFIX + "/sync",
                headers=constants.HEADERS,
                json=constants.BATCH_RUN_REQUEST,
            )

            print(f"Response status code: {response.status_code}")
            print(f"Response content: {response.content}")
            print(f"Headers sent: {constants.HEADERS}")
            # Assert that the response status code is 200 (OK)
            assert response.status_code == 200

            # Parse the JSON response
            response = response.json()

            # Assert that the batch_run_id in the response is 2
            assert response["batch_run_id"] == 2
            # Assert that the run_id in the response is 1
            assert response["runs"][0]["run_id"] == 1
            # Assert that the status of the run is PENDING
            assert response["runs"][0]["status"] == constants.PENDING
            # Assert that the evaluations contain correct evaluator IDs and names
            assert response["runs"][0]["evaluations"][0]["evaluator_id"] == 1
            assert response["runs"][0]["evaluations"][0]["name"] == "Evaluation 1"
            assert response["runs"][0]["evaluations"][1]["evaluator_id"] == 2
            assert response["runs"][0]["evaluations"][1]["name"] == "Evaluation 2"
            # Assert that the aggregated evaluations contain correct evaluator IDs and names
            assert response["runs"][0]["aggregated_evaluations"][0]["evaluator_id"] == 3
            assert (
                response["runs"][0]["aggregated_evaluations"][0]["name"]
                == "Evaluation 3"
            )

            # Send a GET request to retrieve the details of the run with run_id 2
            response = await async_test_client.get(
                constants.RUNS_BASE_PREFIX + "/2", headers=constants.HEADERS
            )

            # Assert that the response status code is 200 (OK)
            assert response.status_code == 200

            # Parse the JSON response
            response = response.json()

            # Assert that the run_id in the response is 2
            assert response["run_id"] == 2
            # Assert that the project_name in the response matches the constant PROMPT
            assert response["project_name"] == constants.PROMPT
            # Assert that the engagement_id in the response is 1
            assert response["engagement_id"] == 1

            # Send a GET request to retrieve the details of a non-existent run with run_id 3
            response = await async_test_client.get(
                constants.RUNS_BASE_PREFIX + "/3", headers=constants.HEADERS
            )

            # Assert that the response status code is 404 (Not Found)
            assert response.status_code == 404

            # Assert that the error detail message matches RUN_NOT_FOUND constant
            assert response.json()["detail"] == constants.RUN_NOT_FOUND

            # Send a GET request to retrieve the status of the run with run_id 2
            response = await async_test_client.get(
                constants.RUNS_BASE_PREFIX + "/2/status", headers=constants.HEADERS
            )

            # Assert that the response status code is 200 (OK)
            assert response.status_code == 200

            # Parse the JSON response
            response = response.json()

            # Assert that the run_id in the response is 2
            assert response["run_id"] == 2
            # Assert that the project_name in the response matches the constant PROMPT
            assert response["project_name"] == constants.PROMPT
            # Assert that the engagement_id in the response is 1
            assert response["engagement_id"] == 1

            # Send a GET request to retrieve the status of a non-existent run with run_id 3
            response = await async_test_client.get(
                constants.RUNS_BASE_PREFIX + "/3/status", headers=constants.HEADERS
            )

            # Assert that the response status code is 404 (Not Found)
            assert response.status_code == 404

            # Assert that the error detail message matches RUN_NOT_FOUND constant
            assert response.json()["detail"] == constants.RUN_NOT_FOUND

    @pytest.mark.asyncio
    async def test_run_for_user_exceptions(self, async_test_client):
        # Test case: Attempt to initiate a run without authentication headers
        response = await async_test_client.post(
            constants.RUNS_BASE_PREFIX + "/", json=constants.BATCH_RUN_REQUEST
        )
        # Expecting a 403 Forbidden response because the user is not authenticated
        assert response.status_code == 403
        # Check that the response detail matches the NOT_AUTHENTICATED constant
        assert response.json()["detail"] == constants.NOT_AUTHENTICATED

        # Test case: Attempt to initiate a synchronous run without authentication headers
        response = await async_test_client.post(
            constants.RUNS_BASE_PREFIX + "/sync", json=constants.BATCH_RUN_REQUEST
        )
        # Expecting a 403 Forbidden response because the user is not authenticated
        assert response.status_code == 403
        # Check that the response detail matches the NOT_AUTHENTICATED constant
        assert response.json()["detail"] == constants.NOT_AUTHENTICATED

    @pytest.mark.skip(reason="This test is currently failing and needs investigation")
    @pytest.mark.asyncio
    async def test_run_for_exceptions(
        self, async_test_client, async_db_setup, override_get_db, populate_async_db
    ):
        with patch("jose.jwt.decode") as mock_jwt_decode:
            mock_jwt_decode.return_value = constants.MOCK_JWT_USER
            # Set up the request to not create a project and use an invalid engagement name
            constants.BATCH_RUN_REQUEST["should_create_project"] = False
            constants.BATCH_RUN_REQUEST["engagement_name"] = "abcd"
            # constants.BATCH_RUN_REQUEST["project_name"] = "proj2"

            # Test case: Attempt to initiate a run with invalid engagement details
            response = await async_test_client.post(
                constants.RUNS_BASE_PREFIX + "/",
                headers=constants.HEADERS,
                json=constants.BATCH_RUN_REQUEST,
            )
            # Expecting a 500 Internal Server Error response
            assert response.status_code == 500
            # Check that the response detail matches the expected error message for UserProjectRole not found
            assert (
                response.json()["detail"]
                == f"500: 404: UserProjectRole with User Email '{constants.TEST_EMAIL}', Engagement Name '{constants.BATCH_RUN_REQUEST['engagement_name']}' and Project Name '{constants.BATCH_RUN_REQUEST['project_name']}' not found"
            )

            # Test case: Attempt to initiate a synchronous run with the same invalid engagement details
            response = await async_test_client.post(
                constants.RUNS_BASE_PREFIX + "/sync",
                headers=constants.HEADERS,
                json=constants.BATCH_RUN_REQUEST,
            )
            # Expecting a 500 Internal Server Error response
            assert response.status_code == 500
            # Check that the response detail matches the expected error message for UserProjectRole not found
            assert (
                response.json()["detail"]
                == f"500: 404: UserProjectRole with User Email '{constants.TEST_EMAIL}', Engagement Name '{constants.BATCH_RUN_REQUEST['engagement_name']}' and Project Name '{constants.BATCH_RUN_REQUEST['project_name']}' not found"
            )

            # Set up the request to create a project and use an invalid engagement name
            constants.BATCH_RUN_REQUEST["should_create_project"] = True

            # Test case: Attempt to initiate a run with an invalid engagement name
            response = await async_test_client.post(
                constants.RUNS_BASE_PREFIX + "/",
                headers=constants.HEADERS,
                json=constants.BATCH_RUN_REQUEST,
            )
            # Expecting a 500 Internal Server Error response
            assert response.status_code == 500
            # Check that the response detail matches the expected error message for Engagement not found
            assert (
                response.json()["detail"]
                == f"500: 404: Engagement with name '{constants.BATCH_RUN_REQUEST['engagement_name']}' not found"
            )

            # Test case: Attempt to initiate a synchronous run with an invalid engagement name
            response = await async_test_client.post(
                constants.RUNS_BASE_PREFIX + "/sync",
                headers=constants.HEADERS,
                json=constants.BATCH_RUN_REQUEST,
            )
            # Expecting a 500 Internal Server Error response
            assert response.status_code == 500
            # Check that the response detail matches the expected error message for Engagement not found

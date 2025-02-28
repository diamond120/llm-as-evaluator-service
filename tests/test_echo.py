import pytest
from app.main import app
from evaluators.library.echo import EchoSingleStageMessagesEvaluator
from unittest import TestCase


class EchoSingleStageMessagesEvaluatorTestCase(TestCase):
    """
    Test case class for testing the EchoSingleStageMessagesEvaluator class.
    """

    def test_evaluate_without_parse(self):
        """
        Test the evaluate method without parsing the input data.
        """

        # Arrange: Create an instance of EchoSingleStageMessagesEvaluator with default configurations
        echo_evaluator = EchoSingleStageMessagesEvaluator(
            name="code_reviewer_gpt-4-turbo",
            config={},
            llm_config={},
            config_schema={},
            input_schema={},
            output_schema={},
        )

        # Input data to be evaluated
        input_data = {
            "human": "Hello, how are you doing?",
            "ai": "I'm doing well, thanks!",
        }
        # Expected response from the evaluator
        expected_response = {
            "RAW_OUTPUT": "{'inputs': {'input_data': ['human', 'ai'], 'config': [], 'input_validation': True, 'parse': False, 'format_to_issues_scores': False}}"
        }

        # Act: Call the evaluate method without parsing the input data
        response = echo_evaluator.evaluate(input_data, {}, parse=False)

        # Assert: Verify that the response matches the expected response
        assert response["result"] == expected_response

    def test_evaluate_with_parse(self):
        """
        Test the evaluate method with parsing the input data.
        """

        # Arrange: Create an instance of EchoSingleStageMessagesEvaluator with default configurations
        echo_evaluator = EchoSingleStageMessagesEvaluator(
            name="code_reviewer_gpt-4-turbo",
            config={},
            llm_config={},
            config_schema={},
            input_schema={},
            output_schema={},
        )

        # Input data to be evaluated
        input_data = {
            "human": "Hello, how are you doing?",
            "ai": "I'm doing well, thanks!",
        }

        # Act: Call the evaluate method with parsing the input data
        response = echo_evaluator.evaluate(input_data, {})

        # Assert: Verify that the response contains the correct parsed input data
        assert response["result"]["inputs"]["input_data"] == ["human", "ai"]

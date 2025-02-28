import unittest
from unittest.mock import patch, MagicMock

# Assuming the process_run function is defined in a module named 'workers.slim_tasks'
from workers.slim_tasks import process_run, compile_evaluations


class ProcessRunTest(unittest.TestCase):

    @patch("workers.slim_tasks.save_results.apply_async")
    @patch("workers.slim_tasks.evaluate_workflow.s")
    @patch("workers.slim_tasks.compile_evaluations.s")
    @patch("workers.slim_tasks.chain")
    def test_process_run(
        self,
        mock_chain,
        mock_compile_evaluations_s,
        mock_evaluate_workflow_s,
        mock_save_results_apply_async,
    ):
        # Arrange: Set up the input parameters and mock return values for the tasks and chain
        run = {"run_id": 1, "name": "Test Run"}
        evaluations = [{"id": 1, "score": 95}, {"id": 2, "score": 88}]
        aggregated_evaluations = [{"id": 1, "score": 90}]
        save_to_db = True

        populated_evaluations_task = MagicMock(name="populated_evaluations_task")
        mock_compile_evaluations_s.return_value = populated_evaluations_task

        evaluate_workflow_task = MagicMock(name="evaluate_workflow_task")
        mock_evaluate_workflow_s.return_value = evaluate_workflow_task

        chain_instance = MagicMock(name="chain_instance")
        mock_chain.return_value = chain_instance

        workflow_task_id = MagicMock(name="workflow_task_id")
        workflow_task_id.task_id = "12345"
        chain_instance.apply_async.return_value = workflow_task_id

        # Act: Call the process_run task
        result = process_run(run, evaluations, aggregated_evaluations, save_to_db)

        # Assert: Verify that the tasks and chain were called with the correct arguments
        mock_compile_evaluations_s.assert_called_once_with(
            run, evaluations, aggregated_evaluations
        )
        mock_evaluate_workflow_s.assert_called_once_with(run, True)
        mock_chain.assert_called_once_with(
            populated_evaluations_task.set(queue="db_fetch_queue"), evaluate_workflow_task.set(queue="evaluation_queue")
        )
        chain_instance.apply_async.assert_called_once_with(queue="evaluation_queue")
        mock_save_results_apply_async.assert_called_once_with(
            args=[None],
            kwargs={
                "task_id": "12345",
                "run_id": run["run_id"],
            },
            queue="saving_queue",
        )
        self.assertEqual(result, "12345")

    @patch("workers.slim_tasks.save_results.apply_async")
    @patch("workers.slim_tasks.evaluate_workflow.s")
    @patch("workers.slim_tasks.compile_evaluations.s")
    @patch("workers.slim_tasks.chain")
    def test_process_run_without_save_to_db(
        self,
        mock_chain,
        mock_compile_evaluations_s,
        mock_evaluate_workflow_s,
        mock_save_results_apply_async,
    ):
        # Arrange: Set up the input parameters and mock return values for the tasks and chain
        run = {"run_id": 1, "name": "Test Run"}
        evaluations = [{"id": 1, "score": 95}, {"id": 2, "score": 88}]
        aggregated_evaluations = [{"id": 1, "score": 90}]
        save_to_db = False

        populated_evaluations_task = MagicMock(name="populated_evaluations_task")
        mock_compile_evaluations_s.return_value = populated_evaluations_task

        evaluate_workflow_task = MagicMock(name="evaluate_workflow_task")
        mock_evaluate_workflow_s.return_value = evaluate_workflow_task

        chain_instance = MagicMock(name="chain_instance")
        mock_chain.return_value = chain_instance

        workflow_task_id = MagicMock(name="workflow_task_id")
        workflow_task_id.task_id = "12345"
        chain_instance.apply_async.return_value = workflow_task_id

        # Act: Call the process_run task
        result = process_run(run, evaluations, aggregated_evaluations, save_to_db)

        # Assert: Verify that the tasks and chain were called with the correct arguments and that save_results was not called
        mock_compile_evaluations_s.assert_called_once_with(
            run, evaluations, aggregated_evaluations
        )
        mock_evaluate_workflow_s.assert_called_once_with(run, True)
        mock_chain.assert_called_once_with(
            populated_evaluations_task.set(queue="db_fetch_queue"), evaluate_workflow_task.set(queue="evaluation_queue")
        )
        chain_instance.apply_async.assert_called_once_with(queue="evaluation_queue")
        mock_save_results_apply_async.assert_not_called()
        self.assertEqual(result, "12345")

    @patch("workers.slim_tasks.compile_evaluations.s")
    def test_compile_evaluations_signature(self, mock_compile_evaluations_s):
        # Arrange: Set up the input parameters
        run = {"id": 1, "name": "Test Run"}
        evaluations = [{"id": 1, "score": 95}, {"id": 2, "score": 88}]
        aggregated_evaluations = {"average": 91.5}

        # Act: Create the Celery signature for the compile_evaluations task
        populated_evaluations_task = compile_evaluations.s(
            run, evaluations, aggregated_evaluations
        )

        # Assert: Verify that the signature was created with the correct arguments
        mock_compile_evaluations_s.assert_called_once_with(
            run, evaluations, aggregated_evaluations
        )
        self.assertEqual(
            populated_evaluations_task, mock_compile_evaluations_s.return_value
        )

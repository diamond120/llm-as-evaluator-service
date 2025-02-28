def evaluate_code_execution(self, code, language, colab_id, turn_number):
    try:
        full_evaluation_configs = [
            llm_as_evaluator.create_evaluation_config(
                "AGENTIC_code_checker_h3_e5__string",
                "agentic_code_checker",
                use_for_agg_layer=True,
                config={"edge_cases_count": 2, "happy_cases_count": 2},
            ),
        ]

        inputs = [
            {
                "code_string": code,
            }
        ]

        aggregated_evaluation_configs = []

        response = llm_as_evaluator.initiate_all_at_once_and_get_all(
            batch_name="Code Gen & Translation",
            inputs=inputs,
            evaluations=full_evaluation_configs,
            aggregated_evaluations=aggregated_evaluation_configs,
            format_to_issues_scores=False,  # <-try with False as well to change formatting of the output
            batches_per_minute=10,
        )
        evaluation = response[0]["runs"][0]["evaluations"][0]["output"][0]

        try:
            evaluation_tests = evaluation["tests"]
            evaluation_results = evaluation["results"]

            failed_tests = []
            passed_tests = []

            for idx, result in enumerate(evaluation_results):
                test_description = evaluation_tests[idx]
                if result["result"] == "FAILED":
                    failed_tests.append(
                        f"Test: {test_description}\nComment: {result['comment']}\n"
                    )
                elif result["result"] == "PASSED":
                    passed_tests.append(
                        f"Test: {test_description}\nComment: {result['comment']}\n"
                    )

            failed = "\n".join(failed_tests)
            passed = "\n".join(passed_tests)

            if passed:
                logger.info(f"Execution passed for {language}: {passed}")

            if failed:
                logger.info(f"Execution failed for {language}: {failed}")

        except KeyError:
            # Handle the case where 'tests' is not in the evaluation dictionary
            first_result_comment = evaluation["results"][0].get(
                "comment", "No comment provided"
            )
            logger.info(f"Execution failed for {language}: {first_result_comment}")
            return
    except Exception as e:
        traceback.print_exc()
        logger.error(
            f"Exception occurred during code execution for {language}: {str(e)}"
        )
        logger.info(
            f"Error occurred during code execution evaluation for {language} - could not get result"
        )

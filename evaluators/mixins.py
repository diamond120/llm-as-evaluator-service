import json


class TokenUsageMixin:
    def extract_token_usage(self, raw_result):
        # Debug print statement to show raw_result details
        print(f"Debug: raw_result details - {raw_result}")
        # Initialize an empty dictionary for usage data
        usage_data = {}

        try:
            # Attempt to parse raw_result as JSON
            result_dict = json.loads(raw_result)
        except (json.JSONDecodeError, TypeError):
            # If raw_result is not a JSON string, handle it as a dictionary
            result_dict = raw_result if isinstance(raw_result, dict) else {}

        if not result_dict:
            try:
                result_dict = raw_result.response_metadata
            except ex:
                result_dict = {}

        # Check for 'usage_metadata' in the parsed result
        if "usage_metadata" in result_dict:
            usage_metadata = result_dict["usage_metadata"]
            usage_data.update(
                {
                    "prompt_tokens": usage_metadata.get("input_tokens", 0),
                    "completion_tokens": usage_metadata.get("output_tokens", 0),
                    "total_tokens": usage_metadata.get("total_tokens", 0),
                }
            )

        # Check for 'response_metadata' in the parsed result
        if "response_metadata" in result_dict:
            response_metadata = result_dict["response_metadata"]
            token_usage = response_metadata.get("token_usage", {})
            usage_data.update(
                {
                    "prompt_tokens": token_usage.get(
                        "prompt_tokens", usage_data.get("prompt_tokens", 0)
                    ),
                    "completion_tokens": token_usage.get(
                        "completion_tokens", usage_data.get("completion_tokens", 0)
                    ),
                    "total_tokens": token_usage.get(
                        "total_tokens", usage_data.get("total_tokens", 0)
                    ),
                }
            )

        # Check for 'token_usage' directly in the parsed result
        if "token_usage" in result_dict:
            token_usage = result_dict["token_usage"]
            usage_data.update(
                {
                    "prompt_tokens": token_usage.get(
                        "prompt_tokens", usage_data.get("prompt_tokens", 0)
                    ),
                    "completion_tokens": token_usage.get(
                        "completion_tokens", usage_data.get("completion_tokens", 0)
                    ),
                    "total_tokens": token_usage.get(
                        "total_tokens", usage_data.get("total_tokens", 0)
                    ),
                }
            )

        # If no token usage data was found, print a debug message
        if not usage_data:
            print("Debug: No token usage data found, returning empty dict")

        return usage_data

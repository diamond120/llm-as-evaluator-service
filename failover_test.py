from llm_failover import ChatFailoverLLM
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
import asyncio
import argparse
from langchain.schema import HumanMessage

def create_model(provider, model, failover=True):
    if failover:
        return ChatFailoverLLM(provider, model)
    
    match provider:
        case "openai_api":
            return ChatOpenAI(model=model)
        case "google_api":
            return ChatGoogleGenerativeAI(model=model)
        case "anthropic_api":
            return ChatAnthropic(model=model)
    
    raise ValueError(f"Unsupported provider: {provider}")

async def async_test(model, input):
    print(f"Generated response: {await model.ainvoke(input)}")

def sync_test(model, input):
    print(f"Generated response: {model.invoke(input)}")
    
def test():
    parser = argparse.ArgumentParser(description="Create and test LLM models")
    
    # Required arguments
    parser.add_argument('--provider', type=str, required=True, help='The provider name (e.g., openai_api, google_api, anthropic_api).')
    parser.add_argument('--model', type=str, required=True, help='The model name (e.g., gpt-4o, gemini-1.5-pro).')
    
    # Optional arguments with default values
    parser.add_argument('--failover', action="store_true", default=False, help='Enable failover (default: False).')
    parser.add_argument('--async_mode', action="store_true", default=False, help='Enable async mode (default: False).')
    parser.add_argument('--structured_output', action="store_true", default=False, help='Enable structured output (default: False).')

    args = parser.parse_args()
    print(f"Parsed args: {args}")

    model = create_model(args.provider, args.model, args.failover)
    print(f"Created model: {type(model)}")

    if args.structured_output:
        output_schema = {
            "title": "EvaluationOutput",
            "description": "Evaluation output with nested structure.",
            "type": "object",
            "required": ["evaluation"],
            "properties": {
                "evaluation": {
                    "title": "Evaluation Details",
                    "type": "object",
                    "required": ["plan_steps", "steps_execution", "issues", "before_scoring"],
                    "properties": {
                        "plan_steps": {
                            "title": "Plan Steps",
                            "type": "string",
                            "description": "Detailed steps for the plan."
                        },
                        "steps_execution": {
                            "title": "Steps Execution",
                            "type": "string",
                            "description": "How the steps were executed."
                        },
                        "issues": {
                            "title": "Issues",
                            "type": "string",
                            "description": "Any issues encountered during the evaluation."
                        },
                        "before_scoring": {
                            "title": "Before Scoring",
                            "type": "string",
                            "description": "Details before the scoring step."
                        }
                    }
                },
                "score_details": {
                    "title": "Score Details",
                    "type": "object",
                    "required": ["score"],
                    "properties": {
                        "score": {
                            "title": "Score",
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 5,
                            "description": "Final evaluation score ranging from 1 to 5."
                        }
                    }
                }
            }
        }
        model = model.with_structured_output(output_schema, include_raw=True)

    input = [HumanMessage(content="Please evaluate the statement '2 + 3 is 5' and provide an explanation in 10 sentences.")]
    if args.async_mode:
        asyncio.run(async_test(model, input))
    else:
        sync_test(model, input)
        
if __name__ == '__main__':
    test()

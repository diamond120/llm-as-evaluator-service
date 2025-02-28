from fastapi import APIRouter, HTTPException

from app.logging_config import logger
from app.schemas.passthrough import PassThroughRequest
from common.utils import load_env
from evaluators.library.pass_through_evaluator import MistralEvaluator, OpenAIEvaluator

env_vars = load_env()


router = APIRouter()


@router.post("/openai")
async def passthrough_openai(request: PassThroughRequest):
    input_data = request.inputs[0].dict()
    eval_config = request.evaluations[0]["config"] if request.evaluations else {}
    llm_config = {
        "model": eval_config.get("model", "gpt-3.5-turbo"),
        "temperature": eval_config.get("temperature"),
        "seed": eval_config.get("seed"),
    }
    try:
        evaluator = OpenAIEvaluator(
            name="openai_evaluator",
            config=eval_config,
            llm_config=llm_config,
            config_schema={},
            input_schema={},
            output_schema={},
        )
        result = evaluator.evaluate(input_data, eval_config)
        logger.info(f"OpenAI evaluation result: {result}")
        return result
    except Exception as e:
        logger.exception("An error occurred in passthrough_openai: {0}".format(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mistral")
async def passthrough_mistral(request: PassThroughRequest):
    input_data = request.inputs[0].dict()
    eval_config = request.evaluations[0]["config"] if request.evaluations else {}
    llm_config = {
        "model": eval_config.get("model", "mistral-large-latest"),
        "temperature": eval_config.get("temperature"),
        "seed": eval_config.get("seed"),
    }
    try:
        evaluator = MistralEvaluator(
            name="mistral_evaluator",
            config=eval_config,
            llm_config=llm_config,
            config_schema={},
            input_schema={},
            output_schema={},
        )
        result = evaluator.evaluate(input_data, eval_config)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

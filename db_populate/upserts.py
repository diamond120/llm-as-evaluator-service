from app.db_api.database import get_db_ctx
from app.db_api.models.models import Engagement, Evaluator, EvaluatorType, Project


def upsert_evaluator_type(fields):
    """
    Function to create evaluator types based on predefined configurations and add them to the database.
    """
    with get_db_ctx() as db:
        existing_evaluator_type = (
            db.query(EvaluatorType).filter_by(name=fields["name"]).first()
        )
        if existing_evaluator_type:
            print(
                f"Evaluator Type '{fields['name']}' already exists, updating instead."
            )
            for key, value in fields.items():
                setattr(existing_evaluator_type, key, value)
            db.add(existing_evaluator_type)
        else:
            evaluator = EvaluatorType(**fields)
            db.add(evaluator)
            print(f"Created and added Evaluator Type: {evaluator.name}")


def upsert_evaluator(creator_id, fields):
    """
    Create evaluators for a given engagement and project using predefined configurations.
    """
    with get_db_ctx() as db:
        # Find the project by name within the specified engagemen

        updated_config = fields.copy()
        updated_config.update({"creator_id": creator_id})
        # updated_config["name"] += f"_{updated_config['llm_model']}"
        # Find evaluator type by name
        evaluator_type = (
            db.query(EvaluatorType)
            .filter(EvaluatorType.name == updated_config["evaluator_type_name"])
            .one_or_none()
        )

        if evaluator_type is None:
            print(
                f"Error: EvaluatorType '{updated_config['evaluator_type_name']}' not found."
            )
            raise

        existing_evaluator = (
            db.query(Evaluator)
            .filter(
                Evaluator.name == updated_config["name"],
                Evaluator.creator_id == creator_id,
            )
            .one_or_none()
        )
        if existing_evaluator:
            print(
                f"Updating: Evaluator '{updated_config['name']}' already exists. Updating it..."
            )
            for key, value in updated_config.items():
                setattr(existing_evaluator, key, value)
            setattr(existing_evaluator, "evaluator_type_id", evaluator_type.id)
            db.add(existing_evaluator)
        else:
            evaluator = Evaluator(
                name=updated_config["name"],
                creator_id=creator_id,
                evaluator_type=evaluator_type,
                description=updated_config["description"],
                config=updated_config["config"],
                llm_provider=updated_config["llm_provider"],
                llm_model=updated_config["llm_model"],
                llm_params=updated_config["llm_params"],
                input_schema=updated_config["input_schema"],
                output_schema=updated_config["output_schema"],
            )

            db.add(evaluator)
            print(f"Created and added Evaluator: {updated_config['name']}")

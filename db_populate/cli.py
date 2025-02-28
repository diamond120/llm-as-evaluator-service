import argparse
from datetime import datetime, timedelta

from sqlalchemy import text

# Updated import based on lint context
from sqlalchemy.exc import NoResultFound

from app.db_api.database import get_db_ctx
from app.db_api.models.models import (
    CONST,
    Engagement,
    Evaluator,
    EvaluatorType,
    Project,
    Role,
    User,
    UserProjectRole,
)
from app.utils.auth import create_access_token

# from evaluators.library.inits.compile_evaluator_type_from_inits import (
#     cellwise_quality_aspector_evaluator_type,
#     generic_evaluator_type,
#     quality_aspector_evaluator_type,
# )
from common.constants import DEFAULT_EMAIL
from evaluators.library.inits.compile_evaluator_from_inits import (
    cellwise_quality_aspector_evaluator,
    code_review_evaluator,
    generic_task_evaluator,
    penalizer_evaluator,
    quality_aspector_evaluator,
    quality_aspector_evaluator_with_thinking_field,
    summarizer_evaluator,
    tagging_evaluator,
    tagging_evaluator_groq_mixtral,
)


def get_or_create_default_user(user_name="admin", user_email=DEFAULT_EMAIL):
    with get_db_ctx() as db:
        user = (
            db.query(User)
            .filter(User.name == user_name, User.email == user_email)
            .one_or_none()
        )
        if user is None:
            user = User(name=user_name, email=user_email)
            db.add(user)
            db.commit()
        return user.id


def delete_all_items_from_tables_cascade():
    """
    Deletes all items from all tables in the database using CASCADE to automatically
    delete dependent entities. This approach does not require disabling and enabling
    constraints but should be used with caution.
    """
    print("Attempting to delete all items from selected tables...")
    if input("Please confirm y? = ") != "y":
        print("Operation cancelled.")
        return
    try:
        with get_db_ctx() as db:
            # Retrieve all table names
            tables = [
                CONST + "evaluation_configs",
                CONST + "evaluator_configs",
                CONST + "evaluation",
                CONST + "evaluator",
                CONST + "run",
                CONST + "project",
                CONST + "engagement",
                CONST + "evaluator_type",
            ]

            # Delete all items from each table using CASCADE
            for table in tables:
                print(f"Clearing `{table}`...")
                db.execute(text(f"DELETE FROM {table};"))
                db.execute(text(f"ALTER TABLE {table} AUTO_INCREMENT = 1;"))

        print("Successfully deleted all items from selected tables.")
    except Exception as e:
        print(f"An error occurred: {e}")


def create_engagements(engagement_names):
    """
    Creates engagements based on the provided list of engagement names.

    This function iterates over a list of engagement names, checks if an engagement
    with the given name already exists in the database, and if not, creates a new
    engagement record.

    Args:
        engagement_names (list of str): A list of names for the engagements to be created.

    Returns:
        None: This function does not return anything but will output the creation status
        of each engagement to the console.
    """
    with get_db_ctx() as db:
        for engagement_name in engagement_names:
            # Check if the engagement already exists
            engagement = (
                db.query(Engagement)
                .filter(Engagement.name == engagement_name)
                .one_or_none()
            )

            # If the engagement does not exist, create it
            if engagement is None:
                engagement = Engagement(name=engagement_name)
                db.add(engagement)

                print(f"Created new engagement: {engagement_name}")
            else:
                print(f"Engagement '{engagement_name}' already exists.")
        db.commit()


def populate_db_with_engagement_and_project_userrole(
    engagement_name,
    engagement_description,
    project_name,
    project_description,
    user_name,
    user_email,
    role_name,
):
    print(f"Engagement Name: {engagement_name}")
    print(f"Engagement Description: {engagement_description}")
    print(f"Project Name: {project_name}")
    print(f"Project Description: {project_description}")
    print(f"User Name: {user_name}")
    print(f"User Email: {user_email}")
    print(f"Role Name: {role_name}")

    with get_db_ctx() as db:
        # Process Engagement
        engagement = (
            db.query(Engagement)
            .filter(Engagement.name == engagement_name)
            .one_or_none()
        )
        if engagement is None:
            engagement = Engagement(
                name=engagement_name, description=engagement_description
            )
            db.add(engagement)

        # Process User
        user = (
            db.query(User)
            .filter(User.name == user_name, User.email == user_email)
            .one_or_none()
        )
        if user is None:
            user = User(name=user_name, email=user_email)
            db.add(user)

        # Process Role
        role = db.query(Role).filter(Role.name == role_name).one_or_none()
        if role is None:
            role = Role(name=role_name)
            db.add(role)

        # Process Project
        project = (
            db.query(Project)
            .filter(Project.name == project_name, Project.engagement == engagement)
            .one_or_none()
        )
        if project is None:
            project = Project(
                name=project_name,
                description=project_description,
                engagement=engagement,
            )
            db.add(project)

        # Process UserProjectRole
        existing_role = (
            db.query(UserProjectRole)
            .filter_by(user_id=user.id, project_id=project.id, role_id=role.id)
            .one_or_none()
        )

        if existing_role:
            # Update is_active or other fields if necessary
            existing_role.is_active = True
            db.add(existing_role)
            print("Updated existing role.")
        else:
            # Insert new record
            new_role = UserProjectRole(
                user_id=user.id, project_id=project.id, role_id=role.id, is_active=True
            )
            db.add(new_role)
            print("Inserted new role.")

        # Commit all changes at once
        print(
            f"Creating new UserProjectRole: User {user_name} (ID: {user.id}), Project {project_name} (ID: {project.id}), Role {role_name} (ID: {role.id})"
        )
        db.commit()
        print("Done dude.")


def create_evaluator_types():
    """
    Function to create evaluator types based on predefined configurations and add them to the database.
    """
    with get_db_ctx() as db:

        evaluator_types = [
            cellwise_quality_aspector_evaluator_type,
            quality_aspector_evaluator_type,
            generic_evaluator_type,
        ]
        for evaluator_type_config in evaluator_types:
            existing_evaluator = (
                db.query(EvaluatorType)
                .filter_by(name=evaluator_type_config["name"])
                .first()
            )
            if existing_evaluator:
                print(
                    f"Evaluator Type '{evaluator_type_config['name']}' already exists, skipping."
                )
            else:

                evaluator = EvaluatorType(**evaluator_type_config)
                db.add(evaluator)
                print(f"Created and added Evaluator Type: {evaluator.name}")


def create_evaluators_for_project(engagement_name, project_name, llm_config):
    with get_db_ctx() as db:
        # Attempt to find the project by name within the specified engagement
        project = (
            db.query(Project)
            .join(Engagement)
            .filter(Project.name == project_name, Engagement.name == engagement_name)
            .one_or_none()
        )

        if project is None:
            print(
                f"Error: Project '{project_name}' under engagement '{engagement_name}' not found."
            )
            return

        # Define evaluator configurations
        evaluator_configs = [
            quality_aspector_evaluator,
            summarizer_evaluator,
            penalizer_evaluator,
            generic_task_evaluator,
            quality_aspector_evaluator_with_thinking_field,
            code_review_evaluator,
            tagging_evaluator,
            tagging_evaluator_groq_mixtral,
            cellwise_quality_aspector_evaluator,
        ]

        # Iterate over the evaluator configurations
        for config in evaluator_configs:
            config = (
                config.copy()
            )  # Copy the dictionary to avoid modifying the original
            config.update({"project_id": project.id})
            config["name"] += f"_{config['llm_model']}"

            # Attempt to find the evaluator type by name
            evaluator_type = (
                db.query(EvaluatorType)
                .filter(EvaluatorType.name == config["evaluator_type_name"])
                .one_or_none()
            )

            if evaluator_type is None:
                print(
                    f"Error: EvaluatorType '{config['evaluator_type_name']}' not found."
                )
                continue

            # Check if an evaluator with the same name already exists
            existing_evaluator = (
                db.query(Evaluator)
                .filter(Evaluator.name == config["name"])
                .one_or_none()
            )
            if existing_evaluator:
                print(f"Skipping: Evaluator '{config['name']}' already exists.")
                continue

            # Check for an admin user or create if not exists
            admin_user = (
                db.query(User)
                .filter(User.name == "admin", User.email == "admin_test@xxxx.com")
                .one_or_none()
            )
            if admin_user is None:
                admin_user = User(name="admin", email="admin_test@xxxx.com")
                db.add(admin_user)
                db.flush()  # Ensure the user ID is available for assignment to the evaluator

            # Create a new evaluator
            evaluator = Evaluator(
                name=config["name"],
                evaluator_type=evaluator_type,
                description=config["description"],
                config=config["config"],
                llm_provider=config["llm_provider"],
                llm_model=config["llm_model"],
                llm_params=config["llm_params"],
                input_schema=config["input_schema"],
                output_schema=config["output_schema"],
                creator_id=admin_user.id,
            )

            db.add(evaluator)
            print(f"Created and added Evaluator: {config['name']}")

        # Commit all changes after processing all evaluators
        db.commit()


def create_evaluators(engagement_name, project_name, llm_config):
    """
    Create evaluators for a given engagement and project using predefined configurations.
    """
    with get_db_ctx() as db:
        # Find the project by name within the specified engagement
        project = (
            db.query(Project)
            .join(Engagement)
            .filter(Project.name == project_name, Engagement.name == engagement_name)
            .one_or_none()
        )

        if project is None:
            print(
                f"Error: Project '{project_name}' under engagement '{engagement_name}' not found."
            )
            return

        # Define evaluator configurations
        evaluator_configs = [
            quality_aspector_evaluator,
            summarizer_evaluator,
            penalizer_evaluator,
            generic_task_evaluator,
            quality_aspector_evaluator_with_thinking_field,
            code_review_evaluator,
            tagging_evaluator,
            tagging_evaluator_groq_mixtral,
            cellwise_quality_aspector_evaluator,
        ]

        for config in evaluator_configs:
            # Update config with project_id and llm_config
            updated_config = config.copy()
            updated_config.update({"project_id": project.id})
            updated_config["name"] += f"_{updated_config['llm_model']}"
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
                continue

            existing_evaluator = (
                db.query(Evaluator)
                .filter(Evaluator.name == updated_config["name"])
                .one_or_none()
            )
            if existing_evaluator is not None:
                print(f"Skipping: Evaluator '{updated_config['name']}' already exists.")
            else:
                user = (
                    db.query(User)
                    .filter(User.name == "admin", User.email == "admin_test@xxxx.com")
                    .one_or_none()
                )
                if user is None:
                    user = User(name="admin", email="admin_test@xxxx.com")
                    db.add(user)

                evaluator = Evaluator(
                    name=updated_config["name"],
                    evaluator_type=evaluator_type,
                    description=updated_config["description"],
                    config=updated_config["config"],
                    llm_provider=updated_config["llm_provider"],
                    llm_model=updated_config["llm_model"],
                    llm_params=updated_config["llm_params"],
                    input_schema=updated_config["input_schema"],
                    output_schema=updated_config["output_schema"],
                    creator_id=user.id,
                )

                db.add(evaluator)
                print(f"Created and added Evaluator: {updated_config['name']}")


def create_users(name, email, project_names, engagement_name, roles):
    with get_db_ctx() as db:
        # Fetch all projects and roles
        # Filter projects by project name and engagement_name
        projects = (
            db.query(Project)
            .join(Engagement)
            .filter(Project.name.in_(project_names), Engagement.name == engagement_name)
            .all()
        )
        roles = db.query(Role).filter(Role.name.in_(roles)).all()

        # Create a new user
        user = (
            db.query(User).filter(User.name == name, User.email == email).one_or_none()
        )
        if user is None:
            user = User(name=name, email=email)

        # Assign all projects and roles to the user
        user.projects.extend(projects)
        user.roles.extend(roles)

        # Add the user to the session
        db.add(user)
        db.commit()


def generate_token(user_instances):

    for user_info in user_instances:
        with get_db_ctx() as db:
            user_email = user_info["email"]
            env = user_info["env"]
            access = user_info["access"]
            is_service_account = user_info.get("is_service_account", False)

            # Check if user exists, if not create the user
            user = db.query(User).filter(User.email == user_email).one_or_none()
            if user is None:
                user = User(
                    email=user_email,
                    name=user_email,
                    is_service_account=is_service_account,
                )
                db.add(user)
                db.flush()  # Us
                print(f"Created new user: {user_email} with email: {user_email}")
            else:
                print(f"User already exists: {user_email} with email: {user_email}")

            # Generate token for the user
            token_payload = {
                "user_email": user.email,
                "user_id": user.id,
                "env": env,
                "issued_on": datetime.utcnow().isoformat(),
                "access": "full",
            }

            jwt_token = create_access_token(
                data=token_payload, expires_delta=timedelta(days=30)  # 30 days validity
            )
            user.api_token = jwt_token  # Update the api_token in the user model
            db.add(user)
            db.commit()

            # Optionally send token via email or print it
            print(f"Generated token for {user_email}: {jwt_token}")


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Database initialization script.")
    parser.add_argument(
        "--clear-db", action="store_true", help="Clear all tables in the database."
    )
    parser.add_argument(
        "--create-engagements",
        type=str,
        help="Path to JSON file with engagements.",
    )
    parser.add_argument(
        "--create-eng-project",
        type=str,
        help="Path to JSON file with engagement and project details.",
    )
    parser.add_argument(
        "--create-evaluator-types",
        action="store_true",
        help="Create and add evaluator types to the database.",
    )
    parser.add_argument(
        "--create-evaluators",
        type=str,
        help="Path to JSON file with evaluator configurations.",
    )
    parser.add_argument(
        "--create-users",
        type=str,
        help="Path to JSON file with User configurations.",
    )
    parser.add_argument(
        "--generate-tokens",
        type=str,
        help="Path to JSON file with generate tokens.",
    )

    args = parser.parse_args()

    if args.clear_db:
        delete_all_items_from_tables_cascade()
    elif args.create_evaluator_types:
        create_evaluator_types()
    elif args.create_engagements:
        with open(args.create_engagements, "r") as file:
            data = json.load(file)
            create_engagements(data["engagements"])
    elif args.create_eng_project:
        with open(args.create_eng_project, "r") as file:
            data = json.load(file)
            populate_db_with_engagement_and_project_userrole(
                engagement_name=data["eng_name"],
                engagement_description=data.get("eng_desc", ""),
                project_name=data["proj_name"],
                project_description=data["proj_desc"],
                user_name=data["user_name"],
                user_email=data["user_email"],
                role_name=data["role_name"],
            )
    elif args.create_evaluators:
        with open(args.create_evaluators, "r") as file:
            configs = json.load(file)
            for config in configs["projects"]:
                create_evaluators_for_project(
                    engagement_name=config["engagement_name"],
                    project_name=config["project_name"],
                    llm_config=config["llm_config"],
                )
                print(
                    f"Processed for project: {config['project_name']} in {config['engagement_name']}"
                )
    elif args.create_users:
        with open(args.create_users, "r") as file:
            configs = json.load(file)
            for config in configs["users"]:
                create_users(
                    name=config["name"],
                    email=config["email"],
                    project_names=[config["project_names"]],
                    engagement_name=config["engagement_name"],
                    roles=config["roles"],
                )
                print(
                    f"Processed for project: {config['project_names']} in {config['engagement_name']}"
                )
    elif args.generate_tokens:
        with open(args.generate_tokens, "r") as file:
            user_data = json.load(file)
            generate_token(user_data["users"])

    else:
        print("No recognized parameters to process. Doing nothing. Bye.")

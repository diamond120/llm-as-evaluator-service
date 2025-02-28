import json
from sqlalchemy.exc import NoResultFound
from datetime import datetime, timedelta

from app.db_api.database import get_db_ctx, env_vars
from app.db_api.models.models import (
    CONST,
    Engagement,
    Evaluator,
    EvaluatorType,
    Project,
    User,
    Role,
    UserProjectRole,
)
from app.utils.auth import create_access_token


users = [
    {
        "engagement": "public-engagement",
        "project": "beta-test",
        "role": "admin",
        "email": "navaneethan.ramasamy@xxxx.com",
        "username": "navaneethan.ramasamy",
    },
    {
        "engagement": "public-engagement",
        "project": "beta-test",
        "role": "admin",
        "email": "alexei.v@xxxx.com",
        "username": "alexei.v",
    },
    {
        "engagement": "Meta",
        "project": "Meta-Project",
        "role": "admin",
        "email": "phuc.anthony@xxxx.com",
        "username": "phuc.anthony",
    },
]


def populate_db_with_engagement_and_project_userrole(
    engagement_name,
    engagement_description,
    project_name,
    project_description,
    user_name,
    user_email,
    role_name,
    env,
):
    print(f"Engagement Name: {engagement_name}")
    print(f"Engagement Description: {engagement_description}")
    print(f"Project Name: {project_name}")
    print(f"Project Description: {project_description}")
    print(f"User Name: {user_name}")
    print(f"User Email: {user_email}")
    print(f"Role Name: {role_name}")
    print(f"Environment: {env}")

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
            db.flush()  # Ensure engagement.id is available

        # Process User
        user = (
            db.query(User)
            .filter(User.name == user_name, User.email == user_email)
            .one_or_none()
        )
        if user is None:
            user = User(name=user_name, email=user_email)
            db.add(user)
            db.flush()  # Ensure user.id is available

        token_payload = {
            "user_email": user.email,
            "user_id": user.id,
            "env": env,
            "issued_on": datetime.utcnow().isoformat(),
            "access": "admin",
        }

        api_token = create_access_token(data=token_payload)
        user.api_token = api_token
        print(f"api_token: {api_token}")
        db.flush()  # Ensure user.api_token is saved

        # Process Role
        role = db.query(Role).filter(Role.name == role_name).one_or_none()
        if role is None:
            role = Role(name=role_name)
            db.add(role)
            db.flush()  # Ensure role.id is available

        # Process Project
        project = (
            db.query(Project)
            .filter(
                Project.name == project_name, Project.engagement_id == engagement.id
            )
            .one_or_none()
        )
        if project is None:
            project = Project(
                name=project_name,
                description=project_description,
                engagement_id=engagement.id,
            )
            db.add(project)
            db.flush()  # Ensure project.id is available

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
        print("~" * 20)


def onboard_new_user():
    print(f"DB Host: {env_vars['DB_HOSTNAME']}")
    print(f"Environment: {env_vars['ENVIRONMENT']}")
    print(
        "```\t\tDO YOU HAVE correct db, environment, secret key variables correctly set in .env? - If yes proceed"
    )
    if input("Please confirm y? = ") != "y":
        print("Operation cancelled.")
        return

    for user in users:
        populate_db_with_engagement_and_project_userrole(
            user["engagement"],
            user.get("engagement_description", "test description"),
            user["project"],
            user.get("project_description", "proj description"),
            user["username"],
            user["email"],
            user["role"],
            env_vars["ENVIRONMENT"],
        )


if __name__ == "__main__":
    onboard_new_user()

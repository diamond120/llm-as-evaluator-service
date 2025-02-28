from fastapi import HTTPException
from app.db_api.database import get_db_ctx_manual
from sqlalchemy.future import select

from app.db_api.models.models import (
    Engagement,
    Evaluator,
    EvaluatorType,
    Project,
    User,
    UserProjectRole,
)
from app.logging_config import logger
from common.constants import DEFAULT_EMAIL
from common.utils import load_env

env_vars = load_env()


def get_engagement_and_user_create_project_and_role(
    engagement_name, project_name, user_email
):
    """
    Get engagement and user, create project and UserProjectRole if project not found.
    """
    with get_db_ctx_manual() as db:
        logger.debug(f"Fetching engagement with name: {engagement_name}")
        engagement = (
            db.query(Engagement).filter(Engagement.name == engagement_name).first()
        )
        if not engagement:
            if user_email in env_vars.get("TLT_API_USERS", []):
                logger.debug(
                    f"Creating engagement with name: {engagement_name} for user: {user_email}"
                )
                engagement = Engagement(name=engagement_name)
                db.add(engagement)
                db.commit()
                db.refresh(engagement)
                logger.info(
                    f"Engagement '{engagement_name}' created successfully for user: {user_email}"
                )
            else:
                raise HTTPException(
                    status_code=404,
                    detail=f"Engagement with name '{engagement_name}' not found for user: {user_email}",
                )
        logger.debug(f"Fetching user with email: {user_email}")
        user = db.query(User).filter(User.email == user_email).first()
        if not user:
            logger.error(f"User with email '{user_email}' not found")
            raise HTTPException(
                status_code=404, detail=f"User with email '{user_email}' not found"
            )

        logger.debug(
            f"Checking if project with name '{project_name}' under engagement '{engagement_name}' exists"
        )
        project = (
            db.query(Project)
            .filter(
                Project.name == project_name, Project.engagement_id == engagement.id
            )
            .first()
        )
        if not project:
            logger.debug(f"Creating project with name: {project_name}")
            project = Project(name=project_name, engagement_id=engagement.id)
            db.add(project)
            db.commit()
            db.refresh(project)
            logger.info(f"Project '{project_name}' created successfully")

        logger.debug(
            f"Creating UserProjectRole for user '{user_email}' and project '{project_name}'"
        )
        user_project_role = UserProjectRole(user_id=user.id, project_id=project.id)
        db.add(user_project_role)
        db.commit()
        db.refresh(user_project_role)
        logger.info(
            f"UserProjectRole created successfully for user '{user_email}' and project '{project_name}'"
        )

    return user_project_role, engagement, project, user


def _get_user_object(
    db, engagement_name, project_name, user_email, raise_exc, create_project_if_not
):
    query = (
        select(Engagement, Project, User, UserProjectRole)
        .join(Project, Project.engagement_id == Engagement.id)
        .join(UserProjectRole, UserProjectRole.project_id == Project.id)
        .join(User, User.id == UserProjectRole.user_id)
        .filter(
            Engagement.name == engagement_name,
            Project.name == project_name,
            User.email == user_email,
        )
    )

    result = yield query

    if not result:
        logger.info(
            f"Project '{project_name}' does not exist for engagement '{engagement_name}' or user '{user_email}' does not have a role in the project."
        )
        if not create_project_if_not:
            if raise_exc:
                raise HTTPException(
                    status_code=404,
                    detail=f"UserProjectRole with User Email '{user_email}', Engagement Name '{engagement_name}' and Project Name '{project_name}' not found",
                )
            yield None, None, None
        else:
            user_project_role, engagement, project, user = (
                get_engagement_and_user_create_project_and_role(
                    engagement_name, project_name, user_email
                )
            )
            yield engagement, project, user, user_project_role
    else:

        engagement, project, user, user_project_role = result

        yield engagement, project, user, user_project_role
    yield None


def _get_user_project_role_object(db, user, project, create_project_if_not):
    query = select(UserProjectRole).filter(
        UserProjectRole.user_id == user.id, UserProjectRole.project_id == project.id
    )

    user_project_role = yield query

    if not user_project_role:
        if create_project_if_not:
            user_project_role = UserProjectRole(user_id=user.id, project_id=project.id)
            db.add(user_project_role)

    yield user_project_role
    yield None


async def async_get_user_project_object(
    db,
    engagement_name,
    project_name,
    user_email=DEFAULT_EMAIL,
    raise_exc=True,
    create_project_if_not=False,
):
    g = _get_user_object(
        db, engagement_name, project_name, user_email, raise_exc, create_project_if_not
    )
    query = next(g)
    logger.debug(f"Generated query: {query}")
    try:
        result = (await db.execute(query)).first()
    except Exception as e:
        logger.debug("Engagement project user not found", exc_info=e)
        result = None
    engagement, project, user, user_project_role = g.send(result)
    logger.info(
        f"Engagement: {engagement}, Project: {project}, User: {user}, user_project_role: {user_project_role}"
    )

    return user_project_role, project, user, engagement


def get_user_project_object(
    db,
    engagement_name,
    project_name,
    user_email=DEFAULT_EMAIL,
    raise_exc=True,
    create_project_if_not=False,
):
    logger.debug(
        f"Fetching user object for email: {user_email}, engagement: {engagement_name}, project: {project_name}"
    )
    g = _get_user_object(
        db, engagement_name, project_name, user_email, raise_exc, create_project_if_not
    )
    query = next(g)
    try:
        result = db.execute(query).first()
        logger.debug(f"Query result for user object: {result}")
    except Exception as e:
        logger.error("Engagement project user not found", exc_info=e)
        result = None

    engagement, project, user, user_project_role = g.send(result)

    if not engagement or not project or not user:
        logger.warning("Engagement, project, or user not found")
        return None, None, None, None

    return user_project_role, project, user, engagement

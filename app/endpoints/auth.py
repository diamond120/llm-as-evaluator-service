import os
from datetime import datetime, timedelta

import httpx
import requests
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBearer
from passlib.context import CryptContext
from pydantic import EmailStr
from sqlalchemy.orm import Session
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse

from app.db_api import database
from app.db_api.models import Engagement, Project, Role, User, UserProjectRole
from app.logging_config import logger
from app.schemas.auth import (
    ProjectEngagementUserAuthTestSchema,
    RefreshTokenRequest,
    RegisterUserForProjectRequest,
)
from app.utils.auth import (
    create_access_token,
    create_and_update_access_token,
    create_user,
    get_current_user,
    verify_google_token,
    get_user_role,
    generate_client_credentials,
)
from app.utils.query import async_get_user_project_object, get_user_project_object
from common.utils import load_env

env_vars = load_env()

PROJECT_ID = env_vars["GOOGLE_CLOUD_PROJECT"]
TOPIC_ID = env_vars["PUBSUB_TOPIC"]
oauth2_scheme = HTTPBearer()
pwd_context = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"], deprecated="auto")

router = APIRouter()


def send_email(to_email: str, subject: str, body: str):
    """
    Sends email to the user.

    Args:
        to_email (str): Email address of the user
        subject (str): Subject of the email
        body (str): Body of the email (HTML supported)
    """
    logger.debug(f"Preparing to send email to {to_email} with subject '{subject}'")
    ecs_url = "https://email-mailer.xxxx.com/api/v1/mail/send-saved-template"
    r = requests.post(
        ecs_url,
        json={
            "template_id": env_vars["xxxx_ECS_EMAIL_TEMPLATE_ID"],
            "receivers": [{"email": to_email}],
            "replacements": [{"subject": subject, "body": body}],
            "sender": {"email": "xxxx-gpt@xxxx.com", "name": "xxxx GPT"},
            "force_choose": "SendGrid",
        },
        headers={
            "Content-Type": "application/json",
            "api-key": env_vars["xxxx_ECS_API_KEY"],
        },
    )
    logger.info(f"Email sent to {to_email} with status code {r.status_code}")
    return r.status_code


def authenticate_user(db, client_id, secret_pwd):
    logger.debug(f"Authenticating user with client_id: {client_id}")
    user = db.query(User).filter(User.client_id == client_id).first()
    if not user:
        logger.warning(f"User with client_id {client_id} not found")
        return False
    logger.debug(f"Verifying password for user {user.email}")
    if not pwd_context.verify(secret_pwd, user.client_secret):
        logger.warning(f"Password verification failed for user {user.email}")
        return False
    logger.info(f"User {user.email} authenticated successfully")
    return user


@router.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    logger.debug("Serving root endpoint")
    return HTMLResponse(
        """<!DOCTYPE html>
<html>
<head>
    <title>Login with Google</title>
</head>
<body>
    <h1>Login with Google</h1>
    <a href="/api/v1/a/auth/login">
        <button>Login with Google</button>
    </a>
</body>
</html>"""
    )


@router.get("/auth/login")
async def login():
    logger.debug("Initiating login process")
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    redirect_uri = os.getenv("REDIRECT_URI")
    logger.info(f"Redirecting to Google OAuth with client_id: {client_id}")
    return RedirectResponse(
        url=f"https://accounts.google.com/o/oauth2/v2/auth?response_type=code&client_id={client_id}&redirect_uri={redirect_uri}&scope=openid%20email%20profile&access_type=offline"
    )


@router.get("/auth/callback")
async def auth_callback(code: str, db: Session = Depends(database.get_db_gen)):
    if code == "fake-login":
        user_info = { "email": "samuel.choi@xxxx.com" }
    else:
        logger.debug(f"Handling auth callback with code: {code}")
        token_url = "https://oauth2.googleapis.com/token"
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        redirect_uri = os.getenv("REDIRECT_URI")
        token_data = {
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }
        response = httpx.post(token_url, data=token_data)
        response.raise_for_status()
        tokens = response.json()
        logger.debug(f"Received tokens: {tokens}")
        user_info = verify_google_token(tokens["id_token"])
        if not user_info["email"].endswith("@xxxx.com"):
            logger.error("User is not a xxxx user")
            return HTMLResponse(
                content="""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Invalid User</title>
                </head>
                <body>
                    <h1>Invalid User</h1>
                    <p>You are not authorized to access this service. Please use a valid xxxx email.</p>
                    <a href="/api/v1/a/auth/login">
                        <button>Login with Google</button>
                    </a>
                </body>
                </html>
                """,
                status_code=403,
            )
    user_obj = create_user(db, user_info["email"])
    token_payload = {
        "user_email": user_info["email"],
        "user_id": user_obj.id,
        "env": env_vars.get("ENVIRONMENT", "development"),
        "issued_on": datetime.utcnow().isoformat(),
        "access": get_user_role(user_info["email"]),
    }
    access_token = create_access_token(token_payload, expires_delta=timedelta(hours=3))
    logger.info(f"Access token created for user {user_info['email']}")
    redirect_url = os.getenv("REDIRECT_URL_AFTER_AUTH", "http://localhost:5173")
    response = RedirectResponse(url=f"{redirect_url}?access_token={access_token}")
    response.set_cookie(key="token", value=f"Bearer {access_token}", httponly=True)
    return response


@router.get("/testauth")
async def read_protected_data(user: User = Depends(get_current_user)):
    logger.debug(f"Accessing protected data for user {user.email}")
    return {"email": user.email, "name": user.name}


@router.post("/test-user-project-auth")
async def test_user_project_auth(
    project_engagement: ProjectEngagementUserAuthTestSchema,
    user: User = Depends(get_current_user),
    db: Session = Depends(database.async_get_db_session),
):
    logger.debug(f"Testing user project auth for user {user.email}")
    await async_get_user_project_object(
        db,
        project_engagement.engagement_name,
        project_engagement.project_name,
        (
            project_engagement.email
            if project_engagement.email != "current_user"
            else user.email
        ),
        raise_exc=True,
        create_project_if_not=False,
    )
    logger.info(f"User {user.email} has access to the project and engagement")
    return {"status": "OK"}


@router.post("/register-user")
async def register_user_for_project(
    user_data: RegisterUserForProjectRequest,
    db: Session = Depends(database.get_db_gen),
    user: User = Depends(get_current_user),
):
    logger.debug(
        f"Registering user {user_data.user_email} for project {user_data.project_name} and engagement {user_data.engagement_name}"
    )
    engagement_name = user_data.engagement_name
    project_name = user_data.project_name
    user_email = user_data.user_email
    role_name = user_data.role_name
    role = db.query(Role).filter(Role.name == role_name).first()
    if not role:
        logger.warning(f"Role '{role_name}' not found")
        return JSONResponse(
            status_code=404, content={"message": f"Role '{role_name}' not found"}
        )

    user_project_role, project, user, engagement = await async_get_user_project_object(
        db, engagement_name, project_name, user_email, raise_exc=False
    )
    if user_project_role:
        logger.warning(
            f"User {user_email} already registered for project {project_name} and engagement {engagement_name}"
        )
        return JSONResponse(
            status_code=400,
            content={
                "message": "User already registered for this project and engagement."
            },
        )

    # user = db.query(User).filter(User.email == user_email).first()
    if not user:
        user = User(email=user_email)
        db.add(user)
        db.commit()
        logger.info(f"New user {user_email} created")

    # engagement = db.query(Engagement).filter(Engagement.name == engagement_name).first()
    if not engagement:
        logger.warning(f"Engagement with name '{engagement_name}' not found")
        return JSONResponse(
            status_code=404,
            content={"message": f"Engagement with name '{engagement_name}' not found"},
        )

    # project = (
    #     db.query(Project)
    #     .filter(Project.name == project_name, Project.engagement_id == engagement.id)
    #     .first()
    # )
    if not project:
        logger.warning(
            f"Project with name '{project_name}' under engagement '{engagement_name}' not found"
        )
        return JSONResponse(
            status_code=404,
            content={
                "message": f"Project with name '{project_name}' under engagement '{engagement_name}' not found"
            },
        )

    new_user_project_role = UserProjectRole(
        user_id=user.id, project_id=project.id, role_id=role.id
    )
    db.add(new_user_project_role)
    db.commit()
    logger.info(
        f"User {user_email} successfully registered for project {project_name} and engagement {engagement_name}"
    )

    return JSONResponse(
        status_code=201,
        content={
            "message": "User successfully registered for the project and engagement."
        },
    )


@router.post("/generate-client-credentials/")
async def generate_client_credentials_for_user(
    email: EmailStr,
    db: Session = Depends(database.get_db_gen),
    user: User = Depends(get_current_user),
):
    logger.debug(f"Generating client credentials for email: {email}")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        logger.error(f"User with email {email} not found")
        raise HTTPException(status_code=404, detail="User not found")

    # Generate client ID and client secret
    client_id, raw_secret, hashed_secret = generate_client_credentials(
        email, email_as_username=True
    )

    # Save them in the user model
    user.client_id = client_id
    user.client_secret = hashed_secret
    # db.add(user)
    # db.commit()
    logger.info(f"Client credentials generated for user {email}")

    return JSONResponse(
        status_code=201,
        content={
            "client_id": client_id,
            "client_secret": raw_secret,
            "message": "Client credentials successfully generated and saved.",
        },
    )


@router.post("/generate-token/")
async def generate_token(
    email: EmailStr,
    db: Session = Depends(database.get_db_gen),
    user: User = Depends(get_current_user),
    sendTokenByEmail: bool = True,
):
    logger.debug(f"Generating token for email: {email}")
    user = db.query(User).filter(User.email == email).first()
    created = False
    if not user:
        user = create_user(db, email)
        created = True
        logger.info(f"New user {email} created")

    token_payload = {
        "user_email": user.email,
        "user_id": user.id,
        "env": env_vars.get("ENVIRONMENT", "development"),
        "issued_on": datetime.utcnow().isoformat(),
        "access": "admin",
    }

    jwt_token = create_access_token(
        data=token_payload, expires_delta=timedelta(days=30)
    )
    user.api_token = jwt_token
    db.add(user)
    db.commit()
    logger.info(f"JWT token generated for user {email}")

    if sendTokenByEmail:
        status_code = send_email(
            email,
            "[Imp]LLM Service Token",
            f"Please find the auth token for accessing LLM service:<br><em>{jwt_token}</em><br>"
            f"Client ID: {user.client_id}<br>Client Secret: {user.client_secret}<br>"
            "Please keep it safe. You can use the Client ID and Client Secret to refresh the token when it expires.",
        )

        if status_code != 200:
            logger.error(f"Failed to send email to {email}")
            raise HTTPException(status_code=500, detail="Failed to send email")

    res = {"message": "Token sent to your email.", "user_creation": created}

    if not sendTokenByEmail:
        res.update({"token": jwt_token})

    return res


@router.post("/refresh-token")
async def refresh_token(
    request: RefreshTokenRequest, db: Session = Depends(database.get_db_gen)
):
    logger.debug(f"Refreshing token for client_id: {request.client_id}")
    client_id = request.client_id
    client_secret = request.client_secret

    user = authenticate_user(db, client_id, client_secret)
    if not user:
        logger.warning(f"Invalid credentials for client_id: {client_id}")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    data = {
        "user_email": user.email,
        "user_id": user.id,
        "env": env_vars.get("ENVIRONMENT", "development"),
        "issued_on": datetime.utcnow().isoformat(),
        "access": "admin",
    }
    new_token = create_and_update_access_token(db, user, data)
    logger.info(f"New token generated for user {user.email}")

    return {"access_token": new_token, "client_id": client_id}

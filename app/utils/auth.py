from datetime import datetime, timedelta
import secrets

from fastapi import Depends, HTTPException, Security
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
    OAuth2PasswordBearer,
)
from jose import JWTError, jwt
from passlib.hash import pbkdf2_sha256

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db_api import AsyncSession, database, models
from app.logging_config import logger
from common.utils import load_env

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
oauth2_scheme = HTTPBearer()

env_vars = load_env()

SECRET_KEY = env_vars["SECRET_KEY"]
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = timedelta(days=15)
REFRESH_TOKEN_EXPIRE_DAYS = timedelta(days=15)


def create_user(db, email):
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        user = models.User(email=email)
        db.add(user)
        db.commit()
    return user


async def _async_get_user_db_request(db, user_id):
    return (
        await db.scalars(select(models.User).where(models.User.id == user_id))
    ).first()


def _sync_get_user_db_request(db, user_id):
    return db.query(models.User).filter(models.User.id == user_id).first()


def _get_current_user_helper(
    credentials: HTTPAuthorizationCredentials,
):
    try:
        token = credentials.credentials
        logger.debug(f"Token received: {token}")
        decrypted_token = token

        payload = jwt.decode(decrypted_token, SECRET_KEY, algorithms=[ALGORITHM])
        logger.debug(f"Token payload: {payload}")

        email = payload["user_email"]
        user_id = payload["user_id"]
        env = payload["env"]

        if env.upper() != env_vars["ENVIRONMENT"]:
            logger.debug(f"Environment from env variable {env_vars['ENVIRONMENT']}")
            logger.debug(f"Environment from payload {env.upper()}")
            logger.error("Invalid token: environment mismatch.")
            raise HTTPException(status_code=401, detail="Invalid token, env mismatch.")

        user_obj = yield user_id

        if not user_obj:
            logger.error("User not found.")
            raise HTTPException(status_code=404, detail="User not found")
        yield user_obj
        yield None

    except jwt.ExpiredSignatureError as e:
        logger.error(f"Token has expired: {str(e)}")
        raise HTTPException(
            status_code=401, detail="Token has expired, please refresh your token."
        )
    except jwt.JWTClaimsError as e:
        logger.error(f"Invalid token claims: {str(e)}")
        raise HTTPException(
            status_code=401, detail="Invalid token claims, please check the token."
        )
    except jwt.JWTError as e:
        logger.error(f"Invalid token: {str(e)}")
        raise HTTPException(
            status_code=401, detail="Invalid token, please request a new one."
        )
    except Exception as e:
        logger.error(f"Error processing token: {str(e)}")
        raise HTTPException(status_code=401, detail="User is not authorized.")


async def async_get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(oauth2_scheme),
    db: Session = Depends(database.async_get_db_session),
):
    try:
        g = _get_current_user_helper(credentials)
        user_id = next(g)
        return g.send(await _async_get_user_db_request(db, user_id))
    except Exception as e:
        logger.error("Error in async_get_current_user", exc_info=e)
        raise HTTPException(status_code=401, detail="User is not authorized.")


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(oauth2_scheme),
    db: Session = Depends(database.get_db_gen),
):
    logger.debug("Starting get_current_user function")
    try:
        g = _get_current_user_helper(credentials)
        user_id = next(g)
        logger.debug(f"User ID obtained: {user_id}")
        return g.send(_sync_get_user_db_request(db, user_id))
    except Exception as e:
        logger.error("Error in get_current_user", exc_info=e)
        raise HTTPException(status_code=401, detail="User is not authorized.")


def verify_google_token(id_token: str):
    try:
        decoded_token = jwt.get_unverified_claims(id_token)
        user_info = {
            "email": decoded_token.get("email"),
            "name": decoded_token.get("name"),
            "profile_pic": decoded_token.get("picture"),
        }
        return user_info
    except JWTError as e:
        raise HTTPException(status_code=400, detail=str(e))


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
        to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_and_update_access_token(db, user, token_payload):
    jwt_token = create_access_token(
        data=token_payload, expires_delta=ACCESS_TOKEN_EXPIRE_DAYS
    )
    user.api_token = jwt_token
    db.add(user)
    db.commit()
    return jwt_token


def update_access_token(db, token: str, expires_delta=REFRESH_TOKEN_EXPIRE_DAYS):
    user = None
    try:
        data = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user = (
            db.query(models.User)
            .filter(models.User.email == data["user_email"])
            .first()
        )
    except jwt.JWTError:
        user = db.query(models.User).filter(models.User.api_token == token).first()
        if user:
            data = {
                "user_email": user.email,
                "user_id": user.id,
                "env": env_vars.get("ENVIRONMENT", "development"),
                "issued_on": datetime.utcnow().isoformat(),
                "access": "admin",
            }
        else:
            raise HTTPException(
                status_code=401, detail="Token is invalid and user not found."
            )

    new_token = create_access_token(data, expires_delta)
    if user:
        user.api_token = new_token
        db.add(user)
        db.commit()
    return new_token


def generate_client_credentials(email, email_as_username):
    print("Email:", email)
    print("Email as Username:", email_as_username)
    if bool(email_as_username):
        client_id = email
        raw_secret = "&5*1*)" + email.split("@")[0] + "@xxxx"
    else:
        client_id = secrets.token_urlsafe(
            16
        )  # You can adjust the byte length as needed
        raw_secret = secrets.token_urlsafe(32)  # Longer for extra security

    # Hash the client_secret before storing it
    hashed_secret = pbkdf2_sha256.hash(raw_secret)

    return client_id, raw_secret, hashed_secret


def get_user_role(email: str):
    super_admin_users = env_vars.get(
        "SUPER_ADMIN_USERS", "navaneethan.ramasamy@xxxx.com,alexei.v@xxxx.com"
    ).split(",")
    if email in super_admin_users:
        return "superadmin"
    else:
        return "user"


def _decode(token: str):
    try:
        decoded_token = jwt.decode(
            token, env_vars["SECRET_KEY"], algorithms=[env_vars["ALGORITHM"]]
        )
        return decoded_token
    except jwt.JWTError:
        return None


def decode_access_token(token: str):
    try:
        decoded_token = _decode(token)
        return decoded_token if decoded_token["exp"] >= datetime.utcnow() else None
    except jwt.JWTError:
        return None

from celery import Celery  # MUST BE FIRST

_ = "1"  # DO NOT REMOVE
# DO NOT SORT
import logging
import traceback
import uuid

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy import TextClause
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.db_api.database import get_db_gen
from app.logging_config import logger
from app.routers import api_router
from common.utils import load_env

SECRET_PATH = "42--3-14"

security = HTTPBasic()


def check_basic_auth(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = "llmadmin"
    correct_password = "llmadmin@2024"
    logger.debug(f"Checking basic auth for user: {credentials.username}")
    if (
        credentials.username != correct_username
        or credentials.password != correct_password
    ):
        logger.warning("Failed basic auth attempt")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    logger.info("Basic auth successful")


app = FastAPI()


# Override the default OpenAPI and Swagger UI endpoints to include basic auth
@app.get(f"/api/v1/openapi.json", include_in_schema=False)
async def get_open_api_endpoint(
    credentials: HTTPBasicCredentials = Depends(check_basic_auth),
):
    logger.info("Serving OpenAPI endpoint")
    return get_openapi(
        title="My API",
        version="1.0.0",
        routes=app.routes,
    )


@app.get(f"/api/v1/docs", include_in_schema=False)
async def get_documentation(
    credentials: HTTPBasicCredentials = Depends(check_basic_auth),
):
    logger.info("Serving Swagger UI documentation")
    return get_swagger_ui_html(
        openapi_url=f"/api/v1/openapi.json",
        title="My API docs",
    )


@app.get(f"/api/v1/redoc", include_in_schema=False)
async def get_redoc_documentation(
    credentials: HTTPBasicCredentials = Depends(check_basic_auth),
):
    logger.info("Serving ReDoc documentation")
    return get_swagger_ui_html(
        openapi_url=f"/api/v1/openapi.json",
        title="My API docs",
    )


app.add_middleware(
    CORSMiddleware,
    # Specify the origins that are allowed to access the API. "*" allows all origins.
    allow_origins=["*"],
    allow_credentials=True,
    # Specify the HTTP methods allowed by the CORS policy.
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    # Specify the HTTP headers allowed by the CORS policy. "*" allows all headers.
    allow_headers=["*"],
)
app.add_middleware(SessionMiddleware, secret_key="!11M-3Valuat0R-5ervic3")

# Load environment variables
env_vars = load_env(override=True)


class LoggingAndTraceIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        trace_id = str(uuid.uuid4())

        # Define specific paths to log
        # Log request payload and trace ID for specific paths
        if request.url.path in ("/api/v1/runs", "/api/v1/runs/"):
            request_body = await request.body()
            try:
                payload = request_body.decode("utf-8")
            except UnicodeDecodeError:
                payload = str(request_body)
            logging.info(f"Trace ID: {trace_id} - Request payload: {payload}")

        # Add trace ID to request state
        request.state.trace_id = trace_id

        # Process request
        response = await call_next(request)

        # Add trace ID to response headers
        response.headers["X-Trace-ID"] = trace_id

        return response


async def catch_exceptions_middleware(request: Request, call_next):
    try:
        logger.info(f"Request: {request.method} {request.url}")
        response: Response = await call_next(request)
        logger.info(f"Response status: {response.status_code}")
        return response
    except Exception as e:
        logger.error(f"Unhandled exception: {e}\n{traceback.format_exc()}", exc_info=e)
        logger.error(
            f"Request method: {request.method}, URL: {request.url}, Headers: {request.headers}"
        )
        raise e from None


if env_vars.get("USE_PROD") != "true":
    logger.info(
        "Running in development mode. Middleware for catching exceptions is enabled."
    )
else:
    logger.info("Running in production mode.")

app.middleware("http")(catch_exceptions_middleware)
app.add_middleware(LoggingAndTraceIDMiddleware)
app.include_router(api_router)


@app.get(f"/api/v1/health")
async def health_check(db: Session = Depends(get_db_gen)):
    try:
        # logger.debug("Performing health check")
        # Attempt to fetch a single row to check database connectivity
        db.execute(TextClause("SELECT 1"))
        # logger.info("Health check successful")
        return {"status": "UP"}
    except Exception as e:
        logger.error(f"Database connection error: {e}", exc_info=e)
        return {"status": "DOWN", "failed": ["db_connection"]}

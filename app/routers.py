from fastapi import APIRouter

from app.endpoints import (
    auth,
    eval_routes,
    export,  # runs,
    gpt_crud_for_all,
    helpers_routes,
    passthrough,
    pricing,
    slim_runs,
    webhook,
)

api_router = APIRouter()
api_router.include_router(auth.router, tags=["auth"], prefix="/api/v1/a")
# switched from /api/v1/runs to /api/v1/con_runs
# api_router.include_router(runs.router, tags=["runs"], prefix="/api/v1/con_runs")
# switched from /api/v1/slim_runs to /api/v1/runs
api_router.include_router(slim_runs.router, tags=["Slim Runs"], prefix="/api/v1/runs")
api_router.include_router(
    helpers_routes.router, tags=["helper functionality"], prefix="/api/v1/helpers"
)
api_router.include_router(
    eval_routes.router, tags=["evaluations and evaluators"], prefix="/api/v1/e"
)
api_router.include_router(export.router, prefix="/api/v1/export", tags=["export"])
api_router.include_router(
    gpt_crud_for_all.router,
    prefix="/api/v1/admin-crud-for-all",
    tags=["AutoGen CRUDs"],
)
api_router.include_router(
    passthrough.router,
    prefix="/api/v1/passthrough",
    tags=["Pass through LLM models"],
)

api_router.include_router(
    webhook.router,
    prefix="/api/v1/webhooks",
    tags=["Webhook URLs"],
)

api_router.include_router(
    pricing.router,
    prefix="/api/v1/pricing",
    tags=["LLM Pricing API"],
)

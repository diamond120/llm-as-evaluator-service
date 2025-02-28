import openai
import logging
import anthropic
import google.api_core.exceptions as google_exceptions
from langchain_google_genai.chat_models import ChatGoogleGenerativeAIError

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("llm-failover")

API_KEY_VISIBLE_PREFIX = 6
API_KEY_VISIBLE_SUFFIX = 4
API_KEY_VISIBLE_MINIMUM = 2

def masked_key(key) -> str:
    prefix = API_KEY_VISIBLE_PREFIX
    suffix = API_KEY_VISIBLE_SUFFIX
    if len(key) <= prefix + suffix:
        prefix = suffix = API_KEY_VISIBLE_MINIMUM
    return f"{key[:prefix]}{'*' * (len(key) - prefix - suffix)}{key[-suffix:]}"

AVAILABLE_PROVIDERS = [
    {
        "provider": "openai_api",
        "api_key": "OPENAI_API_KEY",
        "default_model": "OPENAI_DEFAULT_MODEL",
    },
    {
        "provider": "google_api",
        "api_key": "GOOGLE_API_KEY",
        "default_model": "GOOGLE_DEFAULT_MODEL",
    },
    {
        "provider": "anthropic_api",
        "api_key": "ANTHROPIC_API_KEY",
        "default_model": "ANTHROPIC_DEFAULT_MODEL",
    }
]

WRONG_API_KEY_ERRORS = (
    openai.AuthenticationError,
    openai.PermissionDeniedError,
    ChatGoogleGenerativeAIError, #needs to filter with "API_KEY_INVALID"
    google_exceptions.PermissionDenied,
    anthropic.AuthenticationError,
    anthropic.PermissionDeniedError,
)

TEMPORARY_KEY_ERRORS = (
    openai.RateLimitError,
    google_exceptions.ResourceExhausted,
    anthropic.RateLimitError,
)

TEMPORARY_PROVIDER_ERRORS = (
    openai.InternalServerError,
    openai.APIConnectionError,
    google_exceptions.InternalServerError,
    google_exceptions.ServiceUnavailable,
    google_exceptions.DeadlineExceeded,
    anthropic.InternalServerError,
    anthropic.APIConnectionError,
)

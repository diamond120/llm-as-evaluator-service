from google.oauth2 import service_account
from googleapiclient.discovery import build

from common.constants import GOOGLE_API_CREDENTIALS_PATH


def build_services(
    service_account_json_secrets_path=None, services=["drive", "sheets"]
):
    scopes = {
        "drive": "https://www.googleapis.com/auth/drive",
        "sheets": "https://www.googleapis.com/auth/spreadsheets",
    }
    scope = [scopes[service] for service in services]
    service_account_json_key = (
        service_account_json_secrets_path or GOOGLE_API_CREDENTIALS_PATH
    )
    credentials = service_account.Credentials.from_service_account_file(
        filename=service_account_json_key, scopes=scope
    )
    services_versions = {
        "drive": "v3",
        "sheets": "v4",
    }
    services_dict = {}
    for service_name in services:
        version = services_versions.get(service_name)
        if not version:
            raise ValueError(f"Version for service '{service_name}' is not defined")
        service = build(service_name, version, credentials=credentials)
        services_dict[service_name] = service
    return services_dict

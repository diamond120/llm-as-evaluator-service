import os
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/"
CREDENTIALS_DIR = PROJECT_ROOT + "creds/"

GOOGLE_API_CREDENTIALS_PATH = PROJECT_ROOT + "credentials.json"

DATA_DIR = PROJECT_ROOT + "data/"

DEFAULT_EMAIL = "admintest@xxxx.com"

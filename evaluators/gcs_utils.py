import base64
import os
import json
import io
import datetime

from gevent.pool import Pool
from google.cloud import storage
from google.oauth2 import service_account
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from app.logging_config import logger


def get_gcs_client():
    """Initialize and return a Google Cloud Storage client."""
    if "GCS_CREDS_PATH" in os.environ:
        scope = ["https://www.googleapis.com/auth/devstorage.read_write"]
        service_account_json_key = os.environ["GCS_CREDS_PATH"]
        credentials = service_account.Credentials.from_service_account_file(
            filename=service_account_json_key, scopes=scope
        )
        return storage.Client(credentials=credentials)
    else:
        return storage.Client()


def parse_gcs_uri(gcs_uri):
    """Parse a GCS URI into bucket name and blob name."""
    if not gcs_uri.startswith("gcs://"):
        raise ValueError("Invalid GCS URI. It must start with 'gcs://'.")
    parts = gcs_uri[6:].split("/", 1)
    if len(parts) != 2:
        raise ValueError("Invalid GCS URI. It must contain both bucket and blob name.")
    return parts[0], parts[1]


def download_gcs_file(gcs_uri):
    """Download a file from Google Cloud Storage."""
    bucket_name, blob_name = parse_gcs_uri(gcs_uri)
    storage_client = get_gcs_client()
    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(blob_name)
    return blob.download_as_bytes(), blob.name


def encode_image_to_data_url(file_bytes, file_name):
    """Encode file bytes to a data URL."""
    file_base64 = base64.b64encode(file_bytes).decode("utf-8")
    file_extension = os.path.splitext(file_name)[1].lower()

    # Convert .jpg to .jpeg
    if file_extension == ".jpg":
        file_extension = ".jpeg"
    if file_extension not in [".jpeg", ".png"]:
        raise ValueError("Unsupported file format. Only JPEG and PNG are supported.")

    return f"data:image/{file_extension[1:]};base64,{file_base64}"


def get_gsc_image_as_data_url(uri):
    file_bytes, file_name = download_gcs_file(uri)
    data_url = encode_image_to_data_url(file_bytes, file_name)
    return data_url


def get_gsc_images_as_data_urls(uris):
    """Fetch a list of URIs and return their data URLs using gevent pool."""

    pool = Pool(10)  # Create a pool with a maximum of 10 greenlets
    logger.debug("Gevent Pool initialized with size 10")
    greenlets = [pool.spawn(get_gsc_image_as_data_url, uri) for uri in uris]
    pool.join(raise_error=True)
    data_urls = [greenlet.value for greenlet in greenlets if greenlet.value is not None]
    return data_urls

def get_gcp_service_json_file():
     # Get the file path from the environment variable
    gcs_creds_path = os.getenv('GCS_CREDS_PATH')

     # Check if the path exists and read the JSON file
    if gcs_creds_path:
        with open(gcs_creds_path, 'r') as f:
            gcp_service_account_info = json.load(f)  # Load the JSON data
    else:
        raise EnvironmentError("GCS_CREDS_PATH environment variable not set")

    return gcp_service_account_info


def get_google_drive_service():
    """Initializes and returns the Google Drive service."""
    # Path to the service account key file
    gcp_service_account_file = get_gcp_service_json_file()
    scopes = ['https://www.googleapis.com/auth/drive.readonly']
    
    # Authenticate using the service account
    creds = Credentials.from_service_account_info(gcp_service_account_file, scopes=scopes)
    service = build('drive', 'v3', credentials=creds)
    
    return service

def list_files_in_folder(folder_id, service, is_shared_drive=False, drive_id=None):
    """Lists all files and folders in a Google Drive folder, with support for shared drives."""
    query = f"'{folder_id}' in parents and trashed = false"

    try:
        if is_shared_drive and drive_id:
            results = service.files().list(
                q=query,
                fields="files(id, name, mimeType)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                driveId=drive_id,
                corpora='drive'
            ).execute()
        else:
            results = service.files().list(q=query, fields="files(id, name, mimeType)").execute()

        items = results.get('files', [])
        
        if not items:
            logger.warning("No items found. Check if the folder ID is correct and if the service account has access.")
        else:
            logger.info(f"Found {len(items)} items in folder {folder_id}.")
        return items
    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
        return []


def download_all_files_in_folder(folder_id, destination_folder, service, is_shared_drive=False, drive_id=None):
    """Downloads all files from a Google Drive folder, including nested folders, and returns a list of dictionaries with file paths and names."""
    if not os.path.exists(destination_folder):
        os.makedirs(destination_folder)

    items = list_files_in_folder(folder_id, service, is_shared_drive, drive_id)
    downloaded_files = []

    for item in items:
        if item['mimeType'] == 'application/vnd.google-apps.folder':
            # It's a folder, so recurse into it
            new_folder_path = os.path.join(destination_folder, item['name'])
            downloaded_files.extend(download_all_files_in_folder(item['id'], new_folder_path, service, is_shared_drive, drive_id))
        else:
            # It's a file, download it
            file_id = item['id']
            file_name = item['name']
            file_path = download_file(file_id, file_name, destination_folder, service)
            downloaded_files.append({'local_path': file_path, 'name': file_name})

    return downloaded_files

def download_file(file_id, file_name, destination_folder, service):
    """Download a file from Google Drive and return the path where the file is saved."""
    request = service.files().get_media(fileId=file_id)
    file_path = os.path.join(destination_folder, file_name)
    
    with io.FileIO(file_path, 'wb') as fh:
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            logger.info(f"Downloading {file_name}: {int(status.progress() * 100)}%")
    return file_path


def find_folder_id_by_path(path, drive_id, service):
    """Find a Google Drive folder ID by a path within a shared drive."""

    # Split the path into parts and ignore empty segments (e.g., leading slashes)
    parts = [part for part in path.split('/') if part]
    current_parent_id = drive_id  # Start at the root of the shared drive

    for part in parts:
        query = f"name = '{part}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        if current_parent_id:
            query += f" and '{current_parent_id}' in parents"

        results = service.files().list(
            q=query,
            fields="files(id, name)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            driveId=drive_id,
            corpora='drive'
        ).execute()
        folders = results.get('files', [])

        if not folders:
            logger.warning(f"No folder found with name {part}.")
            return None
        elif len(folders) > 1:
            logger.warning(f"Multiple folders found with name {part}. Consider specifying more unique names or checking the path.")
            return None
        else:
            current_parent_id = folders[0]['id']  # Move to the next part of the path

    logger.info(f"Folder ID for path '{path}': {current_parent_id}")
    return current_parent_id



class CloudStorageManager:
    def __init__(self):
        """Initializes the CloudStorageManager with a specific service account file."""
        gcp_service_account_info = get_gcp_service_json_file()
        self.storage_client = storage.Client.from_service_account_info(gcp_service_account_info)
    
    def upload_blob_signed_url(self, bucket_name, source_file_name, destination_folder):
        """Uploads a file to the bucket and returns a signed URL."""
        bucket = self.storage_client.bucket(bucket_name)
        base_directory = "temp_downloads"
        relative_path = os.path.relpath(source_file_name, base_directory)
        destination_path = f"{destination_folder}/{relative_path}".strip("/")
        blob = bucket.blob(destination_path)
        blob.upload_from_filename(source_file_name)
        
        # Generate a signed URL for the blob
        signed_url = blob.generate_signed_url(
            version="v4",
            expiration=datetime.timedelta(minutes=30),  # URL valid for 15 minutes
            method="GET"
        )
        
        logger.info(f"File {source_file_name} uploaded to {destination_path}.")
        logger.info(f"Signed URL: {signed_url}")
        return signed_url


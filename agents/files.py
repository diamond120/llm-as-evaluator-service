from google.cloud import storage
import json
import os

class CloudStorageManager:
    def __init__(self):
        """Initializes the CloudStorageManager with a specific service account file."""
        service_account_info = json.loads(os.getenv('SERVICE_JSON'))
        self.storage_client = storage.Client.from_service_account_info(service_account_info)

    def download_blob(self, bucket_name, source_blob_name, destination_file_name):
        """Downloads a blob from the bucket and returns the local path."""
        bucket = self.storage_client.bucket(bucket_name)
        blob = bucket.blob(source_blob_name)
        blob.download_to_filename(destination_file_name)
        print(f"Blob {source_blob_name} downloaded to {destination_file_name}.")
        return destination_file_name

    def upload_blob(self, bucket_name, source_file_name, destination_blob_name):
        """Uploads a file to the bucket as public and returns the URL."""
        bucket = self.storage_client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)
        blob.upload_from_filename(source_file_name)
        blob.make_public()
        public_url = blob.public_url
        print(f"File {source_file_name} uploaded to {destination_blob_name} and is publicly accessible at {public_url}.")
        return public_url

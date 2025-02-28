import re
from typing import Optional

from googleapiclient.discovery import Resource


def extract_file_id(file: str, is_url: bool = True) -> str:
    """Extract the file ID from a Google Drive file URL or ID.

    Args:
        file: The URL or ID of the file in Google Drive.
        is_url: A flag indicating whether the provided file is a URL. Default is True.

    Returns:
        The ID of the file.
    """
    if is_url:
        try:
            file_id = file.split("/d/")[1].split("/")[0]
            if not re.match(r"^[a-zA-Z0-9_-]+$", file_id):
                raise ValueError(
                    f"Invalid file ID: {file_id}. Please provide a valid Google Drive file ID."
                )
        except IndexError:
            raise ValueError(
                f"Invalid file URL: {file}. Please provide a valid Google Drive file URL."
            )
    else:
        if "/" in file:
            raise ValueError(
                f"Invalid file ID: {file}. Please provide a valid Google Drive file ID."
            )
        file_id = file
    return file_id


def extract_folder_id(folder: str, is_url: bool = True) -> str:
    """Extract the folder ID from a Google Drive folder URL or ID.

    Args:
        folder: The URL or ID of the folder in Google Drive.
        is_url: A flag indicating whether the provided folder is a URL. Default is True.

    Returns:
        The ID of the folder.
    """
    if is_url:
        try:
            folder_id = folder.split("/folders/")[1].split("?")[0]
            if not re.match(r"^[a-zA-Z0-9_-]+$", folder_id):
                raise ValueError(
                    f"Invalid folder ID: {folder_id}. Please provide a valid Google Drive folder ID."
                )
        except IndexError:
            raise ValueError(
                f"Invalid folder URL: {folder}. Please provide a valid Google Drive folder URL."
            )
    else:
        if "/" in folder:
            raise ValueError(
                f"Invalid folder ID: {folder}. Please provide a valid Google Drive folder ID."
            )
        folder_id = folder
    return folder_id

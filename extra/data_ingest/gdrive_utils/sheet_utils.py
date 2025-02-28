import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build


def download_sheet_as_df(service_account_path, sheet_id, sheet_name):
    # Authenticate with the service account
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = service_account.Credentials.from_service_account_file(
        service_account_path, scopes=scopes
    )
    service = build("sheets", "v4", credentials=creds)

    # Construct the range to read
    sheet_range = f"{sheet_name}!A:Z"  # Adjust the range A:Z as needed

    # Make the API request
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=sheet_id, range=sheet_range)
        .execute()
    )
    values = result.get("values", [])

    # Convert to a DataFrame
    if not values:
        print("No data found.")
        return pd.DataFrame()
    else:
        return pd.DataFrame(values[1:], columns=values[0])


def upload_df_to_sheet(service_account_path, sheet_id, sheet_name, df):
    """
    Uploads headers and data from a DataFrame to a Google Sheet.
    """
    # Authenticate with the service account
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = service_account.Credentials.from_service_account_file(
        service_account_path, scopes=scopes
    )
    service = build("sheets", "v4", credentials=creds)

    # Construct the range to write
    sheet_range = f"{sheet_name}!A:Z"  # Adjust the range A:Z as needed

    # Convert the DataFrame to a 2D list of values
    values = [df.columns.tolist()] + df.values.tolist()

    # Make the API request
    body = {"values": values}
    service.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range=sheet_range,
        valueInputOption="USER_ENTERED",
        body=body,
    ).execute()


def create_new_sheet_from_df(service_account_path, sheet_id, sheet_name, df):
    """
    Creates a new sheet and populates it with headers and data from a DataFrame.
    """
    # Authenticate with the service account
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = service_account.Credentials.from_service_account_file(
        service_account_path, scopes=scopes
    )
    service = build("sheets", "v4", credentials=creds)

    # Convert the DataFrame to a 2D list of values
    values = [df.columns.tolist()] + df.values.tolist()

    # Make the API request
    body = {"values": values}
    service.spreadsheets().values().append(
        spreadsheetId=sheet_id,
        range=sheet_name,
        valueInputOption="USER_ENTERED",
        body=body,
    ).execute()

import requests
import json
import time

# Import the payload configuration from the app's payload_config module
from tests.evaluator_payloads import payloads

# Base URL for the API endpoint
base_url = "https://llm-as-evaluator-develop.xxxx.com"

# Authorization token for API access
HEADER_TOKEN = ""

# Full URL for initiating runs
url = f"{base_url}/api/v1/runs/"

# Headers for the HTTP request
headers = {
    "Accept": "*/*",
    "User-Agent": "Thunder Client (https://www.thunderclient.com)",
    "Authorization": f"Bearer {HEADER_TOKEN}",
    "Content-Type": "application/json",
}

# Make a POST request to initiate runs with the specified payload
# Please check the payload from evaluator_payloads.payloads file
response = requests.request(
    "POST", url, headers=headers, data=json.dumps(payloads.payload_10)
)

# Parse the JSON response
response = response.json()
print(response)

# Extract the list of runs from the response
runs = response["runs"]

# Maximum number of attempts to poll the status of each run
max_attempts = 300

# Loop through each run to check its status
for run in runs:
    attempts = 1
    while attempts < max_attempts:
        run_id = run["run_id"]
        # Construct the URL to check the status of the specific run
        url = f"{base_url}/api/v1/runs/{run_id}/status"

        # Empty payload for the GET request
        payload = {}
        # Headers for the GET request
        headers = {"Authorization": f"Bearer {HEADER_TOKEN}"}

        # Make a GET request to check the status of the run
        response = requests.request("GET", url, headers=headers, data=payload)
        if response.status_code == 200:
            # Get the status from the response
            status = response.json().get("status")
            if status not in ["pending", "in_progress"]:
                # Print the status if the run is completed
                print(f"Run {run_id} completed with status: {status}")
                break
        else:
            # Print an error message if the status check fails
            print(
                f"Failed to get status for run {run_id}. Status code: {status_response.status_code}"
            )
            break
        # Wait for a second before polling again
        time.sleep(1)
        attempts += 1
        if attempts == max_attempts:
            # Print a message if the maximum number of polling attempts is reached
            print(f"Max polling attempts reached for run {run_id}.")

#!/usr/bin/env python3

import os
import pickle
import sys
from pathlib import Path
from typing import List

from google.cloud import secretmanager
from google.oauth2 import service_account

# Global configuration
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "crowdtransfer-mp")
GCP_REGION = os.getenv("GCP_REGION", "europe-west6")
PICKLE_FILENAME = "data_secrets.pkl"
GCP_CREDENTIALS_PATH = os.getenv("GCP_CREDENTIALS_PATH", "./var/gcp_access_key.json")

# Path configuration
SCRIPT_DIR = Path(__file__).parent
VAR_DIR = SCRIPT_DIR / "var"
PICKLE_PATH = VAR_DIR / PICKLE_FILENAME
CREDENTIALS_FILE = Path(GCP_CREDENTIALS_PATH)


def get_credentials() -> service_account.Credentials:
    """
    Retrieves credentials from the service account key file.

    Returns:
        service_account.Credentials: Google Cloud credentials

    Raises:
        FileNotFoundError: If the credentials file is not found
        ValueError: If the credentials file is invalid
    """
    try:
        if not CREDENTIALS_FILE.exists():
            raise FileNotFoundError(
                f"Credentials file not found at: {CREDENTIALS_FILE}. "
                "Please provide valid credentials file path in GCP_CREDENTIALS_PATH "
                "environment variable or place the file in the default location."
            )

        credentials = service_account.Credentials.from_service_account_file(str(CREDENTIALS_FILE))
        return credentials

    except FileNotFoundError as e:
        print(f"Error: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"Error while loading credentials: {str(e)}")
        sys.exit(1)


def get_secrets(
    client: secretmanager.SecretManagerServiceClient, debug_mode: bool = False, save_data: bool = True
) -> List[secretmanager.Secret]:
    """
    Retrieves all secrets from Google Secret Manager or from a local file.

    Args:
        client: Secret Manager client for making requests
        debug_mode: If True, reads data from file instead of Secret Manager
        save_data: If True, saves retrieved data to pickle file

    Returns:
        List[secretmanager.Secret]: List of Secret objects
    """
    # Create directory for data storage if it doesn't exist
    VAR_DIR.mkdir(exist_ok=True)

    secrets = []

    if debug_mode and PICKLE_PATH.exists():
        # Read data from pickle file in debug mode
        with open(PICKLE_PATH, "rb") as f:
            secrets = pickle.load(f)
        return secrets
    if debug_mode and not PICKLE_PATH.exists():
        return secrets

    # Form the project path
    project_path = f"projects/{GCP_PROJECT_ID}"

    try:
        # Get list of all secrets
        request = secretmanager.ListSecretsRequest(
            parent=project_path,
        )

        # Use pagination to get all secrets
        page_result = client.list_secrets(request=request)
        for secret in page_result:
            secrets.append(secret)

        if save_data:
            # Save retrieved data to pickle file
            with open(PICKLE_PATH, "wb") as f:
                pickle.dump(secrets, f)

        return secrets

    except Exception as e:
        print(f"Error while retrieving secrets: {e}")
        return []


def main():
    """
    Main function to demonstrate Secret Manager usage
    """
    # Get credentials
    credentials = get_credentials()

    # Initialize client with credentials
    client = secretmanager.SecretManagerServiceClient(credentials=credentials)

    # Get secrets and print their count
    secrets = get_secrets(client, debug_mode=True, save_data=True)
    print(f"Retrieved secrets: {len(secrets)}")


if __name__ == "__main__":
    main()

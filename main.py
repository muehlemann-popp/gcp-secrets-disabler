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
PICKLE_FILENAME = os.getenv("PICKLE_FILENAME", "data_secrets.pkl")
PICKLE_VERSIONS_FILENAME = os.getenv("PICKLE_FILENAME", "data_secrets_versions.pkl")
GCP_CREDENTIALS_PATH = os.getenv("GCP_CREDENTIALS_PATH", "./var/gcp_access_key.json")


# Options flags
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "false"
SAVE_DATA = os.getenv("SAVE_DATA", "true").lower() == "false"
FILE_MODE = os.getenv("FILE_MODE", "false").lower() == "true"

# Path configuration
SCRIPT_DIR = Path(__file__).parent
VAR_DIR = SCRIPT_DIR / "var"
PICKLE_PATH = VAR_DIR / PICKLE_FILENAME
PICKLE_VERSIONS_PATH = VAR_DIR / PICKLE_VERSIONS_FILENAME
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
    client: secretmanager.SecretManagerServiceClient, file_mode: bool = False, save_data: bool = True
) -> List[secretmanager.Secret]:
    """
    Retrieves all secrets from Google Secret Manager or from a local file.

    Args:
        client: Secret Manager client for making requests
        file_mode: If True, reads data from file instead of Secret Manager
        save_data: If True, saves retrieved data to pickle file

    Returns:
        List[secretmanager.Secret]: List of Secret objects
    """
    # Create directory for data storage if it doesn't exist
    VAR_DIR.mkdir(exist_ok=True)

    secrets = []

    if file_mode and PICKLE_PATH.exists():
        # Read data from pickle file in debug mode
        with open(PICKLE_PATH, "rb") as f:
            secrets = pickle.load(f)
        return secrets
    if file_mode and not PICKLE_PATH.exists():
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


def get_secrets_versions(
    client: secretmanager.SecretManagerServiceClient, file_mode: bool = False, save_data: bool = True
) -> list[list[secretmanager.SecretVersion]]:
    """
    Retrieves all versions for each secret from Google Secret Manager or from a local file.

    Args:
        client: Secret Manager client for making requests
        file_mode: If True, reads data from file instead of Secret Manager
        save_data: If True, saves retrieved data to pickle file

    Returns:
        list[list]: List of lists containing SecretVersions for each secret
    """
    # Create directory for data storage if it doesn't exist
    VAR_DIR.mkdir(exist_ok=True)

    secrets_versions = []

    if file_mode and PICKLE_VERSIONS_PATH.exists():
        # Read data from pickle file in debug mode
        with open(PICKLE_VERSIONS_PATH, "rb") as f:
            secrets_versions = pickle.load(f)
        return secrets_versions
    if file_mode and not PICKLE_VERSIONS_PATH.exists():
        return secrets_versions

    try:
        # Get list of all secrets first
        secrets = get_secrets(client, file_mode=False, save_data=False)

        # For each secret, get its versions
        for secret in secrets:
            versions = []
            request = secretmanager.ListSecretVersionsRequest(
                parent=secret.name,
            )

            # Use pagination to get all versions
            page_result = client.list_secret_versions(request=request)
            for version in page_result:
                versions.append(version)

            secrets_versions.append(versions)

        if save_data:
            # Save retrieved data to pickle file
            with open(PICKLE_VERSIONS_PATH, "wb") as f:
                pickle.dump(secrets_versions, f)

        return secrets_versions

    except Exception as e:
        print(f"Error while retrieving secret versions: {e}")
        return []


def secret_versions_disabling(
    client: secretmanager.SecretManagerServiceClient,
    versions: list[secretmanager.SecretVersion],
    dry_run: bool = True,
) -> None:
    """
    Disables all secret versions except the most recently created one.

    Args:
        client: Secret Manager client for making requests
        versions: List of secret versions to process
        dry_run: If True, only shows what would be changed without making actual changes
    """
    if len(versions) <= 1:
        return

    # Sort versions by creation time in descending order (newest first)
    sorted_versions = sorted(versions, key=lambda x: x.create_time, reverse=True)

    # Get the most recent version (will be kept enabled)
    latest_version = sorted_versions[0]
    # Get all other versions that need to be disabled
    versions_to_disable = sorted_versions[1:]

    print(f"Latest version to keep enabled: {latest_version.name}")
    print(f"Versions to disable: {len(versions_to_disable)}")

    if dry_run:
        return

    # Process each version that needs to be disabled
    for version in versions_to_disable:
        try:
            # Skip versions that are not in ENABLED state
            if version.state != secretmanager.SecretVersion.State.ENABLED:
                print(f"Skipping version {version.name}: already in {version.state} state")
                continue

            print(f"Disabling version: {version.name}")
            request = secretmanager.DisableSecretVersionRequest(name=version.name)
            client.disable_secret_version(request=request)
        except Exception as e:
            print(f"Error disabling version {version.name}: {str(e)}")


def main():
    """
    Main function to demonstrate Secret Manager usage
    """
    # Get credentials
    credentials = get_credentials()

    # Initialize client with credentials
    client = secretmanager.SecretManagerServiceClient(credentials=credentials)

    # Get secrets and print their count
    secrets = get_secrets(client, file_mode=FILE_MODE, save_data=SAVE_DATA)
    print(f"Retrieved secrets: {len(secrets)}")

    secrets_versions = get_secrets_versions(client, file_mode=FILE_MODE, save_data=SAVE_DATA)
    print(f"Retrieved secret versions: {sum(len(versions) for versions in secrets_versions)}")
    if secrets_versions:
        for group in secrets_versions:
            secret_versions_disabling(client, group, dry_run=DRY_RUN)


if __name__ == "__main__":
    main()

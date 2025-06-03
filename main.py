#!/usr/bin/env python3

import os
import pickle
import sys
from pathlib import Path
from typing import List

from google.cloud import secretmanager

# Global configuration
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "crowdtransfer-mp")
GCP_REGION = os.getenv("GCP_REGION", "europe-west6")
PICKLE_FILENAME = os.getenv("PICKLE_FILENAME", "data_secrets.pkl")
PICKLE_VERSIONS_FILENAME = os.getenv("PICKLE_FILENAME", "data_secrets_versions.pkl")

# Options flags
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"
SAVE_DATA = os.getenv("SAVE_DATA", "true").lower() == "true"
FILE_MODE = os.getenv("FILE_MODE", "false").lower() == "true"

# Path configuration
SCRIPT_DIR = Path(__file__).parent
VAR_DIR = SCRIPT_DIR / "var"
PICKLE_PATH = VAR_DIR / PICKLE_FILENAME
PICKLE_VERSIONS_PATH = VAR_DIR / PICKLE_VERSIONS_FILENAME


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
        for secret_item in page_result:
            secrets.append(secret_item)

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

    secrets_versions_data = []

    if file_mode and PICKLE_VERSIONS_PATH.exists():
        # Read data from pickle file in debug mode
        with open(PICKLE_VERSIONS_PATH, "rb") as f:
            secrets_versions_data = pickle.load(f)
        return secrets_versions_data
    if file_mode and not PICKLE_VERSIONS_PATH.exists():
        return secrets_versions_data

    try:
        # Get list of all secrets first
        secrets_list = get_secrets(client, file_mode=False, save_data=False)

        # For each secret, get its versions
        for secret_item in secrets_list:
            versions = []
            request = secretmanager.ListSecretVersionsRequest(
                parent=secret_item.name,
            )

            # Use pagination to get all versions
            page_result = client.list_secret_versions(request=request)
            for version in page_result:
                versions.append(version)

            secrets_versions_data.append(versions)

        if save_data:
            # Save retrieved data to pickle file
            with open(PICKLE_VERSIONS_PATH, "wb") as f:
                pickle.dump(secrets_versions_data, f)

        return secrets_versions_data

    except Exception as e:
        print(f"Error while retrieving secret versions: {e}")
        return []


def secret_versions_disabling(
    client: secretmanager.SecretManagerServiceClient,
    versions: list[secretmanager.SecretVersion],
    dry_run: bool = True,
) -> None:
    """
    Disables all enabled secret versions except the most recently created one.

    Args:
        client: Secret Manager client for making requests
        versions: List of secret versions to process
        dry_run: If True, only shows what would be changed without making actual changes
    """
    if len(versions) <= 1:
        if versions:
            print(f"Secret {versions[0].name.split('/versions/')[0]} has {len(versions)} version(s). No action needed.")
        else:
            print("No versions provided to process.")
        return

    # Sort versions by creation time in descending order (newest first)
    sorted_versions = sorted(versions, key=lambda x: x.create_time, reverse=True)

    # Get the most recent version (will be kept enabled)
    latest_version = sorted_versions[0]

    # Filter versions to get only enabled ones, excluding the latest version
    versions_to_disable = [
        version for version in sorted_versions[1:] if version.state == secretmanager.SecretVersion.State.ENABLED
    ]

    secret_base_name = latest_version.name.split("/versions/")[0]
    print(f"Processing secret: {secret_base_name}")
    print(f"Latest version to keep enabled: {latest_version.name}")
    if not versions_to_disable:
        print("No older enabled versions to disable.")
        return

    print(f"Enabled versions to disable: {len(versions_to_disable)}")
    for version in versions_to_disable:
        print(f"  - {version.name}")

    if dry_run:
        print("Dry run is enabled. No actual changes will be made.")
        return

    # Process each version that needs to be disabled
    for version in versions_to_disable:
        try:
            print(f"Disabling version: {version.name}")
            request = secretmanager.DisableSecretVersionRequest(name=version.name)
            client.disable_secret_version(request=request)
            print(f"Successfully disabled version: {version.name}")
        except Exception as e:
            print(f"Error disabling version {version.name}: {str(e)}")


def main():
    """
    Main function to demonstrate Secret Manager usage
    """
    print(f"Starting secret versions disabling process...")
    print(f"GCP Project ID: {GCP_PROJECT_ID}")
    print(f"Dry run: {DRY_RUN}")
    print(f"Save data: {SAVE_DATA}")
    print(f"File mode: {FILE_MODE}")

    try:
        # Initialize client. It will use Application Default Credentials.
        # google-github-actions/auth (with WIF) or GOOGLE_APPLICATION_CREDENTIALS (for local)
        # will provide the necessary credentials.
        client = secretmanager.SecretManagerServiceClient()
        print("Successfully initialized SecretManagerServiceClient.")
    except Exception as e:
        print(f"Failed to initialize SecretManagerServiceClient: {e}")
        sys.exit(1)

    # Get secrets and print their count
    secrets = get_secrets(client, file_mode=FILE_MODE, save_data=SAVE_DATA)
    print(f"Retrieved secrets: {len(secrets)}")

    if not secrets:
        print("No secrets found or retrieved. Exiting.")
        return

    secrets_versions_list = get_secrets_versions(client, file_mode=FILE_MODE, save_data=SAVE_DATA)
    print(f"Total groups of secret versions retrieved: {len(secrets_versions_list)}")
    # print(f"Retrieved secret versions (total count): {sum(len(versions) for versions in secrets_versions_list)}") # Ошибка если secrets_versions_list пустой

    if secrets_versions_list:
        for group in secrets_versions_list:
            if group:  # Убедимся, что группа версий не пуста
                secret_versions_disabling(client, group, dry_run=DRY_RUN)
            else:
                print("Encountered an empty group of versions.")
    else:
        print("No secret versions found or retrieved.")


if __name__ == "__main__":
    main()

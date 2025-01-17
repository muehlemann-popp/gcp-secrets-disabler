# GCP Secrets Disabler

A Python script for managing and cleaning up secret versions in Google Cloud Secret Manager. The script automatically disables older versions of secrets while keeping the latest version enabled.

## Description

This tool helps maintain Google Cloud Secret Manager by identifying and disabling outdated secret versions. It preserves the most recent version of each secret while disabling older versions, helping to maintain a clean and manageable secrets environment.

## How It Works

1. Authenticates with Google Cloud using service account credentials
2. Retrieves all secrets from the specified GCP project
3. For each secret, retrieves all its versions
4. Identifies the most recent version of each secret
5. Disables all older versions while keeping the latest version enabled
6. Optionally saves the retrieved data to local files for debugging purposes

## Environment Variables

The script uses the following environment variables:

- `GCP_PROJECT_ID` - Google Cloud project ID (default: "crowdtransfer-mp")
- `GCP_REGION` - Google Cloud region (default: "europe-west6")
- `GOOGLE_GHA_CREDS_PATH` - Path to GCP service account credentials file (default: "./var/gcp_access_key.json")
- `DRY_RUN` - Enable/disable dry run mode (default: "true")
- `SAVE_DATA` - Enable/disable saving data to pickle files (default: "true")
- `FILE_MODE` - Enable/disable reading data from local files instead of GCP (default: "false")
- `PICKLE_FILENAME` - Name of the file to store secrets data (default: "data_secrets.pkl")
- `PICKLE_VERSIONS_FILENAME` - Name of the file to store secret versions data (default: "data_secrets_versions.pkl")

## Local Setup and Installation

1. Make sure you have Python 3.12+ installed

2. Install poetry and project dependencies:
   ```bash
   task poetry:install
   ```

3. Set up your GCP project in gcloud:
   ```bash
   task gcloud:project:set
   ```

4. Verify your GCP project configuration:
   ```bash
   task gcloud:project:get
   ```

5. Place your GCP service account credentials file in `./var/gcp_access_key.json`

## Development and Debug Mode

The script supports a debug mode where it can save and load data from local files instead of making requests to GCP. This is controlled by the following environment variables:

- Set `SAVE_DATA=true` to save retrieved data to pickle files
- Set `FILE_MODE=true` to read data from local files instead of GCP
- Files are stored in the `./var` directory

To run the script in debug mode:
```bash
task py:run FILE_MODE=true
```

## ⚠️ Important: Production Run vs Dry Run ⚠️

### Dry Run Mode (Safe)
By default, the script runs in dry run mode (`DRY_RUN=true`). In this mode, it will:
- Show all actions that would be taken
- Not make any actual changes to your secrets
- Safe for testing and verification

To run in dry run mode:
```bash
task py:run DRY_RUN=true
```

### Production Mode (Active Changes)
When running with `DRY_RUN=false`, the script will:
- Actually disable older versions of secrets
- Make changes to your GCP Secret Manager
- Changes can be reverted if needed through the Google Cloud Platform web console

To run in production mode:
```bash
task py:run DRY_RUN=false
```

**⚠️ NOTE: Always run in dry run mode first to verify the changes that will be made. While secret version changes can be reverted through the GCP console if needed, it's best practice to verify the changes before applying them.**
# The Synapse Project

The Synapse Project is an automated pipeline for generative AI research that utilizes a GitOps methodology. It is designed to take a structured research task, query the Google Gemini API, and produce a formatted research document in Google Drive.

## Features

-   **Command-Line Interface:** Run the pipeline with arguments for flexible execution.
-   **Configurable Inputs:** Easily specify different research prompts and authentication keys.
-   **Google Cloud Integration:** Leverages Google Gemini for content generation and Google Drive/Docs for output.
-   **Shared Drive Support:** Correctly handles file creation in Google Shared Drives, which is a requirement for service accounts.
-   **Reliable Output:** Automatically saves a local Markdown copy of every generated report.
-   **User-Friendly Progress:** Displays a live progress indicator with an elapsed timer during API calls.

## Prerequisites

Before you begin, ensure you have the following:

1.  **Python 3.11+** installed.
2.  **Google Cloud SDK (`gcloud`)** installed and authenticated.
3.  A **Google Cloud Platform (GCP) Project**.
4.  A **Google Workspace account** that allows the creation of Shared Drives.
5.  A **Google Cloud Service Account** and a downloaded **JSON key file** for it.

---

## Setup and Configuration

This is a comprehensive guide to set up the project from scratch.

### Step 1: GCP Project & API Configuration

First, configure your Google Cloud project and enable the necessary APIs.

1.  **Set your active project:**
    Replace `your-project-id` with the ID of your GCP project (e.g., `tts-pipeline-project`).
    ```powershell
    gcloud config set project your-project-id
    ```

2.  **Enable required APIs:**
    This command enables all three APIs required for the pipeline to function.
    ```powershell
    gcloud services enable generativelanguage.googleapis.com drive.googleapis.com docs.googleapis.com
    ```

### Step 2: GCP IAM Permissions

The service account needs project-level permissions to use the enabled APIs. The **Editor** role is a straightforward way to grant these permissions.

1.  **Grant the Editor role:**
    Replace `your-project-id` and `your-service-account-email@...` with your actual values.
    ```powershell
    gcloud projects add-iam-policy-binding your-project-id --member="serviceAccount:your-service-account-email@your-project-id.iam.gserviceaccount.com" --role="roles/editor"
    ```

### Step 3: Google Drive Shared Drive Setup

**Why a Shared Drive?**
Service accounts do not have their own "My Drive" or storage quota. They cannot own files in a user's personal drive. Therefore, using a **Shared Drive** is mandatory, as files within it belong to the organization, allowing the service account to create and manage them.

1.  **Create a Shared Drive:**
    -   In Google Drive, navigate to **Shared drives** in the left-hand menu.
    -   Click **New** and give your Shared Drive a name (e.g., `Synapse Project Drive`).

2.  **Add the Service Account as a Manager:**
    -   Right-click the new Shared Drive and select **Manage members**.
    -   In the "Add people and groups" field, paste the email address of your service account.
    -   Ensure the role is set to **Manager**. This is critical for the script to have full control over file creation and management.
    -   Click **Done**.

3.  **Create an Output Folder and Get its ID:**
    -   Open your new Shared Drive.
    -   Create a folder inside it (e.g., `Deep Research results`).
    -   Open this new folder. The URL in your browser's address bar will look like this: `https://drive.google.com/drive/folders/1aBcDeFgHiJkLmNoPqRsTuVwXyZ_12345`.
    -   The final part of the URL (`1aBcDeFgHiJkLmNoPqRsTuVwXyZ_1234s`) is the **Folder ID**. Copy it for the next step.

### Step 4: Local Environment Setup

1.  **Clone the repository and navigate into it:**
    ```powershell
    git clone https://github.com/mayafudimaxionym/The-Synapse-Project.git
    cd The-Synapse-Project
    ```

2.  **Place your Service Account Key:**
    Copy your downloaded JSON key file into the root of the project directory (e.g., as `tts.json`).

3.  **Create and activate a virtual environment:**
    ```powershell
    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    ```

4.  **Install dependencies:**
    ```powershell
    pip install -r requirements.txt
    ```

5.  **Configure the `.env` file:**
    Create a file named `.env` in the project root and populate it with your specific values.

    ```env
    # .env

    # 1. Your Google Cloud Project ID.
    GOOGLE_CLOUD_PROJECT="tts-pipeline-project"

    # 2. The ID of the folder you created *inside* the Shared Drive.
    GOOGLE_DRIVE_FOLDER_ID="YOUR_SHARED_DRIVE_FOLDER_ID"

    # 3. Default path to the service account key file.
    GOOGLE_APPLICATION_CREDENTIALS="tts.json"

    # 4. The specific Gemini API model to use.
    GEMINI_API_MODEL="models/gemini-2.5-pro"
    ```

---

## Usage

The pipeline is executed via `run_pipeline.py`.

**Basic Execution:**
(Uses `prompt.json` and the key file specified in `.env`)
```powershell
py .\\scripts\\run_pipeline.py
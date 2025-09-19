# The Synapse Project

The Synapse Project is an automated pipeline for generative AI research that utilizes a GitOps methodology. It is designed to take a structured research task, query the Google Gemini API, and produce a formatted research document.

## Features

-   **Command-Line Interface:** Run the pipeline with arguments for flexible execution.
-   **Configurable Inputs:** Easily specify different research prompts and authentication keys.
-   **Google Cloud Integration:** Leverages Google Gemini for content generation and Google Drive/Docs for output.
-   **Reliable Output:** Automatically saves a local Markdown copy of every generated report, ensuring no data is lost.
-   **User-Friendly Progress:** Displays a live progress indicator with an elapsed timer during API calls.

## Prerequisites

Before you begin, ensure you have the following:

1.  **Python 3.11+** installed.
2.  A **Google Cloud Platform (GCP) Project**.
3.  In your GCP project, the following APIs must be **enabled**:
    -   Google Generative Language API (`generativelanguage.googleapis.com`)
    -   Google Drive API (`drive.googleapis.com`)
    -   Google Docs API (`docs.googleapis.com`)
4.  A **Google Cloud Service Account** with the `AI Platform User` role (or similar permissions for the Generative Language API).
5.  A **JSON key** downloaded for this service account.
6.  A **Google Drive Folder** where the output documents will be created. The service account's email address must be granted **"Editor"** access to this folder.

## Setup and Installation

1.  **Clone the repository:**
    ```powershell
    git clone https://github.com/mayafudimaxionym/The-Synapse-Project.git
    cd The-Synapse-Project
    ```

2.  **Create and activate a virtual environment:**
    ```powershell
    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    ```

3.  **Install the required dependencies:**
    ```powershell
    pip install -r requirements.txt
    ```

## Configuration

Configuration is managed through a `.env` file in the project's root directory.

1.  **Create the `.env` file:**
    Create a file named `.env` and add the following content.

    ```env
    # .env

    # 1. Google Cloud Project ID from your working project.
    GOOGLE_CLOUD_PROJECT="tts-pipeline-project"

    # 2. The ID of the Google Drive folder where reports will be saved.
    # Find it in the folder's URL: https://drive.google.com/drive/folders/YOUR_ID_HERE
    GOOGLE_DRIVE_FOLDER_ID="YOUR_GOOGLE_DRIVE_FOLDER_ID"

    # 3. (Optional) Default path to the service account key file.
    # Can be overridden with the --key-file command-line argument.
    GOOGLE_APPLICATION_CREDENTIALS="tts.json"

    # 4. The specific Gemini API model to use for generation.
    GEMINI_API_MODEL="models/gemini-2.5-pro"
    ```

2.  **Prompt Configuration (`prompt.json`)**
    The research task is defined in a JSON file (default: `prompt.json`). This file is structured to separate the **process** (instructions) from the final **product** (output format).

    -   `persona`: Defines the role the AI should adopt.
    -   `goals`: High-level objectives for the task.
    -   `instructions`: A step-by-step research process for the AI to follow.
    -   `constraints`: Rules and limitations for the AI's behavior.
    -   `output_format`: A detailed Markdown template describing the exact structure of the final document.

## Usage

The pipeline is executed via `run_pipeline.py`. You can specify the prompt and key files as command-line arguments.

**Basic Execution:**
(Uses `prompt.json` and the key file specified in `.env` or `tts.json` by default)
```powershell
py .\\scripts\\run_pipeline.py
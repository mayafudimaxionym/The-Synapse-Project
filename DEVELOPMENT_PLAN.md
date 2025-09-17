# Development Plan: Automated Research Pipeline

This document outlines the step-by-step plan to implement the automated research pipeline. It uses a direct architecture where GitHub Actions runs the core Python script.

**Technical Stack:**
* **Repository:** `https://github.com/mayafudimaxionym/The-Synapse-Project`
* **Local Environment:** Windows 11
* **Terminal:** PowerShell
* **Scripting Language:** Python

---

### Phase 1: Foundation & Setup

*(Goal: Prepare all accounts, repositories, and credentials.)*

* **Task 1.1: Clone Repo & Create Local Structure**
    1.  Open PowerShell and navigate to your working directory.
        ```powershell
        cd d:\Workarea\
        git clone [https://github.com/mayafudimaxionym/The-Synapse-Project.git](https://github.com/mayafudimaxionym/The-Synapse-Project.git)
        cd The-Synapse-Project
        ```
    2.  Create the project structure.
        ```powershell
        New-Item -ItemType Directory -Path "scripts", ".github\workflows" -Force
        New-Item -ItemType File -Path "prompt.json", "scripts\run_pipeline.py", "requirements.txt", ".github\workflows\pipeline.yml", ".gitignore", "README.md", "DEVELOPMENT_PLAN.md"
        ```

* **Task 1.2: Configure `.gitignore`**
    * Add the following content to your `.gitignore` file to prevent committing secrets.
        ```powershell
        Set-Content -Path ".gitignore" -Value "
        # Python virtual environment
        .venv/

        # Local secrets file (for local testing)
        service-account.json
        "
        ```

* **Task 1.3: Google Cloud & API Configuration**
    1.  Go to the [Google Cloud Console](https://console.cloud.google.com/).
    2.  Enable these APIs: **Generative Language API**, **Google Drive API**, **Google Docs API**.
    3.  Create an **API Key** for Gemini. Copy it.
    4.  Create a **Service Account** and download its JSON key file. Rename it to `service-account.json` and save it in your project root (`d:\Workarea\The-Synapse-Project\`).

* **Task 1.4: Secure Credential Management in GitHub**
    1.  In your GitHub repo, go to `Settings` > `Secrets and variables` > `Actions`.
    2.  Create two new repository secrets:
        * `GEMINI_API_KEY`: Paste the API Key.
        * `GCP_SA_KEY`: Paste the entire content of your `service-account.json` file.

* **Task 1.5: Google Drive Setup**
    1.  Create a new folder in Google Drive (e.g., "Automated AI Reports").
    2.  Share this folder with the service account's email address (found in `service-account.json`) and give it **"Editor"** permissions.

---

### Phase 2: The Python Automation Script

*(Goal: Create a local Python environment and write the core script.)*

* **Task 2.1: Set up Local Python Environment**
    1.  In your PowerShell terminal (at the project root), create a virtual environment:
        ```powershell
        python -m venv .venv
        ```
    2.  Activate it for your current session:
        ```powershell
        .\.venv\Scripts\Activate.ps1
        ```

* **Task 2.2: Define & Install Dependencies**
    1.  Add the required libraries to `requirements.txt`:
        ```powershell
        Set-Content -Path "requirements.txt" -Value "
        google-generativeai
        google-api-python-client
        google-auth-httplib2
        google-auth-oauthlib
        "
        ```
    2.  Install the libraries:
        ```powershell
        pip install -r requirements.txt
        ```

* **Task 2.3: Develop `scripts/run_pipeline.py`**
    * This is where you will write the Python code to connect the services. This script will be responsible for reading the prompt, calling Gemini, and creating the Google Doc.

---

### Phase 3: The GitHub Actions Workflow

*(Goal: Define the automation workflow that runs in the cloud.)*

* **Task 3.1: Create `pipeline.yml` Workflow**
    * Open `.github/workflows/pipeline.yml` and add this configuration.
    ```yaml
    name: 'Automated Research Pipeline'

    on:
      workflow_dispatch: # Allows manual runs
      schedule:
        - cron: '0 6 * * 1' # Runs every Monday at 06:00 UTC

    jobs:
      build-and-run:
        runs-on: ubuntu-latest
        steps:
          - name: Check out repository code
            uses: actions/checkout@v4

          - name: Set up Python 3.11
            uses: actions/setup-python@v5
            with:
              python-version: '3.11'

          - name: Install dependencies
            run: |
              python -m pip install --upgrade pip
              pip install -r requirements.txt
          
          - name: Run the Research Pipeline Script
            env:
              GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
              GCP_SA_KEY: ${{ secrets.GCP_SA_KEY }}
            run: python scripts/run_pipeline.py
    ```

---

### Phase 4: Testing and Deployment

*(Goal: Test locally, then deploy and monitor the automated workflow.)*

* **Task 4.1: Local Test (in PowerShell)**
    * Set temporary environment variables in your terminal to test your Python script locally.
        ```powershell
        $env:GEMINI_API_KEY = "PASTE_YOUR_GEMINI_API_KEY_HERE"
        $env:GCP_SA_KEY = Get-Content -Raw -Path ".\service-account.json"
        
        # Run the script
        python scripts\run_pipeline.py
        ```

* **Task 4.2: Commit and Push to GitHub**
    * Save and upload your work to activate the workflow.
        ```powershell
        git add .
        git commit -m "feat: Add initial pipeline structure and workflow files"
        git push origin main
        ```

* **Task 4.3: End-to-End Test**
    * Go to your GitHub repo's "Actions" tab and run the workflow manually. Check for errors and verify that the output document appears correctly in your Google Drive folder.

# The Synapse Project 🧠

Welcome to The Synapse Project! This repository contains an automated pipeline for generative AI research. It's designed to take a research prompt, execute it using Google's Gemini API, and save the formatted results directly to Google Drive.

---

## How It Works

This project uses a **GitOps** approach to AI. The entire research process is triggered and managed from this repository.

1.  **Prompt**: The research instructions are defined in the `prompt.json` file.
2.  **Trigger**: A [GitHub Action](https://github.com/mayafudimaxionym/The-Synapse-Project/actions) is configured to run on a schedule (e.g., weekly) or can be triggered manually.
3.  **Execution**: The action runs a Python script (`scripts/run_pipeline.py`) which:
    * Reads the `prompt.json` file.
    * Authenticates securely with the Google AI and Google Drive APIs.
    * Sends the prompt to the Gemini API to perform the research.
    * Creates a new Google Doc with the results in a designated Google Drive folder.
4.  **Output**: A new, cleanly formatted research report appears in your Google Drive, ready for use in other tools like NotebookLM.



---

## How to Use

### 1. Modifying the Research Prompt

To change the research topic, simply edit the `prompt.json` file in this repository. The next time the pipeline runs, it will use your updated instructions.

### 2. Running the Pipeline

* **Automatically**: The pipeline is scheduled to run automatically. You can change the schedule by editing the `cron` setting in the `.github/workflows/pipeline.yml` file.
* **Manually**:
    1.  Go to the **Actions** tab of this repository.
    2.  In the left sidebar, click on the **"Automated Research Pipeline"** workflow.
    3.  Click the **"Run workflow"** dropdown button and then the green **"Run workflow"** button to start a new run.

### 3. Viewing the Results

Check the Google Drive folder you configured during setup. A new document titled "Digital Fraud & Scam Intelligence Report - [Current Date]" will appear once the workflow is complete.

---

## Developer Setup

For instructions on how to set up the environment and credentials for the first time, please see the [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md) file.
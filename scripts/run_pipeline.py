import os
import json
import logging
from dotenv import load_dotenv
import google.auth
# highlight-start
import google.auth.exceptions # Import the correct exceptions module
# highlight-end
import google.generativeai as genai

# --- SETUP LOGGING ---
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# --- LOAD ENVIRONMENT VARIABLES ---
logging.info("Loading environment variables from .env file...")
load_dotenv()

# --- CONFIGURATION ---
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
PROMPT_PATH = os.path.join(ROOT_DIR, 'prompt.json')
OUTPUT_PATH = os.path.join(ROOT_DIR, 'output.txt')

def authenticate_and_configure():
    """Authenticates with Google and configures the Gemini API using .env."""
    project_id = os.getenv("GOOGLE_PROJECT_ID")
    if not project_id:
        logging.error("`GOOGLE_PROJECT_ID` not found in .env file or environment.")
        return False

    logging.info(f"Authenticating with Google Cloud for project: {project_id}")
    try:
        credentials, _ = google.auth.default(
            scopes=['https://www.googleapis.com/auth/cloud-platform']
        )
        # highlight-start
        # FIX: The 'project' argument is not needed and causes a TypeError.
        genai.configure(credentials=credentials)
        # highlight-end
        logging.info("✅ Successfully authenticated and configured Gemini API.")
        return True
    # highlight-start
    # FIX: Catch the correct exception from google.auth.exceptions
    except google.auth.exceptions.DefaultCredentialsError:
    # highlight-end
        logging.error("Authentication failed. Please run 'gcloud auth application-default login'")
        return False
    except Exception as e:
        logging.error(f"An unexpected error occurred during authentication: {e}")
        return False

def run_pipeline():
    """Executes the full AI pipeline with detailed logging."""
    
    if not authenticate_and_configure():
        return

    logging.info("🚀 Starting the research pipeline...")
    
    # 1. Read the prompt from JSON
    try:
        logging.info(f"Reading prompt from: {PROMPT_PATH}")
        with open(PROMPT_PATH, 'r', encoding='utf-8') as f:
            prompt_data = json.load(f)
            prompt_content = prompt_data['prompt']
        logging.debug(f"Prompt content loaded (first 100 chars): '{prompt_content[:100]}...'")
    except FileNotFoundError:
        logging.error(f"PIPELINE FAILED: Prompt file not found at {PROMPT_PATH}")
        return
    except json.JSONDecodeError:
        logging.error(f"PIPELINE FAILED: Could not decode JSON from {PROMPT_PATH}.")
        return
    except KeyError:
        logging.error(f"PIPELINE FAILED: 'prompt' key not found in {PROMPT_PATH}.")
        return

    # 2. Send prompt to Gemini API
    try:
        logging.info("Sending prompt to Gemini API...")
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        response = model.generate_content(prompt_content)
        generated_text = response.text
        logging.info("✅ Received response from Gemini.")
        logging.debug(f"Gemini response (first 100 chars): '{generated_text[:100]}...'")
        
    except Exception as e:
        logging.error(f"PIPELINE FAILED: An error occurred with the Gemini API: {e}")
        return

    # 3. Save the output to a local file
    try:
        logging.info(f"Saving output to: {OUTPUT_PATH}")
        with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
            f.write(generated_text)
        logging.info(f"✅ Pipeline complete. Output saved successfully.")
    except IOError as e:
        logging.error(f"PIPELINE FAILED: Could not write to output file: {e}")

if __name__ == "__main__":
    run_pipeline()
    
import os
import json # This import is now used
import logging
from dotenv import load_dotenv
import google.auth
import google.auth.exceptions
import google.generativeai as genai

# --- SETUP LOGGING ---
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# --- LOAD ENVIRONMENT VARIABLES ---
logging.info("Loading environment variables from .env file...")
load_dotenv()

# --- START TEMPORARY DEBUG BLOCK ---
if os.getenv("GOOGLE_API_KEY"):
    logging.warning("!!! DEBUG: The conflicting GOOGLE_API_KEY is still set in the environment!")
else:
    logging.info("--- DEBUG: GOOGLE_API_KEY is not set. This is correct.")
# --- END TEMPORARY DEBUG BLOCK ---

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
        genai.configure(credentials=credentials)
        logging.info("✅ Successfully authenticated and configured Gemini API.")
        return True
    except google.auth.exceptions.DefaultCredentialsError:
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
    
    # 1. Read the structured prompt from JSON
    try:
        logging.info(f"Reading prompt from: {PROMPT_PATH}")
        with open(PROMPT_PATH, 'r', encoding='utf-8') as f:
            prompt_data = json.load(f)
            # highlight-start
            # FIX: Convert the entire JSON object into a formatted string to use as the prompt
            prompt_content = json.dumps(prompt_data, indent=2)
            # highlight-end
        logging.debug(f"Prompt content loaded (first 100 chars): '{prompt_content[:100]}...'")
    except FileNotFoundError:
        logging.error(f"PIPELINE FAILED: Prompt file not found at {PROMPT_PATH}")
        return
    except json.JSONDecodeError:
        logging.error(f"PIPELINE FAILED: Could not decode JSON from {PROMPT_PATH}.")
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

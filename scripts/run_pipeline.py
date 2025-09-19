# scripts/run_pipeline.py

import os
import json
import logging
import time
import itertools
import threading
import argparse
from datetime import datetime
from dotenv import load_dotenv
import google.generativeai as genai
from google.oauth2 import service_account
from googleapiclient.discovery import build

# --- Configuration ---
# Setup basic logging to provide clear feedback to the user
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# --- Core Functions ---

def parse_arguments():
    """
    Parses command-line arguments for the pipeline.
    -h or --help will be automatically generated.
    """
    parser = argparse.ArgumentParser(
        description="Runs the Synapse Project AI research pipeline.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        '--prompt',
        type=str,
        default='prompt.json',
        help="Path to the JSON file containing the research prompt.\n(default: prompt.json)"
    )
    parser.add_argument(
        '--key-file',
        type=str,
        default=None,
        help=(
            "Path to the Google Cloud service account JSON key file.\n"
            "If not provided, the script will look for the GOOGLE_APPLICATION_CREDENTIALS\n"
            "variable in the .env file."
        )
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='output',
        help="Directory to save the local Markdown output file.\n(default: output)"
    )
    return parser.parse_args()

def authenticate_google_services(key_file_path):
    """
    Authenticates with Google services using the provided service account key.
    
    This function performs two separate authentications:
    1. Creates specific credentials for Drive/Docs API with required scopes.
    2. Configures the Gemini client, which automatically finds its credentials
       via the standard GOOGLE_APPLICATION_CREDENTIALS environment variable.

    Args:
        key_file_path (str): The path to the service account JSON key file.

    Returns:
        tuple: A tuple containing credentials for Drive/Docs and the configured
               generative model object, or (None, None) on failure.
    """
    try:
        if not key_file_path or not os.path.exists(key_file_path):
            logging.error(f"Service account key file not found at path: {key_file_path}")
            return None, None

        # --- Authentication for Google Drive & Docs API ---
        # These APIs require specific scopes to be defined.
        scopes = [
            'https://www.googleapis.com/auth/drive',
            'https://www.googleapis.com/auth/documents'
        ]
        drive_creds = service_account.Credentials.from_service_account_file(
            key_file_path, scopes=scopes)
        
        # --- Authentication for Generative AI (Gemini) API ---
        # This library is designed to automatically find and use the credentials
        # from the environment variable set by the google-auth library.
        # We do not need to pass credentials to it directly.
        model_name = os.getenv("GEMINI_API_MODEL")
        if not model_name:
            logging.error("GEMINI_API_MODEL not set in .env file.")
            return None, None
            
        generative_model = genai.GenerativeModel(model_name)
        
        logging.info(f"✅ Successfully authenticated and configured Gemini model: {model_name}")
        return drive_creds, generative_model

    except Exception as e:
        logging.error(f"An error occurred during authentication: {e}", exc_info=True)
        return None, None
    
def read_prompt(file_path):
    """Reads the research prompt from a JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            prompt_data = json.load(f)
        logging.info(f"Reading prompt from: {os.path.abspath(file_path)}")
        return prompt_data
    except FileNotFoundError:
        logging.error(f"Prompt file not found at {file_path}")
        return None
    except json.JSONDecodeError:
        logging.error(f"Error decoding JSON from {file_path}")
        return None

def _animate_waiting(stop_event):
    """Helper function to display a spinner animation with an elapsed timer."""
    start_time = time.time()
    for c in itertools.cycle(['|', '/', '-', '\\']):
        if stop_event.is_set():
            break
        elapsed_time = int(time.time() - start_time)
        minutes, seconds = divmod(elapsed_time, 60)
        timer_str = f"{minutes:02d}:{seconds:02d}"
        print(f'\rWaiting for Gemini API response {c} (Elapsed: {timer_str})', end='', flush=True)
        time.sleep(0.1)
    print('\r' + ' ' * 60 + '\r', end='', flush=True)

def generate_content(model, prompt_data):
    """
    Formats the prompt data into a string and generates content
    using the Gemini API, with a waiting indicator.
    """
    if not model or not prompt_data:
        return None
    try:
        # Format the complex JSON prompt into a single, well-structured string
        formatted_prompt = (
            f"**Persona:**\n{prompt_data.get('persona', {}).get('role', 'N/A')}\n\n"
            f"**Primary Goals:**\n"
            f"{'- ' + '\\n- '.join(prompt_data.get('goals', []))}\n\n"
            f"**Detailed Instructions:**\n"
            f"{'- ' + '\\n- '.join(prompt_data.get('instructions', []))}\n\n"
            f"**Constraints:**\n"
            f"{'- ' + '\\n- '.join(prompt_data.get('constraints', []))}\n\n"
            f"**Output Format:**\n{prompt_data.get('output_format', 'N/A')}"
        )
        
        logging.info("Sending formatted prompt to Gemini API...")
        
        # Start the waiting indicator in a separate thread
        stop_spinner = threading.Event()
        spinner_thread = threading.Thread(target=_animate_waiting, args=(stop_spinner,))
        spinner_thread.start()
        
        try:
            response = model.generate_content(formatted_prompt)
        finally:
            # Ensure the spinner stops, regardless of success or failure
            stop_spinner.set()
            spinner_thread.join()
        
        logging.info("Successfully received response from Gemini API.")
        return response.text
        
    except Exception as e:
        logging.error(f"An error occurred with the Gemini API: {e}", exc_info=True)
        return None

def save_output_locally(output_dir, content, timestamp_str):
    """Saves the generated content to a local Markdown file."""
    try:
        os.makedirs(output_dir, exist_ok=True)
        filename = f"research_output_{timestamp_str}.md"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logging.info(f"✅ Valuable output has been saved locally to: {filepath}")
        return filepath
    except Exception as e:
        logging.error(f"Could not save local file: {e}", exc_info=True)
        return None

def create_google_doc(credentials, folder_id, title, content):
    """Creates a new Google Doc with the generated content in a specific folder."""
    if not credentials or not folder_id:
        logging.warning("Skipping Google Doc creation: credentials or folder_id missing.")
        return None
    try:
        docs_service = build('docs', 'v1', credentials=credentials)
        drive_service = build('drive', 'v3', credentials=credentials)
        
        logging.info(f"Creating new Google Doc titled: '{title}'")
        
        doc = docs_service.documents().create(body={'title': title}).execute()
        doc_id = doc.get('documentId')
        
        requests = [{'insertText': {'location': {'index': 1}, 'text': content}}]
        docs_service.documents().batchUpdate(documentId=doc_id, body={'requests': requests}).execute()
            
        file = drive_service.files().get(fileId=doc_id, fields='parents').execute()
        previous_parents = ",".join(file.get('parents'))
        drive_service.files().update(
            fileId=doc_id,
            addParents=folder_id,
            removeParents=previous_parents,
            fields='id, parents').execute()

        doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
        logging.info(f"✅ Successfully created Google Doc.")
        logging.info(f"   URL: {doc_url}")
        return doc_url

    except Exception as e:
        logging.error(f"Failed to create Google Doc: {e}", exc_info=True)
        return None

def main():
    """Main function to orchestrate the research pipeline."""
    # Load .env file for variables not passed as arguments (e.g., model, folder_id)
    load_dotenv()
    args = parse_arguments()

    logging.info("🚀 Starting the research pipeline...")
    
    # Determine the key file path: prioritize command-line arg, then .env, then default
    key_file = args.key_file or os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or "tts.json"

    drive_creds, model = authenticate_google_services(key_file)
    if not drive_creds or not model:
        logging.critical("Pipeline halted due to authentication failure.")
        return

    prompt_content = read_prompt(args.prompt)
    if not prompt_content:
        logging.critical("Pipeline halted: Could not read prompt file.")
        return

    generated_text = generate_content(model, prompt_content)
    if not generated_text:
        logging.critical("Pipeline halted: Failed to generate content.")
        return

    # --- Permanent local save ---
    timestamp_for_files = datetime.now().strftime('%Y%m%d_%H%M%S')
    save_output_locally(args.output_dir, generated_text, timestamp_for_files)

    # --- Google Doc creation (optional but recommended) ---
    folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
    doc_title = f"Synapse Project Research - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    doc_url = create_google_doc(drive_creds, folder_id, doc_title, generated_text)
    
    if doc_url:
        logging.info("🏁 Research pipeline finished successfully.")
    else:
        logging.warning("🏁 Research pipeline finished, but Google Doc creation failed or was skipped.")

if __name__ == "__main__":
    main()

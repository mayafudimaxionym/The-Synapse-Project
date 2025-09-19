# scripts/run_pipeline.py

import os
import json
import logging
import time
import itertools
import threading
from datetime import datetime
from dotenv import load_dotenv
import google.generativeai as genai
from google.oauth2 import service_account
from googleapiclient.discovery import build

# --- Configuration ---
# Setup basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Load environment variables from .env file
load_dotenv()

# --- Main Pipeline Logic ---

def authenticate_google_services():
    """
    Authenticates with Google services using the service account key
    specified by GOOGLE_APPLICATION_CREDENTIALS.
    
    Returns:
        tuple: A tuple containing credentials for Drive/Docs and the configured
               generative model object, or (None, None) on failure.
    """
    try:
        # This variable is now automatically used by google-auth library
        key_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if not key_path or not os.path.exists(key_path):
            logging.error(f"Service account key file not found at path: {key_path}")
            return None, None

        # Define the required scopes
        scopes = [
            'https://www.googleapis.com/auth/drive',
            'https://www.googleapis.com/auth/documents'
        ]
        
        # Create credentials for Drive/Docs API
        drive_creds = service_account.Credentials.from_service_account_file(
            key_path, scopes=scopes)
        
        # Configure the Generative AI client (it uses the same env var automatically)
        genai.configure(transport='rest') # Use REST transport for broader compatibility
        
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

def read_prompt(file_path='prompt.json'):
    """Reads the research prompt from a JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            prompt_data = json.load(f)
        logging.info(f"Reading prompt from: {os.path.abspath(file_path)}")
        logging.debug(f"Prompt content loaded (first 100 chars): {str(prompt_data)[:100]}...")
        return prompt_data
    except FileNotFoundError:
        logging.error(f"Prompt file not found at {file_path}")
        return None
    except json.JSONDecodeError:
        logging.error(f"Error decoding JSON from {file_path}")
        return None

def _animate_waiting(stop_event):
    """Helper function to display a spinner animation."""
    for c in itertools.cycle(['|', '/', '-', '\\']):
        if stop_event.is_set():
            break
        print(f'\rWaiting for Gemini API response {c}', end='', flush=True)
        time.sleep(0.1)
    # Clear the line after stopping
    print('\r' + ' ' * 40 + '\r', end='', flush=True)

def generate_content(model, prompt_data):
    """
    Formats the prompt data into a string and generates content
    using the Gemini API, with a waiting indicator.
    """
    if not model or not prompt_data:
        return None
    try:
        # Format the complex JSON prompt into a single string
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
        
        # --- NEW: Waiting Indicator Logic ---
        stop_spinner = threading.Event()
        spinner_thread = threading.Thread(target=_animate_waiting, args=(stop_spinner,))
        spinner_thread.start()
        
        try:
            response = model.generate_content(formatted_prompt)
        finally:
            # Ensure the spinner stops even if an error occurs
            stop_spinner.set()
            spinner_thread.join()
        
        logging.info("Successfully received response from Gemini API.")
        return response.text
        
    except Exception as e:
        logging.error(f"An error occurred with the Gemini API: {e}", exc_info=True)
        return None




def create_google_doc(credentials, folder_id, title, content):
    """Creates a new Google Doc with the generated content in a specific folder."""
    if not credentials or not folder_id:
        return None
    try:
        # Build the Google Docs and Drive services
        docs_service = build('docs', 'v1', credentials=credentials)
        drive_service = build('drive', 'v3', credentials=credentials)
        
        logging.info(f"Creating new Google Doc titled: '{title}'")
        
        # 1. Create the document
        doc_body = {'title': title}
        doc = docs_service.documents().create(body=doc_body).execute()
        doc_id = doc.get('documentId')
        
        # 2. Insert the content
        requests = [
            {'insertText': {'location': {'index': 1}, 'text': content}}
        ]
        docs_service.documents().batchUpdate(
            documentId=doc_id, body={'requests': requests}).execute()
            
        # 3. Move the document to the specified folder
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

def _animate_waiting(stop_event):
    """
    Helper function to display a spinner animation with an elapsed timer.
    """
    start_time = time.time()
    for c in itertools.cycle(['|', '/', '-', '\\']):
        if stop_event.is_set():
            break
        elapsed_time = int(time.time() - start_time)
        # Format as MM:SS
        minutes, seconds = divmod(elapsed_time, 60)
        timer_str = f"{minutes:02d}:{seconds:02d}"
        
        print(f'\rWaiting for Gemini API response {c} (Elapsed: {timer_str})', end='', flush=True)
        time.sleep(0.1)
    # Clear the line after stopping
    print('\r' + ' ' * 60 + '\r', end='', flush=True)

if __name__ == "__main__":
    main()

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
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

# --- Configuration ---
# Configure logging to provide informative output to the console.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# --- Core Functions ---

def parse_arguments():
    """
    Parses command-line arguments for the pipeline.
    Help text is automatically generated via -h or --help.
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
    """
    try:
        if not key_file_path or not os.path.exists(key_file_path):
            logging.error(f"Service account key file not found at path: {key_file_path}")
            return None, None

        # Create credentials for Drive API with the required scopes.
        drive_scopes = ['https://www.googleapis.com/auth/drive']
        drive_creds = service_account.Credentials.from_service_account_file(key_file_path, scopes=drive_scopes)
        
        # Configure the Gemini API client. It will automatically use the same credentials.
        model_name = os.getenv("GEMINI_API_MODEL")
        if not model_name:
            logging.error("GEMINI_API_MODEL variable not found in .env file.")
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
        logging.error(f"Prompt file not found: {file_path}")
        return None
    except json.JSONDecodeError:
        logging.error(f"Error decoding JSON from file: {file_path}")
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
    """Formats the prompt and generates content using the Gemini API."""
    if not model or not prompt_data: return None
    try:
        # Convert the complex JSON prompt into a single, well-structured string.
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
        
        stop_spinner = threading.Event()
        spinner_thread = threading.Thread(target=_animate_waiting, args=(stop_spinner,))
        spinner_thread.start()
        
        try:
            response = model.generate_content(formatted_prompt)
        finally:
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
        
        logging.info(f"✅ Output has been saved locally to: {filepath}")
        return filepath
    except Exception as e:
        logging.error(f"Could not save local file: {e}", exc_info=True)
        return None

def create_google_doc(credentials, folder_id, title, local_md_path):
    """
    Creates a new Google Doc by uploading a local Markdown file and letting
    Google Drive convert it. This is a robust workaround for Docs API permission issues.
    """
    if not credentials or not folder_id:
        logging.warning("Skipping Google Doc creation: credentials or folder_id missing.")
        return None
    if not local_md_path or not os.path.exists(local_md_path):
        logging.error(f"Skipping Google Doc creation: local file not found at {local_md_path}")
        return None
        
    try:
        drive_service = build('drive', 'v3', credentials=credentials, cache_discovery=False)
        
        logging.info(f"Uploading local file '{local_md_path}' to create Google Doc...")
        
        # Metadata for the new file on Google Drive.
        # The mimeType tells Drive to convert the uploaded file into a Google Doc.
        file_metadata = {
            'name': title,
            'parents': [folder_id],
            'mimeType': 'application/vnd.google-apps.document'
        }
        
        # Media object for the file upload, specifying the source file's mime type.
        media = MediaFileUpload(
            local_md_path,
            mimetype='text/markdown',
            resumable=True
        )
        
        # Execute the upload and conversion.
        file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink',
            supportsAllDrives=True
        ).execute()

        doc_url = file.get('webViewLink')
        logging.info(f"✅ Successfully created Google Doc via file upload.")
        logging.info(f"   URL: {doc_url}")
        return doc_url

    except Exception as e:
        logging.error(f"Failed to create Google Doc via file upload: {e}", exc_info=True)
        return None

def main():
    """Main function to orchestrate the research pipeline."""
    load_dotenv()
    args = parse_arguments()

    logging.info("🚀 Starting the research pipeline...")
    
    key_file = args.key_file or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

    drive_creds, model = authenticate_google_services(key_file)
    if not drive_creds or not model:
        logging.critical("Pipeline halted: authentication failure.")
        return

    prompt_content = read_prompt(args.prompt)
    if not prompt_content:
        logging.critical("Pipeline halted: could not read prompt file.")
        return

    generated_text = generate_content(model, prompt_content)
    if not generated_text:
        logging.critical("Pipeline halted: failed to generate content.")
        return

    timestamp_for_files = datetime.now().strftime('%Y%m%d_%H%M%S')
    # The local file is now essential for the upload process.
    local_filepath = save_output_locally(args.output_dir, generated_text, timestamp_for_files)

    folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
    doc_title = f"Synapse Project Research - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    # Pass the path of the locally saved file to the creation function.
    doc_url = create_google_doc(drive_creds, folder_id, doc_title, local_filepath)
    
    if doc_url:
        logging.info("🏁 Research pipeline finished successfully.")
    else:
        logging.warning("🏁 Research pipeline finished, but Google Doc creation failed or was skipped.")

if __name__ == "__main__":
    main()
    
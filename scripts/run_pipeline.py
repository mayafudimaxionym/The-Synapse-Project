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

# New imports for web scraping
import requests
from bs4 import BeautifulSoup

import google.generativeai as genai
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

# --- Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# --- Web Content Fetching ---

def fetch_article_content(urls):
    """
    Fetches and extracts the main text content from a list of URLs.
    
    Args:
        urls (list): A list of URL strings.

    Returns:
        str: A single string containing the formatted content of all articles.
    """
    all_articles_content = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    for i, url in enumerate(urls, 1):
        try:
            logging.info(f"Fetching content from: {url}")
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

            soup = BeautifulSoup(response.text, 'lxml')
            
            # Extract text from common article tags, then join and clean it
            text_parts = [p.get_text() for p in soup.find_all(['p', 'h1', 'h2', 'h3', 'li'])]
            article_text = ' '.join(text_parts).strip()
            
            # Format for the LLM prompt
            article_entry = (
                f"--- Article {i} ---\n"
                f"URL: {url}\n"
                f"Content:\n{article_text}\n"
                f"--- End of Article {i} ---\n\n"
            )
            all_articles_content.append(article_entry)

        except requests.exceptions.RequestException as e:
            logging.warning(f"Could not fetch URL {url}. Error: {e}")
            all_articles_content.append(f"--- Article {i} ---\nURL: {url}\nContent: FAILED TO RETRIEVE\n--- End of Article {i} ---\n\n")

    return "".join(all_articles_content)

# --- Core Functions (parse_arguments, authenticate_google_services, read_prompt, _animate_waiting remain the same) ---
def parse_arguments():
    # ... (no changes here)
    parser = argparse.ArgumentParser(description="Runs the Synapse Project AI research pipeline.",formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--prompt',type=str,default='prompt.json',help="Path to the JSON file containing the research prompt.\n(default: prompt.json)")
    parser.add_argument('--key-file',type=str,default=None,help=("Path to the Google Cloud service account JSON key file.\n""If not provided, the script will look for the GOOGLE_APPLICATION_CREDENTIALS\n""variable in the .env file."))
    parser.add_argument('--output-dir',type=str,default='output',help="Directory to save the local Markdown output file.\n(default: output)")
    return parser.parse_args()
def authenticate_google_services(key_file_path):
    # ... (no changes here)
    try:
        if not key_file_path or not os.path.exists(key_file_path):
            logging.error(f"Service account key file not found at path: {key_file_path}")
            return None, None
        drive_scopes = ['https://www.googleapis.com/auth/drive']
        drive_creds = service_account.Credentials.from_service_account_file(key_file_path, scopes=drive_scopes)
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
    # ... (no changes here)
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
    # ... (no changes here)
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


def generate_content(model, prompt_data, articles_text):
    """Formats the prompt with fetched article content and generates the report."""
    if not model or not prompt_data: return None
    try:
        # Combine the instructions with the fetched content
        formatted_prompt = (
            f"**Persona:**\n{prompt_data.get('persona', {}).get('role', 'N/A')}\n\n"
            f"**Primary Goals:**\n"
            f"{'- ' + '\\n- '.join(prompt_data.get('goals', []))}\n\n"
            f"**Instructions:**\n"
            f"{'- ' + '\\n- '.join(prompt_data.get('instructions', []))}\n\n"
            f"**Constraints:**\n"
            f"{'- ' + '\\n- '.join(prompt_data.get('constraints', []))}\n\n"
            f"**Source Material to Analyze:**\n"
            f"Please base your entire report on the following article content:\n\n{articles_text}\n\n"
            f"**Required Output Format:**\n{prompt_data.get('output_format', 'N/A')}"
        )
        
        logging.info("Sending prompt with fetched content to Gemini API...")
        
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

# --- save_output_locally and create_google_doc remain the same ---
def save_output_locally(output_dir, content, timestamp_str):
    # ... (no changes here)
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
    # ... (no changes here)
    if not credentials or not folder_id:
        logging.warning("Skipping Google Doc creation: credentials or folder_id missing.")
        return None
    if not local_md_path or not os.path.exists(local_md_path):
        logging.error(f"Skipping Google Doc creation: local file not found at {local_md_path}")
        return None
    try:
        drive_service = build('drive', 'v3', credentials=credentials, cache_discovery=False)
        logging.info(f"Uploading local file '{local_md_path}' to create Google Doc...")
        file_metadata = {'name': title,'parents': [folder_id],'mimeType': 'application/vnd.google-apps.document'}
        media = MediaFileUpload(local_md_path,mimetype='text/markdown',resumable=True)
        file = drive_service.files().create(body=file_metadata,media_body=media,fields='id, webViewLink',supportsAllDrives=True).execute()
        doc_url = file.get('webViewLink')
        logging.info(f"✅ Successfully created Google Doc via file upload.")
        logging.info(f"   URL: {doc_url}")
        return doc_url
    except Exception as e:
        logging.error(f"Failed to create Google Doc via file upload: {e}", exc_info=True)
        return None

def main():
    """Main function to orchestrate the new two-phase research pipeline."""
    load_dotenv()
    args = parse_arguments()

    logging.info("🚀 Starting the research pipeline...")
    
    key_file = args.key_file or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

    drive_creds, model = authenticate_google_services(key_file)
    if not drive_creds or not model:
        logging.critical("Pipeline halted: authentication failure.")
        return

    # Phase 1: Read prompt and URLs
    prompt_data = read_prompt(args.prompt)
    if not prompt_data:
        logging.critical("Pipeline halted: could not read prompt file.")
        return
        
    source_urls = prompt_data.get("source_articles")
    if not source_urls:
        logging.critical("Pipeline halted: 'source_articles' key with a list of URLs not found in prompt file.")
        return
        
    # Phase 2: Fetch content from URLs
    articles_content = fetch_article_content(source_urls)
    if not articles_content:
        logging.warning("Could not fetch content from any source URLs. The report may be empty or incomplete.")

    # Phase 3: Generate report based on fetched content
    generated_text = generate_content(model, prompt_data, articles_content)
    if not generated_text:
        logging.critical("Pipeline halted: failed to generate content.")
        return

    timestamp_for_files = datetime.now().strftime('%Y%m%d_%H%M%S')
    local_filepath = save_output_locally(args.output_dir, generated_text, timestamp_for_files)

    # Phase 4: Upload to Google Drive
    folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
    doc_title = f"Synapse Project Research - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    doc_url = create_google_doc(drive_creds, folder_id, doc_title, local_filepath)
    
    if doc_url:
        logging.info("🏁 Research pipeline finished successfully.")
    else:
        logging.warning("🏁 Research pipeline finished, but Google Doc creation failed or was skipped.")

if __name__ == "__main__":
    main()
    
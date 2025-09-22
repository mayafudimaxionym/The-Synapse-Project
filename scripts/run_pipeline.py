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

# Web scraping and Search imports
import requests
from bs4 import BeautifulSoup
from googleapiclient.discovery import build as build_google_api

# Gemini and Drive imports
import google.generativeai as genai
from google.oauth2 import service_account
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

# --- KEY FIX: Load environment variables at the very beginning of the script ---
# This ensures all imported libraries and subsequent code can see the variables.
load_dotenv()

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

# --- NEW: Web Search Function ---
def perform_web_search(search_queries, api_key, cse_id, num_results=5):
    """
    Performs a Google search for a list of queries and returns the top URL results.
    """
    logging.info(f"Performing web search for {len(search_queries)} queries...")
    service = build_google_api("customsearch", "v1", developerKey=api_key)
    all_urls = []
    
    for query in search_queries:
        try:
            logging.info(f"  - Searching for: '{query}'")
            res = service.cse().list(q=query, cx=cse_id, num=num_results).execute()
            if 'items' in res:
                urls = [item['link'] for item in res['items']]
                all_urls.extend(urls)
        except HttpError as e:
            logging.error(f"  - HTTP Error during search for '{query}': {e}")
        except Exception as e:
            logging.error(f"  - An unexpected error occurred during search: {e}")
            
    # Remove duplicate URLs
    unique_urls = list(dict.fromkeys(all_urls))
    logging.info(f"Found {len(unique_urls)} unique URLs from search.")
    return unique_urls

# --- Web Content Fetching ---
def fetch_article_content(urls):
    """
    Fetches and extracts the main text content from a list of URLs.
    """
    all_articles_content = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    for i, url in enumerate(urls, 1):
        try:
            logging.info(f"Fetching content from: {url}")
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'lxml')
            text_parts = [p.get_text() for p in soup.find_all(['p', 'h1', 'h2', 'h3', 'li'])]
            article_text = ' '.join(text_parts).strip()
            article_entry = (f"--- Article {i} ---\n" f"URL: {url}\n" f"Content:\n{article_text}\n" f"--- End of Article {i} ---\n\n")
            all_articles_content.append(article_entry)
        except requests.exceptions.RequestException as e:
            logging.warning(f"Could not fetch URL {url}. Error: {e}")
            all_articles_content.append(f"--- Article {i} ---\nURL: {url}\nContent: FAILED TO RETRIEVE\n--- End of Article {i} ---\n\n")
    return "".join(all_articles_content)

# --- Core Functions ---
def parse_arguments():
    """Parses command-line arguments for the pipeline."""
    parser = argparse.ArgumentParser(description="Runs the Synapse Project AI research pipeline.",formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--prompt',type=str,default='prompt.json',help="Path to the JSON file containing the research prompt.\n(default: prompt.json)")
    parser.add_argument('--key-file',type=str,default=None,help=("Path to the Google Cloud service account JSON key file.\n""If not provided, the script will look for the GOOGLE_APPLICATION_CREDENTIALS\n""variable in the .env file."))
    parser.add_argument('--output-dir',type=str,default='output',help="Directory to save the local Markdown output file.\n(default: output)")
    return parser.parse_args()

def authenticate_google_services(key_file_path):
    """Authenticates with Google services using the provided service account key."""
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

def generate_content(model, prompt_data, articles_text):
    """Formats the prompt with fetched article content and generates the report."""
    if not model or not prompt_data: return None
    try:
        formatted_prompt = (f"**Persona:**\n{prompt_data.get('persona', {}).get('role', 'N/A')}\n\n" f"**Primary Goals:**\n" f"{'- ' + '\\n- '.join(prompt_data.get('goals', []))}\n\n" f"**Instructions:**\n" f"{'- ' + '\\n- '.join(prompt_data.get('instructions', []))}\n\n" f"**Constraints:**\n" f"{'- ' + '\\n- '.join(prompt_data.get('constraints', []))}\n\n" f"**Source Material to Analyze:**\n" f"Please base your entire report on the following article content:\n\n{articles_text}\n\n" f"**Required Output Format:**\n{prompt_data.get('output_format', 'N/A')}")
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
    """Creates a new Google Doc by uploading a local Markdown file."""
    if not credentials or not folder_id:
        logging.warning("Skipping Google Doc creation: credentials or folder_id missing.")
        return None
    if not local_md_path or not os.path.exists(local_md_path):
        logging.error(f"Skipping Google Doc creation: local file not found at {local_md_path}")
        return None
    try:
        drive_service = build_google_api('drive', 'v3', credentials=credentials, cache_discovery=False)
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
    """Main function to orchestrate the new multi-phase research pipeline."""
    args = parse_arguments()

    logging.info("🚀 Starting the research pipeline...")
    
    # Get Search API credentials from .env
    api_key = os.getenv("GOOGLE_API_KEY")
    cse_id = os.getenv("CUSTOM_SEARCH_ENGINE_ID")
    if not api_key or not cse_id:
        logging.critical("Pipeline halted: GOOGLE_API_KEY or CUSTOM_SEARCH_ENGINE_ID not found in .env file.")
        return

    # Authenticate Gemini and Drive/Docs services
    key_file = args.key_file or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    drive_creds, model = authenticate_google_services(key_file)
    if not drive_creds or not model:
        logging.critical("Pipeline halted: authentication failure.")
        return

    # Phase 1: Read prompt and get search queries
    prompt_data = read_prompt(args.prompt)
    if not prompt_data:
        logging.critical("Pipeline halted: could not read prompt file.")
        return
        
    search_queries = prompt_data.get("search_queries")
    if not search_queries:
        logging.critical("Pipeline halted: 'search_queries' key not found in prompt file.")
        return
        
    # Phase 2: Perform web search to get URLs
    source_urls = perform_web_search(search_queries, api_key, cse_id)
    if not source_urls:
        logging.critical("Pipeline halted: Web search returned no results.")
        return

    # Phase 3: Fetch content from URLs
    articles_content = fetch_article_content(source_urls)
    if not articles_content:
        logging.warning("Could not fetch content from any source URLs. The report may be empty or incomplete.")

    # Phase 4: Generate report based on fetched content
    generated_text = generate_content(model, prompt_data, articles_content)
    if not generated_text:
        logging.critical("Pipeline halted: failed to generate content.")
        return

    # Phase 5: Save locally and upload to Google Drive
    timestamp_for_files = datetime.now().strftime('%Y%m%d_%H%M%S')
    local_filepath = save_output_locally(args.output_dir, generated_text, timestamp_for_files)

    folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
    doc_title = f"Synapse Project Research - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    doc_url = create_google_doc(drive_creds, folder_id, doc_title, local_filepath)
    
    if doc_url:
        logging.info("🏁 Research pipeline finished successfully.")
    else:
        logging.warning("🏁 Research pipeline finished, but Google Doc creation failed or was skipped.")

if __name__ == "__main__":
    main()
    
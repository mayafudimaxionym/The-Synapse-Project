import os
import json
import datetime
from dotenv import load_dotenv
import google.generativeai as genai
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# --- CONFIGURATION ---
# Load environment variables from .env file for local development
load_dotenv()

# Get credentials and configuration from environment variables
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# GCP_SA_KEY_STR = os.getenv("GCP_SA_KEY")
GOOGLE_DRIVE_FOLDER_ID = "1EOvPuiodi_Fb2KDa5B6IOMQBzUtIsjqt"

# Path to the prompt file
PROMPT_FILE_PATH = "prompt.json"

# --- AUTHENTICATION ---
def authenticate():
    """Handles authentication for Google APIs."""
    print("Authenticating with Google services...")
    
    # Gemini API
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not found in environment variables.")
    genai.configure(api_key=GEMINI_API_KEY)
    print("Gemini API configured.")

    # Google Drive & Docs API
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        service_account_file = os.path.join(script_dir, '..', 'service-account.json')
        with open(service_account_file, 'r') as f:
            gcp_sa_key_dict = json.load(f)

        creds = Credentials.from_service_account_info(
            gcp_sa_key_dict,
            scopes=[
                "https://www.googleapis.com/auth/drive",
                "https://www.googleapis.com/auth/documents"
            ]
        )
        drive_service = build("drive", "v3", credentials=creds)
        docs_service = build("docs", "v1", credentials=creds)
        print("Google Drive and Docs APIs configured.")
        return drive_service, docs_service
    except FileNotFoundError:
        raise ValueError("service-account.json not found.")
    except json.JSONDecodeError:
        raise ValueError("GCP_SA_KEY is not a valid JSON string.")
    except Exception as e:
        raise RuntimeError(f"Failed to authenticate with Google Drive/Docs: {e}")


# --- CORE LOGIC ---
def run_pipeline(drive_service, docs_service):
    """Executes the main research and reporting pipeline."""
    print("\nStarting the research pipeline...")

    # 1. Read the research prompt
    print(f"Reading prompt from '{PROMPT_FILE_PATH}'...")
    try:
        with open(PROMPT_FILE_PATH, "r") as f:
            prompt_data = json.load(f)
        prompt_content = json.dumps(prompt_data)
    except FileNotFoundError:
        raise FileNotFoundError(f"Error: The prompt file was not found at '{PROMPT_FILE_PATH}'")
    except json.JSONDecodeError:
        raise ValueError(f"Error: Could not decode JSON from '{PROMPT_FILE_PATH}'")

    # 2. Execute the prompt with Gemini
    print("Sending prompt to Gemini API...")
    model = genai.GenerativeModel('gemini-1.5-pro-latest')
    response = model.generate_content(prompt_content)
    print("Received response from Gemini.")

    # 3. Create the Google Doc
    create_google_doc(drive_service, docs_service, response.text)


def create_google_doc(drive_service, docs_service, content):
    """Creates a new Google Doc with the research results."""
    if not GOOGLE_DRIVE_FOLDER_ID:
        raise ValueError("GOOGLE_DRIVE_FOLDER_ID not found. Please set it in your .env file or environment.")

    print("\nCreating Google Doc...")
    
    # Format the title with the current date
    today = datetime.date.today()
    doc_title = f"Digital Fraud & Scam Intelligence Report - {today.strftime('%B %Y')}"

    # Create the document in the specified folder
    file_metadata = {
        "name": doc_title,
        "mimeType": "application/vnd.google-apps.document",
        "parents": [GOOGLE_DRIVE_FOLDER_ID]
    }
    
    try:
        document = drive_service.files().create(body=file_metadata).execute()
        doc_id = document.get("id")
        print(f"Successfully created Google Doc titled: '{doc_title}' (ID: {doc_id})")

        # Add the content to the document
        requests = [
            {
                'insertText': {
                    'location': {
                        'index': 1,
                    },
                    'text': content
                }
            }
        ]
        docs_service.documents().batchUpdate(documentId=doc_id, body={'requests': requests}).execute()
        print("Successfully added Gemini content to the document.")

    except Exception as e:
        raise RuntimeError(f"An error occurred while creating the Google Doc: {e}")


# --- MAIN EXECUTION ---
if __name__ == "__main__":
    try:
        drive_service, docs_service = authenticate()
        run_pipeline(drive_service, docs_service)
        print("\n✅ Pipeline executed successfully!")
    except (ValueError, FileNotFoundError, RuntimeError) as e:
        print(f"\n❌ Pipeline failed: {e}")
# diagnose.py
import os
import logging
from dotenv import load_dotenv
import google.auth
import google.generativeai as genai
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

# --- Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def run_gemini_diagnostics():
    """Checks Gemini API authentication."""
    print("\n--- Running Gemini Authentication Diagnostics ---")
    try:
        credentials, _ = google.auth.default()
        if not credentials.service_account_email:
             raise ValueError("Failed to load credentials as a service account.")
        print(f"✅ [1/2] Authenticated as service account: {credentials.service_account_email}")

        list(genai.list_models())
        print("✅ [2/2] Successfully listed Gemini models.")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False

def test_google_drive_upload():
    """Tests Google Drive file upload permissions with Shared Drive support."""
    print("\n--- Running Google Drive Permissions Diagnostics ---")
    file_id_to_delete = None
    drive_service = None
    try:
        key_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")

        if not key_path or not folder_id:
            raise ValueError("Required .env variables not found.")
        
        scopes = ['https://www.googleapis.com/auth/drive']
        creds = service_account.Credentials.from_service_account_file(key_path, scopes=scopes)
        drive_service = build('drive', 'v3', credentials=creds, cache_discovery=False)
        print(f"✅ [1/3] Authenticated for Drive API.")

        test_file_path = 'test.test'
        if not os.path.exists(test_file_path):
            with open(test_file_path, 'w') as f: f.write('test')
            print("   - Created temporary 'test.test' file.")

        file_metadata = {'name': 'synapse_diagnostic_upload.txt', 'parents': [folder_id]}
        media = MediaFileUpload(test_file_path, mimetype='text/plain')
        
        uploaded_file = drive_service.files().create(
            body=file_metadata, media_body=media, fields='id', supportsAllDrives=True).execute()
        
        file_id_to_delete = uploaded_file.get('id')
        if not file_id_to_delete:
            raise Exception("File created but did not return an ID.")
        print(f"✅ [2/3] File uploaded successfully (ID: {file_id_to_delete}).")

        drive_service.files().delete(fileId=file_id_to_delete, supportsAllDrives=True).execute()
        file_id_to_delete = None
        print("✅ [3/3] Cleanup successful.")
        return True

    except HttpError as e:
        print(f"❌ FAILED: An API error occurred.")
        print(f"   Details: {e.content.decode()}")
        return False
    except Exception as e:
        print(f"❌ FAILED: An unexpected error occurred.")
        print(f"   ERROR: {e}")
        return False
    finally:
        if file_id_to_delete and drive_service:
            print("--- Failsafe cleanup ---")
            try:
                drive_service.files().delete(fileId=file_id_to_delete, supportsAllDrives=True).execute()
            except Exception: pass

def test_google_docs_creation():
    """
    Performs a minimal test to check Google Docs API creation permissions.
    """
    print("\n--- Running Google Docs Creation Diagnostics ---")
    try:
        key_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if not key_path:
            raise ValueError("GOOGLE_APPLICATION_CREDENTIALS not found in .env file.")

        print(f"✅ [1/2] Using key file: {key_path}")

        scopes = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/documents']
        credentials = service_account.Credentials.from_service_account_file(key_path, scopes=scopes)
        
        docs_service = build('docs', 'v1', credentials=credentials, cache_discovery=False)
        
        doc_body = {'title': 'Synapse Minimal API Test'}
        doc = docs_service.documents().create(body=doc_body).execute()
        doc_id = doc.get('documentId')
        
        print(f"✅ [2/2] Successfully created a temporary Google Doc (ID: {doc_id}).")
        
        # Cleanup the created doc
        drive_service = build('drive', 'v3', credentials=credentials, cache_discovery=False)
        drive_service.files().delete(fileId=doc_id, supportsAllDrives=True).execute()
        print("   - Cleanup successful.")
        return True

    except HttpError as e:
        print(f"❌ FAILED: The Docs API returned an error.")
        print(f"   Details: {e.content.decode()}")
        return False
    except Exception as e:
        print(f"❌ FAILED: An unexpected script error occurred.")
        print(f"   ERROR: {e}")
        return False

def main():
    """Runs all diagnostic checks sequentially."""
    print("--- Starting Full Diagnostics for Synapse Project ---")
    load_dotenv()
    
    gemini_ok = run_gemini_diagnostics()
    drive_ok = test_google_drive_upload()
    docs_ok = test_google_docs_creation()

    print("\n--- Diagnostics Summary ---")
    print(f"Gemini API Authentication: {'✅ SUCCESS' if gemini_ok else '❌ FAILED'}")
    print(f"Google Drive Permissions:  {'✅ SUCCESS' if drive_ok else '❌ FAILED'}")
    print(f"Google Docs Creation:      {'✅ SUCCESS' if docs_ok else '❌ FAILED'}")
    
    if gemini_ok and drive_ok and docs_ok:
        print("\n✅ All systems are configured correctly. The main pipeline should run successfully.")
    else:
        print("\n❌ Please review the error messages above. The issue is likely related to the FAILED checks.")
        if not docs_ok:
            print("   The 'Google Docs Creation' failure often points to an organizational policy")
            print("   in Google Workspace blocking service accounts. Please contact your administrator.")


if __name__ == "__main__":
    main()
    
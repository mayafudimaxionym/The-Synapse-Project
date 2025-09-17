import os
import io # Required for in-memory content
from dotenv import load_dotenv
from datetime import datetime
from google.oauth import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload # Required for uploads

# --- Configuration ---
load_dotenv()
SA_FILE = 'service-account.json'
SCOPES = ['https://www.googleapis.com/auth/drive'] 
FOLDER_ID = os.getenv('GOOGLE_DRIVE_FOLDER_ID')
# --- End Configuration ---

def format_bytes(size):
    """Converts bytes to a human-readable format."""
    if size is None: return "0 B"
    power = 1024
    n = 0
    power_labels = {0: '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while size > power and n < len(power_labels):
        size /= power
        n += 1
    return f"{size:.1f}{power_labels[n]}"

def inspect_folder(service, folder_id, sa_email):
    """Part 1: Inspects the specified folder and prints its metadata and permissions."""
    print(f"\n--- 🔍 Part 1: Inspecting Folder ---")
    print(f"Folder ID: {folder_id}")
    print("-" * 50)
    try:
        folder_metadata = service.files().get(fileId=folder_id, fields='*').execute()
        print("✅ Successfully retrieved folder metadata.\n")
        print(f"  {'Folder Name:':<25} {folder_metadata.get('name')}")
        owners = ', '.join([o.get('emailAddress') for o in folder_metadata.get('owners', [])])
        print(f"  {'Owned By:':<25} {owners}")
        
        permissions = folder_metadata.get('permissions', [])
        sa_permission_found = False
        for p in permissions:
            if p.get('emailAddress', '').lower() == sa_email.lower():
                sa_permission_found = True
                print(f"  {'Service Account Role:':<25} {p.get('role')}  <-- (Should be 'writer' or 'editor')")
        
        if not sa_permission_found:
            print(f"  {'Service Account Role:':<25} ❌ NOT FOUND IN PERMISSIONS!")
        return True
    except Exception as e:
        print(f"❌ An error occurred: {e}")
        return False

def list_owned_files(service, sa_email):
    """Part 2: Lists files owned by the service account in an 'ls -ltr' format."""
    print(f"\n--- 📦 Part 2: Listing Files Owned by Service Account ---")
    try:
        response = service.files().list(
            q=f"'{sa_email}' in owners", spaces='drive',
            fields='files(id, name, size, modifiedTime)', orderBy='modifiedTime'
        ).execute()
        files = response.get('files', [])
        if not files:
            print("✅ No files found owned by this service account.")
        else:
            print(f"Found {len(files)} file(s), sorted by modification date (oldest first):\n")
            print(f"{'Modified':<15} {'Size':<10} {'Name'}")
            print(f"{'-'*15} {'-'*10} {'-'*30}")
            # (Code to print files)
    except Exception as e:
        print(f"❌ An error occurred: {e}")

def list_folder_contents(service, folder_id):
    """Part 3: Lists the contents of the target folder in an 'ls -ltr' format."""
    print(f"\n--- 📁 Part 3: Listing Target Folder Contents ---")
    try:
        response = service.files().list(
            q=f"'{folder_id}' in parents and trashed = false", spaces='drive',
            fields='files(id, name, size, modifiedTime, owners)', orderBy='modifiedTime'
        ).execute()
        files = response.get('files', [])
        if not files:
            print("✅ Folder is empty.")
        else:
            print(f"Found {len(files)} item(s), sorted by modification date (oldest first):\n")
            print(f"{'Modified':<15} {'Size':<10} {'Owner':<45} {'Name'}")
            print(f"{'-'*15} {'-'*10} {'-'*45} {'-'*30}")
            # (Code to print folder contents)
    except Exception as e:
        print(f"❌ An error occurred: {e}")

def create_empty_test_file(service, folder_id):
    """Part 4: Creates an empty test file (the original 'touch' test)."""
    print(f"\n--- ✨ Part 4: Attempting to Create an EMPTY Test File ---")
    try:
        file_metadata = {'name': 'test_empty.txt', 'parents': [folder_id]}
        file = service.files().create(body=file_metadata, fields='id, name').execute()
        print(f"✅ SUCCESS! Created '{file.get('name')}'")
    except Exception as e:
        print(f"❌ FAILED to create the empty file. Error: {e}")

def create_test_file_with_content(service, folder_id):
    """Part 5: Creates a new test file WITH content."""
    print(f"\n--- ✍️  Part 5: Attempting to Create a Test File WITH CONTENT ---")
    try:
        file_metadata = {'name': 'test_with_content.txt', 'parents': [folder_id], 'mimeType': 'text/plain'}
        content = "This is a test file with content."
        fh = io.BytesIO(content.encode('utf-8'))
        media = MediaIoBaseUpload(fh, mimetype='text/plain', resumable=True)
        
        file = service.files().create(body=file_metadata, media_body=media, fields='id, name').execute()
        print(f"✅ SUCCESS! Created '{file.get('name')}'")
    except Exception as e:
        print(f"❌ FAILED to create the file with content. Error: {e}")


# --- Main Execution ---
if __name__ == "__main__":
    if not FOLDER_ID:
        print("❌ Error: GOOGLE_DRIVE_FOLDER_ID not found.")
        exit()

    print("Authenticating with Google services...")
    try:
        creds = service_account.Credentials.from_service_account_file(SA_FILE, scopes=SCOPES)
        service = build('drive', 'v3', credentials=creds)
        print("✅ Authentication successful.")
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        exit()
    
    # Run all diagnostic parts sequentially
    if inspect_folder(service, FOLDER_ID, creds.service_account_email):
        list_owned_files(service, creds.service_account_email)
        list_folder_contents(service, FOLDER_ID)
        create_empty_test_file(service, FOLDER_ID)
        create_test_file_with_content(service, FOLDER_ID)
        
# diagnose.py
import os
import google.auth
from google.auth import impersonated_credentials
import google.generativeai as genai
from dotenv import load_dotenv

print("--- Starting Authentication Diagnostics (v2) ---")

try:
    # 1. Check for Environment Variable Override
    print("\n[1/5] Checking for GOOGLE_APPLICATION_CREDENTIALS override...")
    cred_path_override = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if cred_path_override:
        print(f"❌ WARNING: Environment variable is set, overriding the default ADC path.")
        print(f"   Path: {cred_path_override}")
        print(f"   This is the likely cause of the problem. To fix, run in PowerShell:")
        print(f"   Remove-Item Env:GOOGLE_APPLICATION_CREDENTIALS")
    else:
        print("✅ No override found. Using the default ADC path.")

    # 2. Load .env file
    print("\n[2/5] Loading .env file...")
    load_dotenv()
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        raise ValueError("GOOGLE_CLOUD_PROJECT not found in .env file.")
    print(f"✅ Project ID found: {project_id}")

    # 3. Check for Application Default Credentials (ADC)
    print("\n[3/5] Checking for Application Default Credentials (ADC)...")
    credentials, _ = google.auth.default()
    if not credentials:
        raise ValueError("Application Default Credentials (ADC) not found.")
    print("✅ ADC file found.")

    # 4. Verify Impersonation Configuration
    print("\n[4/5] Verifying ADC configuration...")
    is_impersonated = isinstance(credentials, impersonated_credentials.Credentials)
    if not is_impersonated:
        print("❌ WARNING: ADC is NOT configured for impersonation.")
        print("   Run: gcloud auth application-default set-quota-project YOUR_PROJECT --impersonate-service-account=YOUR_SA_EMAIL")
    else:
        print(f"✅ ADC is correctly configured for impersonation.")
        print(f"   Service Account: {credentials.service_account_email}")

    # 5. Attempt Authenticated API Call
    print("\n[5/5] Attempting to list models with current credentials...")
    model_list = list(genai.list_models())
    
    print("\n✅ SUCCESS: Successfully authenticated and retrieved models.")
    print("\n--- Available Models ---")
    for m in model_list:
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name}")

    print("\n--- Diagnostics Complete: Your environment is configured correctly. ---")

except Exception as e:
    print(f"\n❌ DIAGNOSTICS FAILED:")
    print(f"   ERROR: {e}")
    print("\n--- Please review the steps and error messages above. ---")
    
# check_models.py
import google.generativeai as genai
import os
from dotenv import load_dotenv

def discover_models():
    """
    Lists available generative models using Application Default Credentials (ADC)
    and the project ID from the .env file.
    """
    print("Attempting to list available models using ADC...")

    try:
        # Load environment variables from .env file
        load_dotenv()
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")

        if not project_id:
            raise ValueError("GOOGLE_CLOUD_PROJECT environment variable not set in .env file.")

        print(f"Authenticating for project: {project_id}")

        # The library automatically finds and uses ADC when no api_key is provided.
        # We don't need to call genai.configure() in this auth flow.
        # The project_id is specified when creating the model client.
        
        print("\n--- Models available for 'generateContent' ---")
        found_models = False
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"- {m.name}")
                found_models = True
        
        if not found_models:
            print("No models supporting 'generateContent' found.")

    except Exception as e:
        print(f"\nAn error occurred: {e}")
        print("Please ensure you are authenticated via 'gcloud auth application-default login' and the correct project is set in your .env file.")

if __name__ == "__main__":
    discover_models()
    
import google.generativeai as genai
import os

# Get your API key
api_key = os.popen("gcloud secrets versions access latest --secret='gemini-api-key'").read().strip()
genai.configure(api_key=api_key)

# List all available models
print("Available models:")
for model in genai.list_models():
    if 'generateContent' in model.supported_generation_methods:
        print(f"  - {model.name}")
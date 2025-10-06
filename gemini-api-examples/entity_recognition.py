import google.generativeai as genai
import os
import json

def recognize_entities(text: str) -> dict:
    """Recognizes entities in the input text using the Gemini Pro model."""

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set.")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-pro-latest')

    prompt = f"""Extract the entities from the following text.
Recognize the following entity types:
- Persons
- Locations
- Organizations
- Dates
- Events
- Phone numbers
- Emails

Return the result as a JSON object with a key for each entity type.

Text: {text}
"""

    response = model.generate_content(prompt)
    # The model might return the JSON in a code block, so I need to clean it.
    cleaned_json = response.text.strip().replace('```json', '').replace('```', '')
    return json.loads(cleaned_json)


if __name__ == "__main__":
    sample_text = """
    John Doe, the CEO of Acme Inc., will be in New York on Monday, October 28, 2025
    for the annual Acme conference. He can be reached at john.doe@acmeinc.com or
    at 555-123-4567.
    """
    entities = recognize_entities(sample_text)
    print(f"Text: {sample_text}")
    print("Recognized Entities:")
    print(json.dumps(entities, indent=2))

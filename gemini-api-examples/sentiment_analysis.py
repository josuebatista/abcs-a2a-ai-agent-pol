import google.generativeai as genai
import os

def analyze_sentiment(text: str) -> str:
    """Analyzes the sentiment of the input text using the Gemini Pro model."""

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set.")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-pro-latest')

    prompt = f"""Analyze the sentiment of the following text and return one of the following:
- Positive
- Negative
- Neutral

Text: {text}
"""

    response = model.generate_content(prompt)
    return response.text


if __name__ == "__main__":
    sample_text = "I am very happy with the new product. It's amazing!"
    sentiment = analyze_sentiment(sample_text)
    print(f"Text: {sample_text}")
    print(f"Sentiment: {sentiment}")

    sample_text_2 = "The weather is okay today."
    sentiment_2 = analyze_sentiment(sample_text_2)
    print(f"Text: {sample_text_2}")
    print(f"Sentiment: {sentiment_2}")

    sample_text_3 = "I am very disappointed with the service."
    sentiment_3 = analyze_sentiment(sample_text_3)
    print(f"Text: {sample_text_3}")
    print(f"Sentiment: {sentiment_3}")

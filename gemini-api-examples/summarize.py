import google.generativeai as genai
import os

def summarize_text(text: str) -> str:
    """Summarizes the input text using the Gemini Pro model."""

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set.")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-pro-latest')

    prompt = f"""Summarize the following text:

    {text}
    """

    response = model.generate_content(prompt)
    return response.text


if __name__ == "__main__":
    sample_text = """
    Jupiter is the fifth planet from the Sun and the largest in the Solar System.
    It is a gas giant with a mass one-thousandth that of the Sun, but two-and-a-half times
    that of all the other planets in the Solar System combined. Jupiter is one of the brightest
    objects visible to the naked eye in the night sky, and has been known to ancient
    civilizations since before recorded history. It is named after the Roman god Jupiter.
    When viewed from Earth, Jupiter can be bright enough for its reflected light to cast
    shadows, and is on average the third-brightest natural object in the night sky after
    the Moon and Venus.
    """
    summary = summarize_text(sample_text)
    print("Summary:")
    print(summary)
"""Step 2 - Content transformation with an LLM API.

Sends the book sheet to a generative AI model and returns a podcast script.
The API key is read from the GEMINI_API_KEY environment variable
(loaded from the .env file in main.py).
"""

from google import genai

MODEL = "gemini-3.8-flash"  # free-tier model from the official quickstart

# Podcast styles the user can choose: label -> (length, how it should sound).
STYLES = {
    "Conversational (about 5 min)": (
        "about 5 minutes (around 600 words)",
        "warm, friendly and easy to follow, like talking to a curious friend",
    ),
    "Reflective and literary (about 5 min)": (
        "about 5 minutes (around 600 words)",
        "thoughtful and calm, with a literary feel, giving space to ideas and images",
    ),
    "Quick summary (about 2 min)": (
        "about 2 minutes (around 250 words)",
        "short, clear and direct, only the essentials",
    ),
}
DEFAULT_STYLE = "Conversational (about 5 min)"

# Why these rules: the output is read aloud, so symbols would be spoken; and
# the "only use the sheet" rule avoids invented facts about a real book.
PROMPT_TEMPLATE = """You are a warm, thoughtful podcast host.
From the book sheet below, do the following:
1. Find the key points (up to 5).
2. Write a podcast script IN ENGLISH of {length}. Tone: {tone}.
   Include a greeting, the key points with a simple example or image for each,
   and a short closing with a sign-off.
Rules: natural spoken English, no titles, no bullet points, no asterisks or
formatting symbols. Use only information found in the book sheet: do not
invent facts, quotes or plot details. Output only the script, no comments.
The book sheet may be written in any language; the script must be in English.

BOOK SHEET:
{sheet_text}
"""


def build_prompt(sheet: dict, style: str = DEFAULT_STYLE) -> str:
    """Insert the clean sheet text and the chosen style into the prompt."""
    length, tone = STYLES.get(style, STYLES[DEFAULT_STYLE])
    return PROMPT_TEMPLATE.format(length=length, tone=tone, sheet_text=sheet["text"])


def generate_script(sheet: dict, style: str = DEFAULT_STYLE) -> str:
    """Ask the model for the podcast script and return it as text."""
    client = genai.Client()  # reads GEMINI_API_KEY automatically
    prompt = build_prompt(sheet, style)
    try:
        response = client.interactions.create(model=MODEL, input=prompt)
        script = response.output_text
    except AttributeError:
        # Why: older SDK versions do not have "interactions"; keep it working
        response = client.models.generate_content(model=MODEL, contents=prompt)
        script = response.text
    if not script or not script.strip():
        raise RuntimeError("The model returned an empty answer.")
    return script.strip()

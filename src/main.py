"""Podcast Studio - main application.

Pipeline: book sheet -> clean (data_processor) -> script (llm_processor)
-> audio (tts_generator) -> Gradio web interface.

Usage (from the project folder):
    python src/main.py --check-key   # checks the API key is found (no request)
    python src/main.py --test        # runs the pipeline on the sample sheet
    python src/main.py               # opens the Gradio web page
"""

import os
import sys
import traceback
from pathlib import Path

import gradio as gr
from dotenv import load_dotenv

from data_processor import SUPPORTED_FILES, parse_sheet, read_text_file
from llm_processor import DEFAULT_STYLE, STYLES, generate_script
from tts_generator import DEFAULT_VOICE, VOICES, generate_audio

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "outputs"
EXAMPLES_DIR = BASE_DIR / "examples"
SAMPLE_SHEET = EXAMPLES_DIR / "sample_sheet.txt"
BOOK_EXAMPLE = EXAMPLES_DIR / "mi_guion.txt"

# API key: normally in .env at the project root.
load_dotenv(BASE_DIR / ".env")
load_dotenv(BASE_DIR / ".vscode" / ".env")  # in case it was saved there


def read_example(path: Path) -> str:
    """Return the text of an example file, or an empty string if missing."""
    return path.read_text(encoding="utf-8") if path.exists() else ""


def load_file(file_path):
    """Read an uploaded file and return its text for the text box."""
    if not file_path:
        return gr.skip()
    try:
        return read_text_file(file_path)
    except ValueError as error:
        raise gr.Error(str(error))  # shown to the user as a pop-up message


def run_pipeline(raw_text: str, voice: str = DEFAULT_VOICE, style: str = DEFAULT_STYLE):
    """Run the three steps. Returns (script, audio_path, status_message).

    Why one try/except per step: the user can see exactly which step failed
    (input, script or audio) and keep what was already produced.
    """
    # Step 1: input
    try:
        sheet = parse_sheet(raw_text)
    except ValueError as error:
        return "", None, f"Input problem: {error}"

    # Step 2: script with the LLM
    try:
        script = generate_script(sheet, style)
    except Exception as error:  # show the reason instead of crashing
        traceback.print_exc()
        return "", None, f"Could not generate the script: {error!r}"
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "last_script.txt").write_text(script, encoding="utf-8")

    # Step 3: audio
    try:
        audio_path, voice_used = generate_audio(script, OUTPUT_DIR, voice)
    except Exception as error:
        traceback.print_exc()
        return script, None, f"Script ready, but audio failed: {error!r}"

    title = sheet["metadata"].get("title", "your book sheet")
    status = (
        f"Done. Podcast generated from: {title}\n"
        f"Voice: {voice_used} | Style: {style} | Script: {len(script.split())} words"
    )
    return script, str(audio_path), status


def build_interface() -> gr.Blocks:
    """Create the Gradio web page."""
    with gr.Blocks(title="Podcast Studio") as demo:
        gr.Markdown(
            "# Podcast Studio\n"
            "Turn the sheet or text of a book into a short podcast: "
            "**paste text, choose a voice and a style, and listen.**"
        )
        with gr.Row():
            with gr.Column(scale=1):
                sheet_box = gr.Textbox(
                    label="1. Book sheet or text",
                    lines=14,
                    value=read_example(BOOK_EXAMPLE) or read_example(SAMPLE_SHEET),
                    placeholder="Paste here the text about the book...",
                )
                upload_box = gr.File(
                    label="...or upload a .txt, .md or .pdf file",
                    file_types=list(SUPPORTED_FILES),
                    type="filepath",
                )
                with gr.Row():
                    example_book = gr.Button("Load example: Death and the Gardener")
                    example_sample = gr.Button("Load example: small habits")
                voice_box = gr.Dropdown(
                    choices=list(VOICES),
                    value=DEFAULT_VOICE,
                    label="2. Voice",
                    info="If a voice is unavailable, the app uses another one.",
                )
                style_box = gr.Dropdown(
                    choices=list(STYLES),
                    value=DEFAULT_STYLE,
                    label="3. Style and length",
                )
                gr.Markdown(
                    "**Tip:** match the voice and style to the book. For intimate or "
                    "serious topics, choose *Reflective and literary* with a warm or "
                    "gentle voice; for light topics, an upbeat voice and the "
                    "*Conversational* style."
                )
                generate_btn = gr.Button("Generate podcast", variant="primary")
            with gr.Column(scale=1):
                status_box = gr.Textbox(label="Status", lines=2, interactive=False)
                audio_box = gr.Audio(label="Your podcast", type="filepath")
                script_box = gr.Textbox(label="Podcast script", lines=14)
        gr.Markdown(
            "_Pipeline: text cleaning (Python) -> script with a Gemini model -> "
            "speech with Gemini TTS. Local app; the API key stays in a private .env file._"
        )

        upload_box.upload(load_file, inputs=upload_box, outputs=sheet_box)
        example_book.click(lambda: read_example(BOOK_EXAMPLE), outputs=sheet_box)
        example_sample.click(lambda: read_example(SAMPLE_SHEET), outputs=sheet_box)
        generate_btn.click(
            run_pipeline,
            inputs=[sheet_box, voice_box, style_box],
            outputs=[script_box, audio_box, status_box],
        )
    return demo


if __name__ == "__main__":
    if "--check-key" in sys.argv:
        key = os.getenv("GEMINI_API_KEY", "")
        if key:
            print(f"Key found ({len(key)} characters). It is not shown for security.")
        else:
            print("GEMINI_API_KEY not found. Check your .env file.")
    elif "--test" in sys.argv:
        script, audio, status = run_pipeline(read_example(SAMPLE_SHEET))
        print(status)
        print(script[:500], "...\n" if script else "")
        print("Audio:", audio)
    else:
        OUTPUT_DIR.mkdir(exist_ok=True)
        build_interface().launch(allowed_paths=[str(OUTPUT_DIR)])

"""Step 3 - Audio generation (text-to-speech).

Main provider: Gemini TTS (same API key as the script step, several voices).
Backups, used only if the previous one fails: edge-tts (free, unofficial
service) and gTTS (free). The backup library gTTS is installed automatically
if it is missing.
"""

import asyncio
import base64
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

TTS_MODEL = "gemini-3.8-flash-tts"  # from the official Gemini speech docs
SPEECH_STYLE = (
    "very warm, soft and unhurried, intimate and comforting, as if speaking "
    "quietly beside a friend in a garden at dusk, with gentle pauses"
)

# Voices the user can choose in the interface: label -> Gemini voice name.
VOICES = {
    "Sulafat - warm": "Sulafat",
    "Achernar - soft": "Achernar",
    "Charon - informative": "Charon",
    "Kore - firm and clear": "Kore",
    "Achird - friendly": "Achird",
    "Puck - upbeat": "Puck",
    "Gacrux - mature": "Gacrux",
    "Vindemiatrix - gentle": "Vindemiatrix",
    "Iapetus - clear": "Iapetus",
}
DEFAULT_VOICE = "Sulafat - warm"

EDGE_NAME = "edge-tts backup voice (Aria)"
EDGE_VOICE = "en-US-AriaNeural"
GTTS_NAME = "gTTS backup voice"


def clean_for_speech(script: str) -> str:
    """Remove formatting symbols that should not be read aloud."""
    return re.sub(r"[*#_`>]", "", script)


def _gemini_tts_save(text: str, voice_name: str, path: Path) -> None:
    """Create a WAV file with a Gemini voice (24 kHz, mono)."""
    from google import genai

    client = genai.Client()  # reads GEMINI_API_KEY automatically
    interaction = client.interactions.create(
        model=TTS_MODEL,
        input=[
            {
                "type": "user_input",
                "content": [
                    {
                        "type": "text",
                        "text": text,
                        "annotations": [
                            {"type": "speech_metadata", "style": SPEECH_STYLE}
                        ],
                    }
                ],
            }
        ],
        response_format={"type": "audio"},
        generation_config={"speech_config": [{"voice": voice_name}]},
    )
    path.write_bytes(base64.b64decode(interaction.output_audio.data))


def _edge_tts_save(text: str, path: Path) -> None:
    import edge_tts

    async def _save():
        await edge_tts.Communicate(text, EDGE_VOICE).save(str(path))

    asyncio.run(_save())


def _gtts_save(text: str, path: Path) -> None:
    try:
        from gtts import gTTS
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "gTTS"])
        from gtts import gTTS
    gTTS(text, lang="en").save(str(path))


def _is_valid(path: Path) -> bool:
    return path.exists() and path.stat().st_size > 0


def generate_audio(script: str, output_dir: Path, voice_label: str = DEFAULT_VOICE):
    """Convert the script into an audio file.

    Tries the chosen Gemini voice first, then edge-tts, then gTTS.
    Returns (path, name_of_the_voice_used).
    """
    output_dir.mkdir(exist_ok=True)
    text = clean_for_speech(script)
    stamp = f"{datetime.now():%Y%m%d_%H%M%S}"
    voice_label = voice_label if voice_label in VOICES else DEFAULT_VOICE

    # Why a chain of providers: voice services can fail (quota, network, blocked
    # requests); the user should still get an audio and know which voice was used.
    errors = []

    # 1) Gemini TTS with the chosen voice
    wav_path = output_dir / f"podcast_{stamp}.wav"
    try:
        _gemini_tts_save(text, VOICES[voice_label], wav_path)
        if _is_valid(wav_path):
            return wav_path, voice_label
    except Exception as error:
        errors.append(f"Gemini TTS: {error!r}")
        print(f"Gemini TTS failed: {error!r}")

    # 2) edge-tts and 3) gTTS write mp3 files
    mp3_path = output_dir / f"podcast_{stamp}.mp3"
    for name, saver in (
        (EDGE_NAME, lambda: _edge_tts_save(text, mp3_path)),
        (GTTS_NAME, lambda: _gtts_save(text, mp3_path)),
    ):
        try:
            saver()
            if _is_valid(mp3_path):
                return mp3_path, name
        except Exception as error:
            errors.append(f"{name}: {error!r}")
            print(f"{name} failed: {error!r}")

    raise RuntimeError("All audio providers failed. " + " | ".join(errors))

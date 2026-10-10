"""
Free narration via edge-tts (uses Microsoft Edge's online neural voices,
no API key required, no cost). Produces an mp3.
"""

import asyncio
from pathlib import Path

import edge_tts


async def _synthesize(text: str, voice: str, out_path: Path):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(out_path))


def synthesize_voiceover(text: str, voice: str, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    asyncio.run(_synthesize(text, voice, out_path))
    return out_path


if __name__ == "__main__":
    p = synthesize_voiceover(
        "This is a test of the free text to speech narration engine.",
        "en-US-GuyNeural",
        Path("/tmp/test_voice.mp3"),
    )
    print("Wrote", p)

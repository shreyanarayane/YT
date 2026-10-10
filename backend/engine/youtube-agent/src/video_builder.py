"""
Assembles the final vertical video:
  free stock video clips (Pexels API, free tier) + burned-in captions
  + the narration track from tts.py, trimmed/looped to match audio length.

Uses Pillow for caption overlays to avoid external ImageMagick dependencies on Windows.
"""

import os
import random
import tempfile
from pathlib import Path
from typing import List, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont
import requests
from moviepy import (
    AudioFileClip,
    ColorClip,
    CompositeVideoClip,
    ImageClip,
    VideoFileClip,
    concatenate_videoclips,
)


def _fetch_pexels_clips(query: str, api_key: str, resolution: tuple, n: int = 3) -> List[Path]:
    if not api_key or api_key.startswith("YOUR_"):
        return []
    headers = {"Authorization": api_key}
    try:
        resp = requests.get(
            "https://api.pexels.com/videos/search",
            headers=headers,
            params={"query": query, "orientation": "portrait", "per_page": n},
            timeout=15,
        )
        resp.raise_for_status()
        videos = resp.json().get("videos", [])

        downloaded = []
        for i, v in enumerate(videos):
            files = sorted(v.get("video_files", []), key=lambda f: f.get("width", 0))
            if not files:
                continue
            pick = next((f for f in files if f.get("width", 0) >= resolution[0]), files[-1])
            local_path = Path(tempfile.gettempdir()) / f"pexels_clip_{i}.mp4"
            with requests.get(pick["link"], stream=True, timeout=60) as r:
                r.raise_for_status()
                with open(local_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1 << 16):
                        f.write(chunk)
            downloaded.append(local_path)
        return downloaded
    except Exception as e:
        print(f"[video_builder] Pexels fetch error: {e}")
        return []


def _create_caption_clip(title: str, resolution: tuple, duration: float) -> ImageClip:
    """Renders a modern typography title banner overlay using Pillow without ImageMagick."""
    width, height = resolution
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Try loading Arial or default font
    font_size = max(40, int(width * 0.05))
    try:
        # Windows standard font path
        font = ImageFont.truetype("arial.ttf", font_size)
    except Exception:
        try:
            font = ImageFont.truetype("Arial.ttf", font_size)
        except Exception:
            font = ImageFont.load_default()

    # Wrap title into lines
    words = title.split()
    lines = []
    curr_line = []
    for w in words:
        test_line = " ".join(curr_line + [w])
        bbox = draw.textbbox((0, 0), test_line, font=font) if hasattr(draw, "textbbox") else draw.textsize(test_line, font=font)
        text_w = bbox[2] - bbox[0] if hasattr(draw, "textbbox") else bbox[0]
        if text_w > width - 160:
            if curr_line:
                lines.append(" ".join(curr_line))
                curr_line = [w]
            else:
                lines.append(w)
                curr_line = []
        else:
            curr_line.append(w)
    if curr_line:
        lines.append(" ".join(curr_line))

    # Calculate bounding box for background pill
    line_height = int(font_size * 1.3)
    total_text_h = len(lines) * line_height
    pill_padding_x = 40
    pill_padding_y = 24
    top_y = int(height * 0.12)
    center_x = width // 2

    max_line_w = 0
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font) if hasattr(draw, "textbbox") else draw.textsize(line, font=font)
        line_w = bbox[2] - bbox[0] if hasattr(draw, "textbbox") else bbox[0]
        max_line_w = max(max_line_w, line_w)

    pill_left = max(20, center_x - (max_line_w // 2) - pill_padding_x)
    pill_right = min(width - 20, center_x + (max_line_w // 2) + pill_padding_x)
    pill_top = top_y - pill_padding_y
    pill_bottom = top_y + total_text_h + pill_padding_y

    # Draw dark translucent rounded banner
    if hasattr(draw, "rounded_rectangle"):
        draw.rounded_rectangle(
            [pill_left, pill_top, pill_right, pill_bottom],
            radius=20,
            fill=(15, 23, 42, 210),
            outline=(239, 68, 68, 240),
            width=3,
        )
    else:
        draw.rectangle(
            [pill_left, pill_top, pill_right, pill_bottom],
            fill=(15, 23, 42, 210),
            outline=(239, 68, 68, 240),
            width=3,
        )

    # Draw text lines
    curr_y = top_y
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font) if hasattr(draw, "textbbox") else draw.textsize(line, font=font)
        line_w = bbox[2] - bbox[0] if hasattr(draw, "textbbox") else bbox[0]
        text_x = center_x - (line_w // 2)
        # Drop shadow
        draw.text((text_x + 2, curr_y + 2), line, font=font, fill=(0, 0, 0, 200))
        # Main text
        draw.text((text_x, curr_y), line, font=font, fill=(255, 255, 255, 255))
        curr_y += line_height

    arr = np.array(img)
    return ImageClip(arr).with_duration(duration).with_position("center")


def _fallback_background(duration: float, resolution: tuple) -> ColorClip:
    color = random.choice([(15, 23, 42), (24, 24, 27), (30, 27, 75)])
    return ColorClip(size=resolution, color=color, duration=duration)


def build_video(
    topic: str,
    title: str,
    script_text: str,
    narration_path: Path,
    pexels_api_key: str,
    resolution: tuple,
    out_path: Path,
) -> Path:
    audio = AudioFileClip(str(narration_path))
    duration = audio.duration
    if duration < 1.0:
        duration = 5.0 # Fallback for dummy audio
        # The regular TTS path always produces a valid, longer narration.  If
        # it does not, let the caller's fallback render path handle the job.
        raise ValueError("Narration audio is too short to render a video")

    clip_paths = _fetch_pexels_clips(topic, pexels_api_key, resolution)

    if clip_paths:
        try:
            clips = []
            remaining = duration
            for p in clip_paths:
                if remaining <= 0:
                    break
                vc = VideoFileClip(str(p)).without_audio()
                vc = vc.resized(height=resolution[1]) if vc.h < vc.w else vc.resized(width=resolution[0])
                vc = vc.subclipped(0, min(vc.duration, remaining / max(len(clip_paths), 1) + 1))
                clips.append(vc)
                remaining -= vc.duration
            background = concatenate_videoclips(clips, method="compose").with_duration(duration)
        except Exception as e:
            print(f"[video_builder] Failed assembling pexels clips ({e}), using animated background")
            background = _fallback_background(duration, resolution)
    else:
        background = _fallback_background(duration, resolution)

    background = background.resized(new_size=resolution).with_position("center")

    # Generate overlay without requiring ImageMagick
    caption_clip = _create_caption_clip(title, resolution, duration)

    final = CompositeVideoClip([background, caption_clip], size=resolution).with_audio(audio).with_duration(duration)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    final.write_videofile(
        str(out_path),
        fps=30,
        codec="libx264",
        audio_codec="aac",
        threads=4,
        logger=None,
    )
    return out_path

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import shutil
import subprocess
import threading
import time
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.request import Request, urlopen


def ffmpeg_path(path: Path) -> str:
    return path.resolve().as_posix().replace("'", "'\\''")

STYLE_PRESETS = {
    "auto": {
        "label": "Auto Faceless",
        "backgrounds": [
            "clean cartoon explainer studio background, empty center space, bright professional animation style",
            "simple modern animated room background, clean faceless YouTube style, empty foreground",
            "cartoon whiteboard presentation background, clear composition, no text",
            "cartoon city and workspace montage background, polished explainer video style",
            "simple cinematic animated background for a faceless YouTube video, empty center space",
        ],
        "poses": ["neutral", "talking", "point_right", "thinking", "happy"],
    },
    "finance": {
        "label": "Finance Explainer",
        "backgrounds": [
            "cartoon office desk with laptop and money charts, clean finance explainer style, empty center space",
            "cartoon city skyline with bank building and stock chart overlay, clean finance explainer style",
            "cartoon living room with bills on table, personal finance animation background, empty foreground",
            "cartoon whiteboard room with simple upward graph, finance YouTube animation style",
            "cartoon house exterior with for sale sign and coins, real estate investing explainer style",
        ],
        "poses": ["neutral", "point_right", "talking", "thinking", "shocked", "happy"],
    },
    "stickman_story": {
        "label": "Stickman Story",
        "backgrounds": [
            "simple cartoon classroom background, empty center space, clean lines, stickman animation style",
            "simple cartoon school hallway with lockers, empty center space, clean lines",
            "simple cartoon bedroom background with desk and bed, empty center space",
            "simple cartoon cafeteria background, bright colors, empty foreground",
            "simple cartoon street at night, clean lines, empty center space",
        ],
        "poses": ["neutral", "talking", "shocked", "angry", "sad", "run", "point_left"],
    },
    "ink_explainer": {
        "label": "Ink Explainer",
        "backgrounds": [
            "hand drawn black ink ancient human survival scene on warm white paper, simple stick figures, cave, fire, tools, no readable text",
            "black ink line art prehistoric camp diagram with arrows, animals, footprints, and simple symbols, off white paper, no readable text",
            "minimal hand drawn ancient humans hunting and gathering scene, black ink on parchment white background, educational explainer style",
            "sketchbook style map and timeline of early human migration, black ink, simple icons, clean explainer background, no readable text",
            "simple black ink comparison of modern life and ancient human life, split scene, stick figures, no readable text",
        ],
        "poses": ["neutral", "talking", "point_right", "thinking", "happy"],
    },
    "general": {
        "label": "General Faceless",
        "backgrounds": [
            "clean cartoon studio background, empty center space, bright colors",
            "simple modern room background, clean animation style, empty foreground",
            "cartoon whiteboard presentation background, clean lines",
            "cartoon city street background, bright explainer video style",
            "cartoon desktop workspace background, laptop and notes, empty center space",
        ],
        "poses": ["neutral", "talking", "point_right", "thinking", "happy"],
    },
    "documentary": {
        "label": "Mini Documentary",
        "backgrounds": [
            "cinematic cartoon documentary map room, timeline wall, dramatic but clean, empty center space",
            "cartoon newsroom desk with monitors and notes, investigative explainer style, empty foreground",
            "cinematic cartoon city aerial view, soft lighting, documentary animation background",
            "cartoon archive room with file boxes and evidence board, clean animated documentary style",
            "cartoon interview studio background, warm practical lights, empty center space",
        ],
        "poses": ["neutral", "thinking", "point_right", "talking", "shocked"],
    },
    "history": {
        "label": "History Explainer",
        "backgrounds": [
            "cartoon ancient city background, clean history explainer style, empty center space",
            "cartoon medieval map table with candles and parchment, no text, empty foreground",
            "cartoon museum gallery with artifacts, clean animation style, empty center space",
            "cartoon battlefield from far distance, simple non-violent history explainer background",
            "cartoon old library with globe and bookshelves, warm lighting, no people",
        ],
        "poses": ["neutral", "point_right", "talking", "thinking", "shocked"],
    },
    "scary_story": {
        "label": "Scary Story",
        "backgrounds": [
            "simple cartoon dark bedroom at night, eerie but family friendly, empty center space",
            "cartoon quiet neighborhood street at night with streetlights, clean animated story style",
            "cartoon abandoned hallway, suspenseful lighting, no gore, empty foreground",
            "cartoon forest path at night, misty, clean lines, empty center space",
            "cartoon basement room with single light, suspense story background, no people",
        ],
        "poses": ["neutral", "shocked", "sad", "run", "thinking"],
    },
}


FORMAT_PRESETS = {
    "youtube": {"width": 1024, "height": 576, "minutes": 6.0, "scene_count": 24},
    "shorts": {"width": 576, "height": 1024, "minutes": 0.75, "scene_count": 8},
    "tiktok": {"width": 576, "height": 1024, "minutes": 0.75, "scene_count": 8},
    "reels": {"width": 576, "height": 1024, "minutes": 0.75, "scene_count": 8},
}


@dataclass
class Scene:
    number: int
    title: str
    narration: str
    caption: str
    background_prompt: str
    character_pose: str
    camera: str
    shot_type: str
    transition: str
    visual_beat: str
    sfx: str
    duration: float
    background_file: str | None = None


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")[:60] or "episode"


def split_sentences(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"(?<=[.!?])\s+", text.strip()) if p.strip()]


def resolve_style(topic: str, style: str) -> str:
    if style != "auto":
        return style
    value = topic.lower()
    if any(word in value for word in ["money", "invest", "stock", "budget", "finance", "rich", "broke", "income"]):
        return "finance"
    if any(word in value for word in ["scary", "horror", "creepy", "haunted", "mystery", "disturbing"]):
        return "scary_story"
    if any(word in value for word in ["ink", "drawn", "sketch", "whiteboard", "diagram", "hand drawn", "ancient human", "early human", "prehistoric", "neanderthal", "caveman", "hunter gatherer"]):
        return "ink_explainer"
    if any(word in value for word in ["history", "war", "ancient", "empire", "king", "queen", "civilization"]):
        return "history"
    if any(word in value for word in ["story", "school", "friend", "kid", "animation", "stickman"]):
        return "stickman_story"
    if any(word in value for word in ["documentary", "true story", "case", "rise and fall", "explained"]):
        return "documentary"
    return "general"


def template_script(topic: str, style: str) -> str:
    topic_phrase = topic[:1].lower() + topic[1:] if topic else "this topic"
    if style == "finance":
        return (
            f"Most people think {topic_phrase} is too small to matter. "
            "But small decisions repeated every week can change your money life. "
            "First, understand the real problem. "
            "Second, build a simple system that removes guesswork. "
            "Third, stay patient because consistency creates the biggest results. "
            "This video is for education only and is not financial advice."
        )
    if style == "stickman_story":
        return (
            f"Stickman thought {topic} would be normal. "
            "Then the first clue told him something was wrong. "
            "Every choice made the situation worse. "
            "Finally, he noticed one tiny detail everyone else missed. "
            "That detail changed everything."
        )
    if style == "ink_explainer":
        return (
            f"This morning, something ordinary reminded you of {topic}. "
            "Now rewind thousands of years, before alarms, cities, and schedules existed. "
            "For ancient humans, the same problem looked completely different. "
            "Every choice was connected to food, danger, weather, family, and survival. "
            "The strange part is that many of their solutions still shape how we live today."
        )
    if style == "documentary":
        return (
            f"The story of {topic} starts with one overlooked detail. "
            "At first, it looked ordinary. "
            "Then the pattern became impossible to ignore. "
            "The more people investigated, the stranger the timeline became. "
            "By the end, the real lesson was bigger than the event itself."
        )
    if style == "history":
        return (
            f"To understand {topic}, you have to start before the famous moment. "
            "Small choices created pressure over time. "
            "Then one decision changed the direction of everything. "
            "The surprising part is how familiar the lesson still feels today."
        )
    if style == "scary_story":
        return (
            f"Nobody believed the first warning about {topic}. "
            "The signs were small at first. "
            "Then something happened that could not be explained. "
            "By the time the truth appeared, it was already too late to ignore."
        )
    return (
        f"Today we are talking about {topic}. "
        "First, we explain the main problem. "
        "Then we show why it matters. "
        "Finally, we turn it into a simple takeaway anyone can remember."
    )


def gemini_script(topic: str, style: str, minutes: float, api_key: str | None) -> str | None:
    if not api_key:
        return None
    prompt = (
        "Write a concise narration script for a faceless animated YouTube video.\n"
        f"Topic: {topic}\n"
        f"Style: {STYLE_PRESETS.get(style, STYLE_PRESETS['general'])['label']}\n"
        f"Target length: {minutes} minutes.\n"
        "Use short narration sentences. Start with a strong hook. End with a clear payoff. "
        "Do not include stage directions."
    )
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-1.5-flash:generateContent?key={api_key}"
    )
    try:
        request = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
        return result["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as exc:
        print(f"Gemini failed, using template script: {exc}")
        return None


def build_scenes(topic: str, style: str, scene_count: int, minutes: float, script: str, generation_mode: str) -> list[Scene]:
    preset = STYLE_PRESETS.get(style, STYLE_PRESETS["general"])
    sentences = split_sentences(script) or split_sentences(template_script(topic, style))
    total_seconds = max(30.0, minutes * 60.0)
    duration = max(3.0, total_seconds / scene_count)
    cameras = ["slow_zoom", "pan_left", "pan_right", "push_in", "slow_zoom", "pull_back"]
    shot_types = ["establishing shot", "medium shot", "close-up detail", "wide reveal", "overhead explainer"]
    transitions = ["cut", "crossfade", "whip pan", "push cut", "flash cut"]
    sfx_cues = ["soft whoosh", "subtle hit", "paper slide", "low riser", "clean pop"]
    scenes = []
    for index in range(scene_count):
        sentence = sentences[index % len(sentences)]
        shot_type = shot_types[index % len(shot_types)]
        visual_beat = f"{shot_type} showing the key idea: {sentence}"
        if generation_mode == "flow_fast":
            prompt_prefix = (
                f"{shot_type}, cinematic storyboard frame, clear subject staging, "
                "depth, clean animation production still, "
            )
        else:
            prompt_prefix = ""
        prompt = (
            f"{prompt_prefix}{preset['backgrounds'][index % len(preset['backgrounds'])]}, "
            f"scene about {topic}, no text, no people"
        )
        caption = sentence if len(sentence) <= 88 else sentence[:85].rstrip() + "..."
        scenes.append(
            Scene(
                number=index + 1,
                title=f"Scene {index + 1}",
                narration=sentence,
                caption=caption,
                background_prompt=prompt,
                character_pose=preset["poses"][index % len(preset["poses"])],
                camera=cameras[index % len(cameras)],
                shot_type=shot_type,
                transition=transitions[index % len(transitions)],
                visual_beat=visual_beat,
                sfx=sfx_cues[index % len(sfx_cues)],
                duration=round(duration, 2),
            )
        )
    return scenes


def load_diffusion_pipeline(model_id: str):
    import torch
    from diffusers import AutoPipelineForText2Image

    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32
    pipe = AutoPipelineForText2Image.from_pretrained(
        model_id,
        torch_dtype=dtype,
        variant="fp16" if device == "cuda" else None,
    )
    pipe = pipe.to(device)
    return pipe, device


def generate_backgrounds(
    scenes: list[Scene],
    out_dir: Path,
    model_id: str,
    width: int,
    height: int,
    guidance_scale: float,
    steps: int,
    seed: int,
) -> None:
    import torch

    width = int(width)
    height = int(height)
    steps = int(steps)
    seed = int(seed)
    try:
        pipe, device = load_diffusion_pipeline(model_id)
    except Exception as exc:
        fallback = "stabilityai/sd-turbo"
        if model_id == fallback:
            raise
        print(f"Could not load {model_id}, falling back to {fallback}: {exc}")
        pipe, device = load_diffusion_pipeline(fallback)
    generator = torch.Generator(device=device).manual_seed(seed)
    for scene in scenes:
        image_path = out_dir / f"scene_{scene.number:03}.jpg"
        image = pipe(
            prompt=scene.background_prompt,
            width=width,
            height=height,
            guidance_scale=guidance_scale,
            num_inference_steps=steps,
            generator=generator,
        ).images[0]
        image.save(image_path)
        scene.background_file = str(image_path.name)
        print(f"Saved {image_path}")


async def edge_tts(text: str, out_path: Path, voice: str) -> None:
    import edge_tts

    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(out_path))


def run_async_blocking(coro) -> None:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(coro)
        return

    error: list[BaseException] = []

    def runner() -> None:
        try:
            asyncio.run(coro)
        except BaseException as exc:
            error.append(exc)

    thread = threading.Thread(target=runner)
    thread.start()
    thread.join()
    if error:
        raise error[0]


def gtts_voice(text: str, out_path: Path) -> None:
    from gtts import gTTS

    gTTS(text=text, lang="en").save(str(out_path))


def create_voice(
    text: str,
    out_path: Path,
    voice_provider: str,
    edge_voice: str,
    omnivoice_audio_path: str | None,
) -> Path:
    if voice_provider == "omnivoice":
        if not omnivoice_audio_path:
            raise ValueError("voice_provider='omnivoice' needs omnivoice_audio_path pointing to an OmniVoice WAV or MP3.")
        source_audio = Path(omnivoice_audio_path)
        if not source_audio.exists():
            raise FileNotFoundError(f"OmniVoice audio was not found: {source_audio}")
        copied_audio = out_path.with_name(f"omnivoice{source_audio.suffix.lower()}")
        shutil.copyfile(source_audio, copied_audio)
        return normalize_audio_for_ffmpeg(copied_audio, out_path)
    if voice_provider == "gtts":
        gtts_voice(text, out_path)
        return out_path
    try:
        run_async_blocking(edge_tts(text, out_path, edge_voice))
    except Exception as exc:
        print(f"Edge TTS failed, falling back to gTTS: {exc}")
        gtts_voice(text, out_path)
    return out_path


def write_srt(scenes: list[Scene], output_path: Path) -> None:
    def fmt(seconds: float) -> str:
        ms = int((seconds - int(seconds)) * 1000)
        seconds = int(seconds)
        return f"{seconds // 3600:02}:{(seconds % 3600) // 60:02}:{seconds % 60:02},{ms:03}"

    cursor = 0.0
    lines = []
    for scene in scenes:
        start = cursor
        end = cursor + scene.duration
        lines.extend([str(scene.number), f"{fmt(start)} --> {fmt(end)}", scene.caption, ""])
        cursor = end
    output_path.write_text("\n".join(lines), encoding="utf-8")


def write_storyboard(scenes: list[Scene], output_path: Path) -> None:
    lines = ["# Storyboard", ""]
    for scene in scenes:
        lines.extend(
            [
                f"## Scene {scene.number}: {scene.title}",
                f"- Narration: {scene.narration}",
                f"- Visual beat: {scene.visual_beat}",
                f"- Shot: {scene.shot_type}",
                f"- Camera: {scene.camera}",
                f"- Transition: {scene.transition}",
                f"- SFX cue: {scene.sfx}",
                f"- Background prompt: {scene.background_prompt}",
                "",
            ]
        )
    output_path.write_text("\n".join(lines), encoding="utf-8")


def write_edit_decision_list(scenes: list[Scene], output_path: Path) -> None:
    cursor = 0.0
    events = []
    for scene in scenes:
        events.append(
            {
                "scene": scene.number,
                "start": round(cursor, 2),
                "end": round(cursor + scene.duration, 2),
                "duration": scene.duration,
                "shot_type": scene.shot_type,
                "camera": scene.camera,
                "transition": scene.transition,
                "sfx": scene.sfx,
                "caption": scene.caption,
                "background": scene.background_file,
            }
        )
        cursor += scene.duration
    output_path.write_text(json.dumps({"events": events}, indent=2), encoding="utf-8")


def build_metadata(topic: str, style: str, platform: str, script: str) -> dict:
    title_topic = topic.strip().rstrip(".")
    if platform in {"shorts", "tiktok", "reels"}:
        titles = [
            f"{title_topic} in 60 Seconds",
            f"The Truth About {title_topic}",
            f"You Need To Know This About {title_topic}",
        ]
    else:
        titles = [
            f"The Simple Truth About {title_topic}",
            f"Why {title_topic} Matters More Than You Think",
            f"{title_topic}: Explained Simply",
        ]
    tags = ["faceless animation", "animated explainer", STYLE_PRESETS.get(style, STYLE_PRESETS["general"])["label"].lower()]
    if style == "finance":
        tags.extend(["personal finance", "money", "investing education"])
    if style == "stickman_story":
        tags.extend(["stickman animation", "story animation"])
    hashtags = ["#facelessyoutube", "#animation", "#explainer"]
    description = (
        f"An animated faceless explainer about {title_topic}.\n\n"
        "Generated with FreeCalliope on Google Colab.\n\n"
        + " ".join(hashtags)
    )
    return {
        "titles": titles,
        "description": description,
        "tags": tags,
        "hashtags": hashtags,
        "script_preview": script[:500],
    }


def write_placeholder_character(out_dir: Path) -> None:
    from PIL import Image, ImageDraw

    out_dir.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((220, 70, 292, 142), outline="black", width=8)
    draw.line((256, 142, 256, 310), fill="black", width=8)
    draw.line((256, 190, 170, 245), fill="black", width=8)
    draw.line((256, 190, 342, 245), fill="black", width=8)
    draw.line((256, 310, 190, 430), fill="black", width=8)
    draw.line((256, 310, 322, 430), fill="black", width=8)
    image.save(out_dir / "neutral.png")


def write_thumbnail(project: Path, topic: str, width: int, height: int) -> Path:
    from PIL import Image, ImageDraw, ImageFont

    thumbs = project / "thumbnails"
    thumbs.mkdir(parents=True, exist_ok=True)
    first_background = Image.open(project / "backgrounds" / "scene_001.jpg").convert("RGB").resize((width, height))
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rectangle((0, 0, width, height), fill=(0, 0, 0, 70))
    draw.rounded_rectangle((int(width * 0.05), int(height * 0.62), int(width * 0.95), int(height * 0.9)), radius=18, fill=(255, 255, 255, 230))
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", max(28, width // 14))
    except OSError:
        font = ImageFont.load_default()
    headline = topic.upper()
    if len(headline) > 42:
        headline = headline[:39].rstrip() + "..."
    draw_wrapped_text(
        draw,
        headline,
        (int(width * 0.08), int(height * 0.64), int(width * 0.92), int(height * 0.88)),
        font,
        "black",
    )
    thumbnail = Image.alpha_composite(first_background.convert("RGBA"), overlay).convert("RGB")
    path = thumbs / "thumbnail.jpg"
    thumbnail.save(path, quality=92)
    return path


def draw_wrapped_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    box: tuple[int, int, int, int],
    font: ImageFont.ImageFont,
    fill: str,
) -> None:
    words = text.split()
    lines: list[str] = []
    current = ""
    max_width = box[2] - box[0]
    for word in words:
        test = f"{current} {word}".strip()
        left, top, right, bottom = draw.textbbox((0, 0), test, font=font)
        if right - left <= max_width or not current:
            current = test
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)

    line_height = max(24, int((draw.textbbox((0, 0), "Ag", font=font)[3]) * 1.25))
    total_height = line_height * len(lines)
    y = box[1] + max(0, ((box[3] - box[1]) - total_height) // 2)
    for line in lines:
        left, top, right, bottom = draw.textbbox((0, 0), line, font=font)
        x = box[0] + max(0, (max_width - (right - left)) // 2)
        draw.text((x + 2, y + 2), line, font=font, fill="black")
        draw.text((x, y), line, font=font, fill=fill)
        y += line_height


def normalize_audio_for_ffmpeg(audio_path: Path, out_path: Path) -> Path:
    if audio_path.suffix.lower() == ".mp3":
        return audio_path
    run_ffmpeg(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(audio_path),
            "-vn",
            "-codec:a",
            "libmp3lame",
            "-q:a",
            "2",
            str(out_path),
        ],
    )
    return out_path


def run_ffmpeg(command: list[str]) -> None:
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "Unknown FFmpeg error."
        raise RuntimeError(message[-2000:])


def render_video(
    project: Path,
    scenes: list[Scene],
    voice_path: Path,
    width: int,
    height: int,
    fps: int = 24,
) -> Path:
    from PIL import Image, ImageDraw, ImageFont

    if not scenes:
        raise ValueError("Cannot render a video with zero scenes.")
    width = int(width)
    height = int(height)
    fps = int(fps)
    videos = project / "videos"
    frames = project / "frames"
    videos.mkdir(parents=True, exist_ok=True)
    frames.mkdir(parents=True, exist_ok=True)

    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", max(26, width // 24))
    except OSError:
        font = ImageFont.load_default()

    stickman = Image.open(project / "characters" / "stickman" / "neutral.png").convert("RGBA")
    stickman_size = max(130, int(height * 0.42))
    stickman = stickman.resize((stickman_size, stickman_size))

    concat_lines: list[str] = []
    clip_paths: list[Path] = []
    for scene in scenes:
        background = Image.open(project / "backgrounds" / f"scene_{scene.number:03}.jpg").convert("RGB")
        background = background.resize((width, height))
        frame = background.convert("RGBA")

        x = max(12, int(width * 0.07))
        y = height - stickman_size - max(18, int(height * 0.08))
        frame.alpha_composite(stickman, (x, y))

        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        caption_h = max(90, int(height * 0.18))
        draw.rounded_rectangle(
            (int(width * 0.08), height - caption_h - 22, int(width * 0.92), height - 18),
            radius=18,
            fill=(0, 0, 0, 175),
        )
        draw_wrapped_text(
            draw,
            scene.caption,
            (int(width * 0.11), height - caption_h - 8, int(width * 0.89), height - 32),
            font,
            "white",
        )
        frame = Image.alpha_composite(frame, overlay).convert("RGB")

        frame_path = frames / f"frame_{scene.number:03}.png"
        frame.save(frame_path)
        clip_path = videos / f"clip_{scene.number:03}.mp4"
        frame_count = max(1, int(scene.duration * fps))
        if scene.camera == "pan_left":
            zoom_expr = "1.08"
            x_expr = f"iw/12-(iw/12)*on/{frame_count}"
            y_expr = "ih/24"
        elif scene.camera == "pan_right":
            zoom_expr = "1.08"
            x_expr = f"(iw/12)*on/{frame_count}"
            y_expr = "ih/24"
        elif scene.camera == "push_in":
            zoom_expr = "min(zoom+0.0025,1.12)"
            x_expr = "iw/2-(iw/zoom/2)"
            y_expr = "ih/2-(ih/zoom/2)"
        elif scene.camera == "pull_back":
            zoom_expr = "max(1.14-0.0025*on,1.0)"
            x_expr = "iw/2-(iw/zoom/2)"
            y_expr = "ih/2-(ih/zoom/2)"
        else:
            zoom_expr = "min(zoom+0.0015,1.08)"
            x_expr = "iw/2-(iw/zoom/2)"
            y_expr = "ih/2-(ih/zoom/2)"
        transition_filter = ""
        if scene.transition == "flash cut":
            transition_filter = ",fade=t=in:st=0:d=0.08"
        elif scene.transition == "crossfade":
            transition_filter = ",fade=t=in:st=0:d=0.18"
        run_ffmpeg(
            [
                "ffmpeg",
                "-y",
                "-loop",
                "1",
                "-i",
                str(frame_path),
                "-vf",
                f"zoompan=z='{zoom_expr}':x='{x_expr}':y='{y_expr}':d={frame_count}:s={width}x{height}:fps={fps}{transition_filter},format=yuv420p",
                "-t",
                str(scene.duration),
                str(clip_path),
            ]
        )
        if not clip_path.exists() or clip_path.stat().st_size == 0:
            raise RuntimeError(f"FFmpeg did not create clip: {clip_path}")
        clip_paths.append(clip_path)
        concat_lines.append(f"file '{ffmpeg_path(clip_path)}'")

    concat_file = project / "frames.txt"
    concat_file.write_text("\n".join(concat_lines), encoding="utf-8")

    silent_video = videos / "silent.mp4"
    final_video = videos / "final.mp4"
    run_ffmpeg(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            str(silent_video),
        ]
    )
    run_ffmpeg(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(silent_video),
            "-i",
            str(voice_path),
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-shortest",
            str(final_video),
        ]
    )
    if not final_video.exists() or final_video.stat().st_size == 0:
        raise RuntimeError("FFmpeg did not create a valid final video.")
    return final_video


def zip_dir(source: Path, zip_path: Path) -> None:
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in source.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(source.parent))


def run_pipeline(
    topic: str,
    style: str = "auto",
    minutes: float = 3.0,
    scene_count: int = 12,
    output_root: str = "outputs",
    gemini_key: str | None = None,
    image_model: str = "stabilityai/sdxl-turbo",
    width: int = 1024,
    height: int = 576,
    steps: int = 3,
    guidance_scale: float = 0.0,
    voice_provider: str = "edge",
    edge_voice: str = "en-US-AriaNeural",
    omnivoice_audio_path: str | None = None,
    seed: int = 1234,
    make_video: bool = True,
    platform: str = "youtube",
    generation_mode: str = "flow_fast",
) -> dict:
    minutes = float(minutes)
    scene_count = max(1, int(scene_count))
    width = int(width)
    height = int(height)
    steps = max(1, int(steps))
    seed = int(seed)
    output_root_path = Path(output_root)
    output_root_path.mkdir(parents=True, exist_ok=True)
    project_name = f"{time.strftime('%Y%m%d-%H%M%S')}-{slugify(topic)}"
    project = output_root_path / project_name
    backgrounds = project / "backgrounds"
    voices = project / "voices"
    captions = project / "captions"
    characters = project / "characters" / "stickman"
    manifests = project / "manifests"
    for folder in (backgrounds, voices, captions, characters, manifests):
        folder.mkdir(parents=True, exist_ok=True)

    if platform in FORMAT_PRESETS and platform != "youtube" and width == 1024 and height == 576:
        preset = FORMAT_PRESETS[platform]
        width = int(preset["width"])
        height = int(preset["height"])
    requested_style = style
    resolved_style = resolve_style(topic, style)
    script = gemini_script(topic, resolved_style, minutes, gemini_key) or template_script(topic, resolved_style)
    scenes = build_scenes(topic, resolved_style, scene_count, minutes, script, generation_mode)
    generate_backgrounds(scenes, backgrounds, image_model, width, height, guidance_scale, steps, seed)

    narration_text = " ".join(scene.narration for scene in scenes)
    voice_path = voices / "narration.mp3"
    voice_path = create_voice(narration_text, voice_path, voice_provider, edge_voice, omnivoice_audio_path)

    write_srt(scenes, captions / "captions.srt")
    write_storyboard(scenes, project / "storyboard.md")
    write_edit_decision_list(scenes, project / "edit_decision_list.json")
    write_placeholder_character(characters)
    thumbnail_path = write_thumbnail(project, topic, width, height)
    video_path = None
    if make_video:
        video_path = render_video(project, scenes, voice_path, width, height)
    (project / "script.txt").write_text(script, encoding="utf-8")
    metadata = build_metadata(topic, resolved_style, platform, script)
    (project / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    manifest = {
        "topic": topic,
        "style": resolved_style,
        "requested_style": requested_style,
        "platform": platform,
        "generation_mode": generation_mode,
        "minutes": minutes,
        "scene_count": scene_count,
        "script": script,
        "image_model": image_model,
        "voice_provider": voice_provider,
        "voice_file": f"voices/{voice_path.name}",
        "captions_file": "captions/captions.srt",
        "storyboard_file": "storyboard.md",
        "edit_decision_list_file": "edit_decision_list.json",
        "thumbnail_file": f"thumbnails/{thumbnail_path.name}",
        "video_file": "videos/final.mp4" if video_path else None,
        "metadata": metadata,
        "scenes": [asdict(scene) for scene in scenes],
    }
    (manifests / "episode.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    zip_path = output_root_path / f"{project_name}.zip"
    zip_dir(project, zip_path)
    manifest["project_dir"] = str(project)
    manifest["zip_path"] = str(zip_path)
    manifest["video_path"] = str(video_path) if video_path else None
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", required=True)
    parser.add_argument("--style", default="auto", choices=STYLE_PRESETS.keys())
    parser.add_argument("--platform", default="youtube", choices=FORMAT_PRESETS.keys())
    parser.add_argument("--generation-mode", default="flow_fast", choices=["flow_fast", "classic_fast"])
    parser.add_argument("--minutes", type=float, default=3.0)
    parser.add_argument("--scene-count", type=int, default=12)
    parser.add_argument("--output-root", default="outputs")
    parser.add_argument("--gemini-key", default=os.environ.get("GEMINI_API_KEY"))
    parser.add_argument("--image-model", default="stabilityai/sdxl-turbo")
    parser.add_argument("--width", type=int, default=1024)
    parser.add_argument("--height", type=int, default=576)
    parser.add_argument("--steps", type=int, default=3)
    parser.add_argument("--guidance-scale", type=float, default=0.0)
    parser.add_argument("--voice-provider", default="edge", choices=["edge", "gtts", "omnivoice"])
    parser.add_argument("--edge-voice", default="en-US-AriaNeural")
    parser.add_argument("--omnivoice-audio-path")
    parser.add_argument("--seed", type=int, default=1234)
    parser.add_argument("--no-video", action="store_true")
    args = parser.parse_args()
    result = run_pipeline(
        topic=args.topic,
        style=args.style,
        minutes=args.minutes,
        scene_count=args.scene_count,
        output_root=args.output_root,
        gemini_key=args.gemini_key,
        image_model=args.image_model,
        width=args.width,
        height=args.height,
        steps=args.steps,
        guidance_scale=args.guidance_scale,
        voice_provider=args.voice_provider,
        edge_voice=args.edge_voice,
        omnivoice_audio_path=args.omnivoice_audio_path,
        seed=args.seed,
        make_video=not args.no_video,
        platform=args.platform,
        generation_mode=args.generation_mode,
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

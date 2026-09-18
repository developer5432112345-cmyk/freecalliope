from __future__ import annotations

import base64
import json
import os
import re
import shutil
import subprocess
import sys
import time
import wave
from dataclasses import asdict, dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent.parent
APP_ROOT = Path(__file__).resolve().parent
PROJECTS = ROOT / "projects"
FASTSD_API = "http://127.0.0.1:8000/api/generate"
PIPER = ROOT / "piper-env" / "Scripts" / "piper.exe"
PIPER_MODEL = ROOT / "voices" / "piper-models" / "en_US-amy-low.onnx"
PIPER_CONFIG = ROOT / "voices" / "piper-models" / "en_US-amy-low.onnx.json"
EDGE_TTS = ROOT / "piper-env" / "Scripts" / "edge-tts.exe"
ENV_PATH = ROOT / ".env"


def load_env() -> None:
    if not ENV_PATH.exists():
        return
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"'))


load_env()


STYLE_PRESETS = {
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
        "icons": ["money", "chart_up", "debt", "house", "warning", "checkmark"],
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
        "icons": ["exclamation", "phone", "door", "clock", "question"],
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
        "icons": ["idea", "arrow", "checkmark", "warning", "spark"],
    },
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
    duration: float
    background_file: str | None = None


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = value.strip("-")
    return value[:60] or "episode"


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def make_script(topic: str, style: str, minutes: float) -> str:
    label = STYLE_PRESETS.get(style, STYLE_PRESETS["general"])["label"]
    topic_phrase = topic[:1].lower() + topic[1:] if topic else "this topic"
    if style == "finance":
        return (
            f"Most people think {topic_phrase} is too small to matter. "
            f"But the simple truth is that small decisions repeated every week can change your money life. "
            f"First, you need to understand the problem clearly. "
            f"Second, you need a simple system that removes guesswork. "
            f"Third, you need patience because the biggest results usually come from consistency. "
            f"In this video, we break it down using simple examples, simple visuals, and zero confusing jargon. "
            f"This is for education only and is not financial advice."
        )
    if style == "stickman_story":
        return (
            f"Stickman thought {topic} would be normal. "
            f"He walked in confident, but the first clue told him something was wrong. "
            f"Every choice made the situation worse. "
            f"Then he noticed one tiny detail that everyone else missed. "
            f"That detail changed everything. "
            f"By the end, Stickman learned the hard way that even simple days can turn into wild stories."
        )
    return (
        f"Today we are talking about {topic}. "
        f"The idea sounds simple, but there are a few details that make it interesting. "
        f"First, we explain the main problem. "
        f"Then we show why it matters. "
        f"Finally, we turn it into a simple takeaway that anyone can remember. "
        f"By the end, {topic} will feel much easier to understand."
    )


def make_gemini_script(topic: str, style: str, minutes: float) -> str | None:
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None
    prompt = (
        "Write a concise narration script for a faceless animated YouTube video.\n"
        f"Topic: {topic}\n"
        f"Style: {STYLE_PRESETS.get(style, STYLE_PRESETS['general'])['label']}\n"
        f"Target length: {minutes} minutes.\n"
        "Use short narration sentences. Do not include stage directions. "
        "For finance topics, include a brief education-only disclaimer."
    )
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-1.5-flash:generateContent?key={api_key}"
    )
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        print(f"Gemini script generation failed, falling back locally: {exc}")
        return None
    try:
        return result["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError):
        return None


def build_scenes(topic: str, style: str, scene_count: int, minutes: float, script: str | None) -> list[Scene]:
    preset = STYLE_PRESETS.get(style, STYLE_PRESETS["general"])
    sentences = split_sentences(script or make_script(topic, style, minutes))
    if not sentences:
        sentences = split_sentences(make_script(topic, style, minutes))

    scene_count = max(1, min(scene_count, 200))
    total_seconds = max(30.0, minutes * 60.0)
    scene_duration = max(3.0, total_seconds / scene_count)
    cameras = ["slow_zoom", "pan_left", "pan_right", "push_in", "static"]
    scenes: list[Scene] = []

    for i in range(scene_count):
        sentence = sentences[i % len(sentences)]
        bg_base = preset["backgrounds"][i % len(preset["backgrounds"])]
        prompt = f"{bg_base}, scene about {topic}, no text, no people"
        pose = preset["poses"][i % len(preset["poses"])]
        caption = sentence
        if len(caption) > 88:
            caption = caption[:85].rstrip() + "..."
        scenes.append(
            Scene(
                number=i + 1,
                title=f"Scene {i + 1}",
                narration=sentence,
                caption=caption,
                background_prompt=prompt,
                character_pose=pose,
                camera=cameras[i % len(cameras)],
                duration=round(scene_duration, 2),
            )
        )
    return scenes


def call_fastsd(prompt: str, output_path: Path, width: int, height: int, openvino: bool) -> float:
    payload = {
        "prompt": prompt,
        "use_openvino": openvino,
        "image_width": width,
        "image_height": height,
        "inference_steps": 1,
        "guidance_scale": 1.0,
        "number_of_images": 1,
    }
    data = json.dumps(payload).encode("utf-8")
    request = Request(FASTSD_API, data=data, headers={"Content-Type": "application/json"}, method="POST")
    started = time.time()
    with urlopen(request, timeout=900) as response:
        result = json.loads(response.read().decode("utf-8"))
    if result.get("error"):
        raise RuntimeError(result["error"])
    output_path.write_bytes(base64.b64decode(result["images"][0]))
    return float(result.get("latency") or (time.time() - started))


def generate_piper_voice(text: str, output_path: Path) -> float | None:
    if not (PIPER.exists() and PIPER_MODEL.exists() and PIPER_CONFIG.exists()):
        return None
    input_path = output_path.with_suffix(".txt")
    input_path.write_text(text, encoding="utf-8")
    subprocess.run(
        [
            str(PIPER),
            "--model",
            str(PIPER_MODEL),
            "--config",
            str(PIPER_CONFIG),
            "--input-file",
            str(input_path),
            "--output-file",
            str(output_path),
        ],
        check=True,
        cwd=str(ROOT),
    )
    try:
        with wave.open(str(output_path), "rb") as wav:
            return wav.getnframes() / float(wav.getframerate())
    except wave.Error:
        return None


def generate_edge_voice(text: str, output_path: Path, voice: str) -> float | None:
    if not EDGE_TTS.exists():
        return None
    mp3_path = output_path.with_suffix(".mp3")
    subprocess.run(
        [
            str(EDGE_TTS),
            "--voice",
            voice,
            "--text",
            text,
            "--write-media",
            str(mp3_path),
        ],
        check=True,
        cwd=str(ROOT),
    )
    return None


def write_omnivoice_note(output_path: Path) -> None:
    output_path.with_suffix(".omnivoice.txt").write_text(
        "OmniVoice is configured as an advanced external provider.\n"
        "It is open-source and supports multilingual zero-shot voice cloning, "
        "but it is too heavy for this laptop's CPU workflow.\n\n"
        "Recommended path:\n"
        "1. Open the OmniVoice Colab notebook from the project README.\n"
        "2. Upload this project's narration text.\n"
        "3. Generate/clone the voice on Colab GPU.\n"
        "4. Download the WAV/MP3 into this voices folder as narration.wav.\n",
        encoding="utf-8",
    )


def generate_voice(text: str, output_path: Path, provider: str, voice: str) -> tuple[str | None, float | None]:
    if provider == "edge":
        duration = generate_edge_voice(text, output_path, voice)
        mp3_path = output_path.with_suffix(".mp3")
        if mp3_path.exists():
            return str(mp3_path), duration
        return None, duration
    if provider == "omnivoice":
        write_omnivoice_note(output_path)
        return None, None
    duration = generate_piper_voice(text, output_path)
    if output_path.exists():
        return str(output_path), duration
    return None, duration


def write_srt(scenes: list[Scene], output_path: Path) -> None:
    def fmt(seconds: float) -> str:
        ms = int((seconds - int(seconds)) * 1000)
        seconds = int(seconds)
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        return f"{h:02}:{m:02}:{s:02},{ms:03}"

    cursor = 0.0
    lines: list[str] = []
    for scene in scenes:
        start = cursor
        end = cursor + scene.duration
        lines.extend([str(scene.number), f"{fmt(start)} --> {fmt(end)}", scene.caption, ""])
        cursor = end
    output_path.write_text("\n".join(lines), encoding="utf-8")


def make_placeholder_assets(project_dir: Path) -> None:
    stickman = project_dir / "characters" / "stickman"
    stickman.mkdir(parents=True, exist_ok=True)
    readme = stickman / "README.txt"
    readme.write_text(
        "Put transparent PNG pose assets here, e.g. neutral.png, talking.png, shocked.png.\n"
        "The manifest already assigns poses per scene.\n",
        encoding="utf-8",
    )


def create_project(config: dict) -> dict:
    topic = str(config.get("topic") or "A simple faceless video").strip()
    style = str(config.get("style") or "general")
    mode = str(config.get("mode") or "fast")
    minutes = float(config.get("minutes") or 3)
    scene_count = int(config.get("scene_count") or (18 if mode == "fast" else 40))
    width = int(config.get("width") or 512)
    height = int(config.get("height") or 512)
    generate_backgrounds = bool(config.get("generate_backgrounds", True))
    generate_narration = bool(config.get("generate_narration", True))
    openvino = bool(config.get("openvino", False))
    planner = str(config.get("planner") or "local")
    voice_provider = str(config.get("voice_provider") or "piper")
    voice = str(config.get("voice") or "en-US-AriaNeural")
    custom_script = str(config.get("script") or "").strip() or None

    stamp = time.strftime("%Y%m%d-%H%M%S")
    project_name = f"{stamp}-{slugify(topic)}"
    project_dir = PROJECTS / project_name
    dirs = {
        "backgrounds": project_dir / "backgrounds",
        "voices": project_dir / "voices",
        "captions": project_dir / "captions",
        "manifests": project_dir / "manifests",
        "characters": project_dir / "characters",
        "exports": project_dir / "exports",
    }
    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)

    script = custom_script
    if not script and planner == "gemini":
        script = make_gemini_script(topic, style, minutes)
    script = script or make_script(topic, style, minutes)
    scenes = build_scenes(topic, style, scene_count, minutes, script)

    latencies: list[float] = []
    if generate_backgrounds:
        for scene in scenes:
            image_path = dirs["backgrounds"] / f"scene_{scene.number:03}.jpg"
            latency = call_fastsd(scene.background_prompt, image_path, width, height, openvino)
            latencies.append(latency)
            scene.background_file = str(image_path.relative_to(project_dir))

    narration_file = None
    narration_duration = None
    if generate_narration:
        narration_text = " ".join(scene.narration for scene in scenes)
        narration_path = dirs["voices"] / "narration.wav"
        generated_voice_path, narration_duration = generate_voice(
            narration_text, narration_path, voice_provider, voice
        )
        if generated_voice_path:
            narration_file = str(Path(generated_voice_path).relative_to(project_dir))

    write_srt(scenes, dirs["captions"] / "captions.srt")
    make_placeholder_assets(project_dir)

    manifest = {
        "topic": topic,
        "style": style,
        "mode": mode,
        "minutes": minutes,
        "scene_count": scene_count,
        "script": script,
        "planner": planner,
        "voice_provider": voice_provider,
        "voice": voice,
        "narration_file": narration_file,
        "narration_duration": narration_duration,
        "captions_file": "captions/captions.srt",
        "average_background_latency": round(sum(latencies) / len(latencies), 2) if latencies else None,
        "scenes": [asdict(scene) for scene in scenes],
        "next_steps": [
            "Add transparent stickman or presenter PNG poses under characters/stickman.",
            "Use the manifest to assemble in Kdenlive/OpenToonz, or add FFmpeg rendering next.",
        ],
    }
    (dirs["manifests"] / "episode.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (project_dir / "script.txt").write_text(script, encoding="utf-8")

    return {
        "project": project_name,
        "project_dir": str(project_dir),
        "manifest": str((dirs["manifests"] / "episode.json")),
        "summary": manifest,
    }


class Handler(BaseHTTPRequestHandler):
    def send_json(self, value: dict, status: int = 200) -> None:
        body = json.dumps(value).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, path: Path, content_type: str) -> None:
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path in ("/", "/index.html"):
            self.send_file(APP_ROOT / "static" / "index.html", "text/html; charset=utf-8")
            return
        if self.path == "/style.css":
            self.send_file(APP_ROOT / "static" / "style.css", "text/css; charset=utf-8")
            return
        if self.path == "/app.js":
            self.send_file(APP_ROOT / "static" / "app.js", "application/javascript; charset=utf-8")
            return
        if self.path == "/api/status":
            fastsd = False
            try:
                req = Request("http://127.0.0.1:8000/api/info", method="GET")
                with urlopen(req, timeout=3):
                    fastsd = True
            except Exception:
                pass
            self.send_json(
                {
                    "fastsd_api": fastsd,
                    "piper": PIPER.exists() and PIPER_MODEL.exists(),
                    "edge_tts": EDGE_TTS.exists(),
                    "gemini": bool(os.environ.get("GEMINI_API_KEY", "").strip()),
                    "omnivoice": "external_colab_recommended",
                    "projects_dir": str(PROJECTS),
                    "styles": {key: value["label"] for key, value in STYLE_PRESETS.items()},
                }
            )
            return
        self.send_error(404)

    def do_POST(self) -> None:
        if self.path != "/api/create":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8")
        try:
            config = json.loads(raw or "{}")
            result = create_project(config)
            self.send_json(result)
        except URLError as exc:
            self.send_json({"error": f"FastSD API is not reachable: {exc}"}, 503)
        except Exception as exc:
            self.send_json({"error": str(exc)}, 500)


def main() -> int:
    port = int(os.environ.get("FREECALLIOPE_PORT", "8787"))
    PROJECTS.mkdir(exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"FreeCalliope running at http://127.0.0.1:{port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

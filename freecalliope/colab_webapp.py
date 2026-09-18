from __future__ import annotations

import json
from pathlib import Path

import gradio as gr

from freecalliope.colab_pipeline import run_pipeline


STYLE_OPTIONS = [
    "auto",
    "ink_explainer",
    "finance",
    "stickman_story",
    "documentary",
    "history",
    "scary_story",
    "general",
]

PLATFORM_OPTIONS = ["youtube", "shorts", "tiktok", "reels"]
MODE_OPTIONS = ["flow_fast", "classic_fast"]
MODEL_OPTIONS = ["stabilityai/sdxl-turbo", "stabilityai/sd-turbo"]
VOICE_OPTIONS = ["edge", "gtts", "omnivoice"]
EDGE_VOICES = [
    "en-US-AriaNeural",
    "en-US-GuyNeural",
    "en-US-JennyNeural",
    "en-GB-RyanNeural",
    "en-GB-SoniaNeural",
]


def video_size(platform: str) -> tuple[int, int]:
    if platform in {"shorts", "tiktok", "reels"}:
        return 576, 1024
    return 1024, 576


def read_text(path: Path, fallback: str = "") -> str:
    if path.exists():
        return path.read_text(encoding="utf-8")
    return fallback


def existing_file(path: str | Path | None) -> str | None:
    if not path:
        return None
    file_path = Path(path)
    if file_path.exists() and file_path.stat().st_size > 0:
        return str(file_path)
    return None


def generate_video(
    topic: str,
    style: str,
    platform: str,
    generation_mode: str,
    minutes: float,
    scene_count: int,
    image_model: str,
    steps: int,
    voice_provider: str,
    edge_voice: str,
    omnivoice_audio_path: str,
    gemini_api_key: str,
) -> tuple[str, str | None, str | None, str | None, str, str, str]:
    try:
        topic = topic.strip()
        if not topic:
            raise gr.Error("Add a topic first.")
        if voice_provider == "omnivoice" and not omnivoice_audio_path.strip():
            raise gr.Error("OmniVoice mode needs an audio file path, like /content/omnivoice_output.wav.")

        width, height = video_size(platform)
        result = run_pipeline(
            topic=topic,
            style=style,
            platform=platform,
            generation_mode=generation_mode,
            minutes=float(minutes),
            scene_count=int(scene_count),
            gemini_key=gemini_api_key or None,
            image_model=image_model,
            width=width,
            height=height,
            steps=int(steps),
            guidance_scale=0.0,
            voice_provider=voice_provider,
            edge_voice=edge_voice,
            omnivoice_audio_path=omnivoice_audio_path.strip() or None,
        )

        project = Path(result["project_dir"])
        video_path = existing_file(result.get("video_path"))
        zip_path = existing_file(result.get("zip_path"))
        thumbnail_path = project / "thumbnails" / "thumbnail.jpg"
        script = read_text(project / "script.txt")
        storyboard = read_text(project / "storyboard.md")
        metadata = read_text(project / "metadata.json", json.dumps(result.get("metadata", {}), indent=2))
        status = (
            f"Generated `{result['style']}` video for `{platform}`.\n\n"
            f"Video: `{video_path}`\n\n"
            f"Zip: `{zip_path}`"
        )
        return status, video_path, zip_path, existing_file(thumbnail_path), script, storyboard, metadata
    except gr.Error:
        raise
    except Exception as exc:
        raise gr.Error(f"Generation failed: {type(exc).__name__}: {exc}") from exc


CSS = """
:root {
  --fc-ink: #171717;
  --fc-paper: #f7f2e8;
  --fc-panel: #ffffff;
  --fc-line: #ded7c8;
  --fc-accent: #2f6fed;
  --fc-green: #11a36a;
}
.gradio-container {
  background: linear-gradient(180deg, #f7f2e8 0%, #eef3fb 100%);
  color: var(--fc-ink);
}
.fc-shell {
  max-width: 1220px;
  margin: 0 auto;
}
.fc-hero {
  padding: 26px 28px 18px;
  border-bottom: 1px solid var(--fc-line);
}
.fc-title {
  font-size: 32px;
  font-weight: 800;
  margin: 0;
}
.fc-subtitle {
  font-size: 15px;
  color: #555;
  margin-top: 6px;
}
.fc-badge {
  display: inline-block;
  padding: 5px 9px;
  border: 1px solid #b9c7e8;
  background: #eef4ff;
  color: #254b98;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  margin-right: 6px;
}
.fc-card {
  border: 1px solid var(--fc-line) !important;
  background: rgba(255,255,255,0.88) !important;
  border-radius: 12px !important;
  box-shadow: 0 12px 34px rgba(22, 31, 49, 0.08);
}
.fc-run button {
  min-height: 48px !important;
  font-weight: 800 !important;
  background: var(--fc-ink) !important;
  border: 1px solid var(--fc-ink) !important;
}
"""


def build_app() -> gr.Blocks:
    with gr.Blocks(css=CSS, title="FreeCalliope Studio") as app:
        gr.HTML(
            """
            <div class="fc-shell fc-hero">
              <div>
                <span class="fc-badge">Colab GPU Studio</span>
                <span class="fc-badge">Flow Fast</span>
                <span class="fc-badge">Faceless Video</span>
              </div>
              <h1 class="fc-title">FreeCalliope Studio</h1>
              <div class="fc-subtitle">Build faceless videos from a topic: script, storyboard, AI scenes, voice, captions, thumbnail, and MP4.</div>
            </div>
            """
        )

        with gr.Row(elem_classes=["fc-shell"]):
            with gr.Column(scale=5, elem_classes=["fc-card"]):
                gr.Markdown("### Project")
                topic = gr.Textbox(
                    label="Video Topic",
                    value="What did ancient humans actually do all day?",
                    lines=4,
                    placeholder="Describe any faceless video idea...",
                )
                with gr.Row():
                    style = gr.Dropdown(STYLE_OPTIONS, value="auto", label="Style")
                    platform = gr.Dropdown(PLATFORM_OPTIONS, value="youtube", label="Platform")
                    generation_mode = gr.Dropdown(MODE_OPTIONS, value="flow_fast", label="Generation Mode")
                with gr.Row():
                    minutes = gr.Slider(0.5, 12, value=3, step=0.5, label="Length")
                    scene_count = gr.Slider(4, 48, value=12, step=1, label="Scenes")
                    steps = gr.Slider(1, 8, value=3, step=1, label="Image Steps")

                gr.Markdown("### Visuals And Voice")
                image_model = gr.Dropdown(MODEL_OPTIONS, value="stabilityai/sdxl-turbo", label="Image Model")
                with gr.Row():
                    voice_provider = gr.Dropdown(VOICE_OPTIONS, value="edge", label="Voice Provider")
                    edge_voice = gr.Dropdown(EDGE_VOICES, value="en-US-AriaNeural", label="Edge Voice")
                omnivoice_audio_path = gr.Textbox(
                    label="OmniVoice Audio Path",
                    placeholder="/content/omnivoice_output.wav",
                    value="",
                )
                gemini_api_key = gr.Textbox(
                    label="Gemini Key",
                    placeholder="Optional Google AI Studio key for stronger scripts",
                    value="",
                    type="password",
                )
                run = gr.Button("Generate Video", variant="primary", elem_classes=["fc-run"])

            with gr.Column(scale=7, elem_classes=["fc-card"]):
                gr.Markdown("### Preview And Downloads")
                status = gr.Markdown("Ready.")
                video = gr.Video(label="Final MP4")
                with gr.Row():
                    zip_file = gr.File(label="Project Zip")
                    thumbnail = gr.Image(label="Thumbnail", type="filepath")
                with gr.Tabs():
                    with gr.Tab("Script"):
                        script = gr.Textbox(lines=16, show_label=False)
                    with gr.Tab("Storyboard"):
                        storyboard = gr.Textbox(lines=16, show_label=False)
                    with gr.Tab("Metadata"):
                        metadata = gr.Code(language="json", label="metadata.json")

        run.click(
            generate_video,
            inputs=[
                topic,
                style,
                platform,
                generation_mode,
                minutes,
                scene_count,
                image_model,
                steps,
                voice_provider,
                edge_voice,
                omnivoice_audio_path,
                gemini_api_key,
            ],
            outputs=[status, video, zip_file, thumbnail, script, storyboard, metadata],
        )
    return app


def launch(share: bool = True) -> None:
    build_app().queue().launch(share=share, debug=True)


if __name__ == "__main__":
    launch()

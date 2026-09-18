# FreeCalliope

FreeCalliope is a free, Colab-first faceless animation project generator inspired by CalliopeLabs-style workflows.

It turns a topic into a video project pack:

- script
- scene list
- Flow Fast storyboard
- edit decision list
- AI backgrounds
- narration
- captions
- animated camera movement
- thumbnail image
- title ideas, description, tags, hashtags
- rendered MP4 video
- manifest JSON
- zipped output

The main target is Google Colab, so users do not need a strong computer.

## Quick Start On Google Colab

1. Open the notebook:

   ```text
   notebooks/FreeCalliope_Colab.ipynb
   ```

2. In Colab, run the setup cell.

3. Enter a topic, style, platform, number of scenes, and voice.

4. Run generation.

5. Download the finished MP4 and the zip from `outputs/`.

## Styles

- Auto Faceless
- Ink Explainer
- Finance Explainer
- Stickman Story
- Mini Documentary
- History Explainer
- Scary Story
- General Faceless

Use `STYLE = "auto"` when you want the tool to choose the best faceless format from the topic.

## Platforms

- `youtube`: 16:9 long-form videos
- `shorts`: vertical short videos
- `tiktok`: vertical short videos
- `reels`: vertical short videos

## Generation Modes

- `flow_fast`: Google Flow-style planning with shots, camera moves, transitions, SFX cues, storyboard, edit decision list, AI backgrounds, and fast video rendering.
- `classic_fast`: simpler scene generation for the fastest basic output.

`flow_fast` is the recommended default. It is designed to feel like a free Colab-friendly Flow workflow without using slow text-to-video generation by default.

## Optional Gemini Script Planning

FreeCalliope can use Gemini for better scripts if you provide a free Google AI Studio key.

1. Get a key from:

   ```text
   https://aistudio.google.com/app/apikey
   ```

2. In Colab, set:

   ```python
   GEMINI_API_KEY = "your-key-here"
   ```

If no key is provided, FreeCalliope uses local script templates.

## Voice Providers

Colab mode supports:

- Edge TTS voices, no key
- gTTS fallback, no key
- OmniVoice audio import, documented in `freecalliope/OMNIVOICE.md`

## Image Generation

Colab mode uses Hugging Face Diffusers. On GPU it is much faster than CPU-only local generation.

Default model:

```text
stabilityai/sdxl-turbo
```

Recommended fast Colab settings:

```python
IMAGE_MODEL = "stabilityai/sdxl-turbo"
WIDTH = 1024
HEIGHT = 576
STEPS = 3
GUIDANCE_SCALE = 0.0
```

If SDXL Turbo cannot load in a Colab session, the pipeline falls back to `stabilityai/sd-turbo`.

## Local Windows Mode

Local mode is still available, but it is slower and secondary.

See:

```text
START_HERE.md
```

## Repository Layout

```text
freecalliope/
  colab_pipeline.py      # Colab-first generator
  app.py                 # Local web app
  static/                # Local web UI
notebooks/
  FreeCalliope_Colab.ipynb
outputs/                 # Generated project zips in Colab
```

## Output Files

Each run creates a project folder with:

```text
videos/final.mp4
thumbnails/thumbnail.jpg
backgrounds/scene_###.jpg
voices/narration.mp3
captions/captions.srt
storyboard.md
edit_decision_list.json
metadata.json
manifests/episode.json
script.txt
```

## Important Limits

This is a free/open-source pipeline, not paid cloud infrastructure.

Colab free GPU availability is not guaranteed. If no GPU is available, generation still works but will be slower.

The renderer creates captioned scene videos with AI backgrounds, a reusable stickman overlay, Flow Fast shot planning, transitions, and Ken Burns style camera motion. More advanced character motion, mouth movement, and full text-to-video clips can be added later, but those are slower on free Colab.

# FreeCalliope

FreeCalliope is a local, CPU-first faceless video project generator. It is not a paid cloud renderer; it builds an organized project pack using free tools on this machine.

## What It Does Now

- Runs as a local web app at `http://127.0.0.1:8787`
- Accepts a topic, style, length, and scene count
- Creates a starter script
- Splits the script into scenes
- Generates scene background prompts
- Calls FastSD CPU for AI still backgrounds
- Calls Piper for local narration
- Supports Edge TTS voices as another free/no-key voice option
- Supports optional Gemini script planning through `.env`
- Documents OmniVoice as an external Colab/GPU provider
- Writes captions as SRT
- Writes `manifests/episode.json` for editing/assembly
- Creates a placeholder character pose folder

## Current Styles

- Finance Explainer
- Stickman Story
- General Faceless

## Start

```powershell
powershell -ExecutionPolicy Bypass -File C:\Video\tools\start-freecalliope.ps1
```

## Requirements

FastSD CPU API should be running:

```powershell
cd C:\Video\fastsdcpu
.\start-webserver.bat
```

Piper is already installed at:

```text
C:\Video\piper-env
```

Optional Gemini planning:

1. Copy `.env.example` to `.env`.
2. Add a free Google AI Studio key as `GEMINI_API_KEY=...`.
3. Restart FreeCalliope.

OmniVoice:

- See `freecalliope/OMNIVOICE.md`.
- Use the Colab notebook for voice cloning/multilingual generation.

## Next Features

- FFmpeg auto-renderer for rough MP4 exports
- Reusable stickman/presenter PNG asset library
- Kdenlive project export
- Browser/manual AI connector for ChatGPT/Claude scene planning without API keys
- More style templates

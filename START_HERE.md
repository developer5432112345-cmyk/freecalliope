# Local Stickman Video Pipeline

This folder is set up for a lightweight Mack-style stickman channel workflow.

## Running Services

FastSD CPU Web UI:

```powershell
cd C:\Video\fastsdcpu
.\start-webui.bat
```

Open in browser:

```text
http://127.0.0.1:7860
```

FastSD CPU API for batch generation:

```powershell
cd C:\Video\fastsdcpu
.\start-webserver.bat
```

API address:

```text
http://127.0.0.1:8000
```

## Generate Backgrounds

Edit prompts here:

```text
C:\Video\prompts\background_prompts.txt
```

Generate numbered scene backgrounds:

```powershell
powershell -ExecutionPolicy Bypass -File C:\Video\tools\generate-backgrounds.ps1
```

Outputs:

```text
C:\Video\backgrounds\scene_001.jpg
C:\Video\backgrounds\scene_002.jpg
...
```

## Generate Voice

Edit narration here:

```text
C:\Video\scripts\narration.txt
```

Generate narration WAV:

```powershell
powershell -ExecutionPolicy Bypass -File C:\Video\tools\generate-voice.ps1
```

Output:

```text
C:\Video\voices\narration.wav
```

## Installed Tools

- FastSD CPU: AI still backgrounds/assets
- Piper TTS: local AI narration
- OpenToonz: stickman/2D animation
- Kdenlive: final editing
- Blender LTS 4.2: simple 3D backgrounds/props
- FreeCalliope: local CalliopeLabs-style web app

## FreeCalliope Web App

Start the local app:

```powershell
powershell -ExecutionPolicy Bypass -File C:\Video\tools\start-freecalliope.ps1
```

Open:

```text
http://127.0.0.1:8787
```

FreeCalliope creates project packs under:

```text
C:\Video\projects
```

Optional Gemini script planning:

```powershell
copy C:\Video\.env.example C:\Video\.env
notepad C:\Video\.env
```

Add your free Google AI Studio key to `GEMINI_API_KEY`, then restart FreeCalliope.

OmniVoice support is documented at:

```text
C:\Video\freecalliope\OMNIVOICE.md
```

## Practical Settings

- Use 512x512 or 768x768 AI backgrounds.
- Keep prompts simple and consistent.
- Animate stickmen in OpenToonz; use AI for backgrounds, props, thumbnails, and concepts.
- Generate large batches overnight.

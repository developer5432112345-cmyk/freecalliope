$ErrorActionPreference = "Stop"

Set-Location "C:\Video"

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    winget install --id Git.Git --source winget --accept-package-agreements --accept-source-agreements
}

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    winget install --id Python.Python.3.11 --source winget --accept-package-agreements --accept-source-agreements
}

python -m pip install --user -U uv
$env:Path = "$env:APPDATA\Python\Python314\Scripts;$env:APPDATA\Python\Python311\Scripts;$env:Path"

if (-not (Test-Path "C:\Video\fastsdcpu\env")) {
    git clone https://github.com/rupeshs/fastsdcpu.git C:\Video\fastsdcpu
    Set-Location "C:\Video\fastsdcpu"
    .\install.bat
    Set-Location "C:\Video"
}

if (-not (Test-Path "C:\Video\piper-env")) {
    uv venv --python 3.11.6 C:\Video\piper-env
}

uv pip install --python C:\Video\piper-env\Scripts\python.exe piper-tts edge-tts

New-Item -ItemType Directory -Force -Path C:\Video\voices\piper-models | Out-Null
if (-not (Test-Path "C:\Video\voices\piper-models\en_US-amy-low.onnx")) {
    Invoke-WebRequest -Uri https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/low/en_US-amy-low.onnx -OutFile C:\Video\voices\piper-models\en_US-amy-low.onnx
    Invoke-WebRequest -Uri https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/low/en_US-amy-low.onnx.json -OutFile C:\Video\voices\piper-models\en_US-amy-low.onnx.json
}

winget install --id DWANGO.OpenToonz --source winget --accept-package-agreements --accept-source-agreements --silent
winget install --id KDE.Kdenlive --source winget --accept-package-agreements --accept-source-agreements --silent
winget install --id BlenderFoundation.Blender.LTS.4.2 --source winget --accept-package-agreements --accept-source-agreements --silent

if (-not (Test-Path "C:\Video\.env")) {
    Copy-Item "C:\Video\.env.example" "C:\Video\.env"
}

Write-Host "Install complete. Start FastSD API, then FreeCalliope:"
Write-Host "  cd C:\Video\fastsdcpu; .\start-webserver.bat"
Write-Host "  powershell -ExecutionPolicy Bypass -File C:\Video\tools\start-freecalliope.ps1"

param(
    [string]$TextFile = "C:\Video\scripts\narration.txt",
    [string]$OutputFile = "C:\Video\voices\narration.wav",
    [string]$Model = "C:\Video\voices\piper-models\en_US-amy-low.onnx",
    [string]$Config = "C:\Video\voices\piper-models\en_US-amy-low.onnx.json"
)

if (-not (Test-Path -LiteralPath $TextFile)) {
    throw "Narration file not found: $TextFile"
}

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $OutputFile) | Out-Null
C:\Video\piper-env\Scripts\piper.exe `
    --model $Model `
    --config $Config `
    --input-file $TextFile `
    --output-file $OutputFile

Write-Host "Saved $OutputFile"

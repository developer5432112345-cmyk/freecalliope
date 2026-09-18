param(
    [string]$PromptFile = "C:\Video\prompts\background_prompts.txt",
    [string]$OutputDir = "C:\Video\backgrounds",
    [string]$ApiUrl = "http://127.0.0.1:8000/api/generate",
    [int]$Width = 512,
    [int]$Height = 512,
    [int]$Steps = 1,
    [decimal]$Guidance = 1.0,
    [switch]$OpenVino
)

if (-not (Test-Path -LiteralPath $PromptFile)) {
    throw "Prompt file not found: $PromptFile"
}

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$prompts = Get-Content -LiteralPath $PromptFile | ForEach-Object { [string]$_ } | Where-Object {
    $_.Trim() -and -not $_.Trim().StartsWith("#")
}

$index = 1
foreach ($prompt in $prompts) {
    $name = "scene_{0:D3}.jpg" -f $index
    $path = Join-Path $OutputDir $name

    Write-Host "Generating $name..."
    $body = @{
        prompt = [string]$prompt
        use_openvino = [bool]$OpenVino
        image_width = $Width
        image_height = $Height
        inference_steps = $Steps
        guidance_scale = $Guidance
        number_of_images = 1
    } | ConvertTo-Json

    $response = Invoke-RestMethod -Uri $ApiUrl -Method Post -Body $body -ContentType "application/json" -ErrorAction Stop
    if ($response.error) {
        throw "Generation failed for scene $index`: $($response.error)"
    }

    [IO.File]::WriteAllBytes($path, [Convert]::FromBase64String($response.images[0]))
    Write-Host "Saved $path latency=$($response.latency)s"
    $index++
}

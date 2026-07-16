param(
    [int]$PlayerPort = 8080,
    [int]$StreamerPort = 8888
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$InfrastructureDir = Join-Path $ScriptDir "PixelStreamingInfrastructure"
$ServerDir = Join-Path $InfrastructureDir "SignallingWebServer"
$NodeBin = "C:\Users\cloud\AppData\Local\OpenAI\Codex\runtimes\cua_node\03b1cdac8af3a530\bin"
$NodeExe = Join-Path $NodeBin "node.exe"
$ServerEntry = Join-Path $ServerDir "dist\index.js"
$HttpRoot = Join-Path $ServerDir "www"

if (!(Test-Path -LiteralPath $NodeExe)) {
    throw "node.exe not found at $NodeExe"
}
if (!(Test-Path -LiteralPath $ServerEntry)) {
    throw "SignallingWebServer is not built. Run npm install and npm run build in $InfrastructureDir first."
}
if (!(Test-Path -LiteralPath (Join-Path $HttpRoot "player.html"))) {
    throw "Pixel Streaming player.html not found in $HttpRoot"
}

$env:Path = "$NodeBin;$env:Path"

Write-Host "Starting Pixel Streaming Signalling/Web Server"
Write-Host "Player URL: http://localhost:$PlayerPort"
Write-Host "Unreal streamer URL: ws://127.0.0.1:$StreamerPort"

& $NodeExe $ServerEntry `
    --serve `
    --player_port "$PlayerPort" `
    --streamer_port "$StreamerPort" `
    --http_root "$HttpRoot" `
    --homepage "player.html" `
    --console_messages "verbose" `
    --log_config `
    --https_redirect false

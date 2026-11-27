
param(
    [string]$Command = 'WriteToLog("Hello from Python!", "green")'
)

$ErrorActionPreference = "Stop"

$dll = "C:\ti\mmwave_studio_02_01_01_00\mmWaveStudio\Clients\RtttNetClientController\RtttNetClientAPI.dll"
Add-Type -Path $dll

$status = [RtttNetClientAPI.RtttNetClient]::Init()

if ($status -ne 0) {
    throw "Initialization failed: $status"
}

$status = [RtttNetClientAPI.RtttNetClient]::Connect(
    "127.0.0.1", 2777
)

if ($status -ne 0) {
    throw "Connection failed: $status"
}

Write-Host "Connected to RSTD"

Start-Sleep -Seconds 1

[object[]]$response = @()

Write-Host "Sending Lua command: $Command"

$status = [RtttNetClientAPI.RtttNetClient]::SendCommand(
    $Command,
    [ref]$response
)

Write-Host "Command status: $status"
Write-Host "Response: $response"

if ($status -ne 0) {
    throw "Lua command failed: $status"
}

Write-Host "Command executed successfully!"
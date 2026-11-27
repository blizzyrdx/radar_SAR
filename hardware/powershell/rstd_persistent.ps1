
$ErrorActionPreference = "Stop"

$dll = "C:\ti\mmwave_studio_02_01_01_00\mmWaveStudio\Clients\RtttNetClientController\RtttNetClientAPI.dll"

Add-Type -Path $dll

# Initialize the client once
$status = [RtttNetClientAPI.RtttNetClient]::Init()

if ($status -ne 0) {
    throw "Initialization failed: $status"
}

# Connect to mmWave Studio once
$status = [RtttNetClientAPI.RtttNetClient]::Connect(
    "127.0.0.1", 2777
)

if ($status -ne 0) {
    throw "Connection failed: $status"
}

Start-Sleep -Seconds 1

[Console]::WriteLine("RSTD_READY")

# Keep the connection open
while ($true) {

    $command = [Console]::ReadLine()

    if ($null -eq $command) {
        break
    }

    if ($command -eq "EXIT") {
        break
    }

    try {

        [object[]]$response = @()

        $status = [RtttNetClientAPI.RtttNetClient]::SendCommand(
            $command,
            [ref]$response
        )

        [Console]::WriteLine("STATUS:$status")

    }
    catch {

        [Console]::WriteLine(
            "ERROR:" + $_.Exception.Message
        )

    }
}

[Console]::WriteLine("SESSION_CLOSED")

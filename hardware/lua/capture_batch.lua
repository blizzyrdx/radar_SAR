
-- ==========================================
-- Automated Batch Radar Acquisition
-- AWR1843AoP + DCA1000EVM
-- ==========================================

local output_dir = [[C:\ti\mmwave_studio_02_01_01_00\mmWaveStudio\PostProc\]]

local num_captures = 5

ar1.SelectCaptureDevice("DCA1000")

for i = 1, num_captures do

    local filename = string.format(
        "batch_capture_%03d.bin", i
    )

    local capture_path = output_dir .. filename

    -- Prevent overwriting existing recordings
    local existing = io.open(capture_path, "rb")

    if existing then
        existing:close()
        error("File already exists: " .. filename)
    end

    WriteToLog(
        "\nStarting capture " .. i ..
        "/" .. num_captures .. "\n",
        "green"
    )

    -- Arm DCA1000
    local status = ar1.CaptureCardConfig_StartRecord(
        capture_path, 1
    )

    if status ~= 0 then
        error("Failed to arm DCA1000")
    end

    RSTD.Sleep(3000)

    -- Trigger radar
    status = ar1.StartFrame()

    if status ~= 0 then
        error("Failed to trigger radar")
    end

    -- Allow capture to finish
    RSTD.Sleep(8000)

    WriteToLog(
        "Capture interval finished: " ..
        filename .. "\n",
        "green"
    )

end

WriteToLog(
    "\nBatch acquisition script finished!\n",
    "green"
)

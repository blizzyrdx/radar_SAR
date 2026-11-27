
    ar1.SelectCaptureDevice("DCA1000")

    WriteToLog("Arming DCA1000...\n", "green")

    local status = ar1.CaptureCardConfig_StartRecord(
        [[C:\ti\mmwave_studio_02_01_01_00\mmWaveStudio\PostProc\capture_20261126_162740_188213.bin]], 1
    )

    if status ~= 0 then
        error("DCA1000 ARM failed")
    end

    RSTD.Sleep(3000)

    WriteToLog("Triggering radar...\n", "green")

    status = ar1.StartFrame()

    if status ~= 0 then
        error("Frame trigger failed")
    end

    RSTD.Sleep(8000)

    WriteToLog("Processing captured data...\n", "green")

    ar1.StartMatlabPostProc([[C:\ti\mmwave_studio_02_01_01_00\mmWaveStudio\PostProc\capture_20261126_162740_188213.bin]])
    

    ar1.SelectCaptureDevice("DCA1000")

    local status = ar1.CaptureCardConfig_StartRecord(
        [[C:/ti/mmwave_studio_02_01_01_00/mmWaveStudio/PostProc/capture_20261126_160544_635406.bin]], 1
    )

    if status ~= 0 then
        error("DCA1000 ARM failed")
    end

    RSTD.Sleep(3000)

    status = ar1.StartFrame()

    if status ~= 0 then
        error("Frame trigger failed")
    end

    RSTD.Sleep(8000)

    ar1.StartMatlabPostProc([[C:/ti/mmwave_studio_02_01_01_00/mmWaveStudio/PostProc/capture_20261126_160544_635406.bin]])
    
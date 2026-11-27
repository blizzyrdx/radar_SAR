
-- ==========================================
-- AWR1843AoP + DCA1000 Automated Capture
-- ==========================================

local capture_path = [[C:\ti\mmwave_studio_02_01_01_00\mmWaveStudio\PostProc\recovery_test_01.bin]]
-- Select DCA1000
ar1.SelectCaptureDevice("DCA1000")

-- Arm the capture card
WriteToLog("Arming DCA1000...\n", "green")

ar1.CaptureCardConfig_StartRecord(capture_path, 1)

-- Wait 3 seconds
RSTD.Sleep(3000)

-- Trigger radar frames
WriteToLog("Triggering radar...\n", "green")

local status = ar1.StartFrame()

if status ~= 0 then
    WriteToLog("Frame trigger failed!\n", "red")
    return
end

-- Allow recording to finish
RSTD.Sleep(5000)

-- Process captured ADC data
WriteToLog("Processing captured data...\n", "green")

ar1.StartMatlabPostProc(capture_path)

WriteToLog("Capture script finished.\n", "green")

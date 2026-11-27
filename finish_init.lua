
-- Resume interrupted radar initialization

WriteToLog("Resuming initialization...\n", "green")

local status = ar1.FrameConfig(
    0, 0, 8, 128, 40, 0, 0, 1
)

if status ~= 0 then
    error("Frame configuration failed")
end

WriteToLog("Frame configuration passed\n", "green")

-- Configure DCA1000

ar1.SelectCaptureDevice("DCA1000")

ar1.CaptureCardConfig_EthInit(
    "192.168.33.30",
    "192.168.33.180",
    "12:34:56:78:90:12",
    4096,
    4098
)

ar1.CaptureCardConfig_Mode(1, 2, 1, 2, 3, 30)

ar1.CaptureCardConfig_PacketDelay(25)

RSTD.Sleep(1000)

ar1.GetCaptureCardFPGAVersion()

WriteToLog("Initialization finished!\n", "green")

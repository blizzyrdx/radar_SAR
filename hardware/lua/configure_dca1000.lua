
-- DCA1000 Ethernet configuration
-- Run after radar initialization

local PACKET_DELAY = 50

WriteToLog("Configuring DCA1000...\n", "green")

ar1.SelectCaptureDevice("DCA1000")

ar1.CaptureCardConfig_EthInit(
    "192.168.33.30",
    "192.168.33.180",
    "12:34:56:78:90:12",
    4096,
    4098
)

ar1.CaptureCardConfig_Mode(1, 2, 1, 2, 3, 30)

ar1.CaptureCardConfig_PacketDelay(PACKET_DELAY)

RSTD.Sleep(1000)

ar1.GetCaptureCardFPGAVersion()

WriteToLog("Packet delay: " .. PACKET_DELAY .. " us\n", "green")

WriteToLog("DCA1000 configuration finished.\n", "green")

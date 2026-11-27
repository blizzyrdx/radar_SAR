
-- AWR1843AoP + DCA1000EVM
-- SAR high-bandwidth initialization
-- Run AFTER firmware loading and RF power-up
-- Run BEFORE RF Init

local function check(name, status)
    if status ~= 0 then
        error(name .. " failed: " .. tostring(status))
    end

    WriteToLog(name .. " passed\n", "green")
end

WriteToLog("Starting radar initialization...\n", "green")

-- ==========================================
-- Static Configuration
-- ==========================================

-- TX0 enabled, all four RX channels enabled
-- 16-bit complex ADC, I first

check("Channel and ADC configuration",
    ar1.ChanNAdcConfig(1, 0, 0, 1, 1, 1, 1, 2, 1, 0))

-- Required for AWR1843AoPEVM
check("RF LDO bypass",
    ar1.RfLdoBypassConfig(0x3))

check("Low power mode configuration",
    ar1.LPModConfig(0, 0))

RSTD.Sleep(500)

check("RF initialization", ar1.RfInit())

RSTD.Sleep(2000)

-- ==========================================
-- Data Configuration
-- ==========================================

check("Data path configuration",
    ar1.DataPathConfig(513, 1216644097, 0))

check("LVDS clock configuration",
    ar1.LvdsClkConfig(1, 1))

check("LVDS lane configuration",
    ar1.LVDSLaneConfig(0, 1, 1, 0, 0, 1, 0, 0))

-- ==========================================
-- High-bandwidth Profile
-- ==========================================

check("Profile configuration",
    ar1.ProfileConfig(
        0, 77, 100, 6, 65,
        0, 0, 0, 0, 0, 0,
        60.012, 0, 512, 10000,
        0, 0, 30
    ))

-- ==========================================
-- Chirp Configuration
-- ==========================================

check("Chirp configuration",
    ar1.ChirpConfig(
        0, 0, 0, 0, 0,
        0, 0, 1, 0, 0
    ))

ar1.DisableTestSource(0)

-- ==========================================
-- Frame Configuration
-- ==========================================

check("Frame configuration",
    ar1.FrameConfig(
        0, 0, 8, 128, 40, 0, 0, 1
    ))

-- ==========================================
-- DCA1000 Configuration
-- ==========================================

check("Select DCA1000",
    ar1.SelectCaptureDevice("DCA1000"))

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

WriteToLog("\nInitialization script finished!\n", "green")
WriteToLog("Check DCA1000 configuration status.\n", "green")

# https://github.com/MagilaWEB/unblock-youtube-discord
# https://github.com/ankddev/zapret-discord-youtube
import os

BIN_FOLDER = "bin"
BAT_FOLDER = "bat"
INDEXJSON_FOLDER = "json"
EXE_FOLDER = "exe"
ICO_FOLDER = "ico"
LISTS_FOLDER = "lists"
THEME_FOLDER = "themes"
LOGS_FOLDER = "logs"
WINWS_EXE = os.path.join(EXE_FOLDER, "winws.exe")
ICON_PATH = os.path.join(ICO_FOLDER, "zapret.ico")
ICON_TEST_PATH = os.path.join(ICO_FOLDER, "ZapretDevLogo.ico")

OTHER_PATH = os.path.join(LISTS_FOLDER, "other.txt")
OTHER2_PATH = os.path.join(LISTS_FOLDER, "other2.txt")
NETROGAT_PATH = os.path.join(LISTS_FOLDER, "netrogat.txt")
NETROGAT2_PATH = os.path.join(LISTS_FOLDER, "netrogat2.txt")
DEFAULT_STRAT = "Если эта стратегия не работает смени её!"
REG_LATEST_STRATEGY = "LastStrategy2"

# Настройки для GitHub стратегий
STRATEGIES_FOLDER = BAT_FOLDER

WIDTH = 450
HEIGHT = 680

# Discord TCP конфигурации

#DiscordFix (ALT v10).bat
Ankddev10_1 = ""


#$UDP6 = "--filter-udp=50000-65535 --dpi-desync=fake,split2 --dpi-desync-any-protocol --dpi-desync-cutoff=d2 --dpi-desync-fake-quic=quic_test_00.bin --new"
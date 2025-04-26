# https://github.com/MagilaWEB/unblock-youtube-discord
# https://github.com/ankddev/zapret-discord-youtube
import os

BIN_FOLDER, LISTS_FOLDER, APP_VERSION = "bin", "lists", "14.9.9.2"

WINWS_EXE = os.path.join(BIN_FOLDER, "winws.exe")
ICON_PATH = os.path.join(BIN_FOLDER, "zapret.ico")

# Настройки для GitHub стратегий
GITHUB_STRATEGIES_BASE_URL = "https://gitflic.ru/project/main1234/main1234/blob/raw?file="
GITHUB_STRATEGIES_JSON_URL = "https://gitflic.ru/project/main1234/main1234/blob/raw?file=index.json"
STRATEGIES_FOLDER = BIN_FOLDER

# Discord TCP конфигурации

#DiscordFix (ALT v10).bat
Ankddev10_1 = ""


#$UDP6 = "--filter-udp=50000-65535 --dpi-desync=fake,split2 --dpi-desync-any-protocol --dpi-desync-cutoff=d2 --dpi-desync-fake-quic={BIN_FOLDER}/quic_test_00.bin --new"
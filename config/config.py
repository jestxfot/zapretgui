# https://github.com/MagilaWEB/unblock-youtube-discord
# https://github.com/ankddev/zapret-discord-youtube
import os

# 2025.0.0.dev15
BIN_FOLDER, APP_VERSION = "bin", "16.0.1"
BIN_DIR = os.path.join(os.getcwd(), "bin")
WINWS_EXE = os.path.join(BIN_FOLDER, "winws.exe")
ICON_PATH = os.path.join(BIN_FOLDER, "zapret.ico")

OTHER_PATH = os.path.join(BIN_FOLDER, "other.txt")
NETROGAT_PATH = os.path.join(BIN_FOLDER, "netrogat.txt")

# Настройки для GitHub стратегий
STRATEGIES_FOLDER = BIN_FOLDER

WIDTH = 450
HEIGHT = 680

# Discord TCP конфигурации

#DiscordFix (ALT v10).bat
Ankddev10_1 = ""


#$UDP6 = "--filter-udp=50000-65535 --dpi-desync=fake,split2 --dpi-desync-any-protocol --dpi-desync-cutoff=d2 --dpi-desync-fake-quic={BIN_FOLDER}/quic_test_00.bin --new"
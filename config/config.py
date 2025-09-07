# https://github.com/MagilaWEB/unblock-youtube-discord
# https://github.com/ankddev/zapret-discord-youtube

#config/config.py
import os
import sys


MAIN_DIRECTORY = os.path.dirname(sys.executable)

# Все папки относительно MAIN_DIRECTORY
BIN_FOLDER = os.path.join(MAIN_DIRECTORY, "bin")
BAT_FOLDER = os.path.join(MAIN_DIRECTORY, "bat")
INDEXJSON_FOLDER = os.path.join(MAIN_DIRECTORY, "json")
EXE_FOLDER = os.path.join(MAIN_DIRECTORY, "exe")
ICO_FOLDER = os.path.join(MAIN_DIRECTORY, "ico")
LISTS_FOLDER = os.path.join(MAIN_DIRECTORY, "lists")
THEME_FOLDER = os.path.join(MAIN_DIRECTORY, "themes")
LOGS_FOLDER = os.path.join(MAIN_DIRECTORY, "logs")

# Настройка количества сохраняемых лог-файлов (опционально)
MAX_LOG_FILES = 50  # можно сделать настраиваемым через реестр

WINDIVERT_FILTER = os.path.join(MAIN_DIRECTORY, "windivert.filter")

# Пути к файлам
WINWS_EXE = os.path.join(EXE_FOLDER, "winws.exe")
ICON_PATH = os.path.join(ICO_FOLDER, "Zapret2.ico")
ICON_TEST_PATH = os.path.join(ICO_FOLDER, "ZapretDevLogo4.ico")

OTHER_PATH = os.path.join(LISTS_FOLDER, "other.txt")
OTHER2_PATH = os.path.join(LISTS_FOLDER, "other2.txt")
NETROGAT_PATH = os.path.join(LISTS_FOLDER, "netrogat.txt")
NETROGAT2_PATH = os.path.join(LISTS_FOLDER, "netrogat2.txt")

DEFAULT_STRAT = "Alt 2"
REG_LATEST_STRATEGY = "LastStrategy2"

# Настройки для GitHub стратегий
STRATEGIES_FOLDER = BAT_FOLDER

WIDTH = 450
HEIGHT = 730

# Discord TCP конфигурации

#DiscordFix (ALT v10).bat
Ankddev10_1 = ""

#$UDP6 = "--filter-udp=50000-65535 --dpi-desync=fake,split2 --dpi-desync-any-protocol --dpi-desync-cutoff=d2 --dpi-desync-fake-quic=quic_test_00.bin --new"

# Отладочная информация (можно убрать в продакшене)
if __name__ == "__main__":
    print(f"MAIN_DIRECTORY: {MAIN_DIRECTORY}")
    print(f"BAT_FOLDER: {BAT_FOLDER}")
    print(f"Существует BAT_FOLDER: {os.path.exists(BAT_FOLDER)}")
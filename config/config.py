# https://github.com/MagilaWEB/unblock-youtube-discord
# https://github.com/ankddev/zapret-discord-youtube

#config/config.py
import os, sys

MAIN_DIRECTORY = os.path.dirname(sys.executable)

# Все папки относительно MAIN_DIRECTORY
BIN_FOLDER = os.path.join(MAIN_DIRECTORY, "bin")
BAT_FOLDER = os.path.join(MAIN_DIRECTORY, "bat")
INDEXJSON_FOLDER = os.path.join(MAIN_DIRECTORY, "json")
EXE_FOLDER = os.path.join(MAIN_DIRECTORY, "exe")
LUA_FOLDER = os.path.join(MAIN_DIRECTORY, "lua")  # Lua библиотеки для Zapret 2
ICO_FOLDER = os.path.join(MAIN_DIRECTORY, "ico")
LISTS_FOLDER = os.path.join(MAIN_DIRECTORY, "lists")
THEME_FOLDER = os.path.join(MAIN_DIRECTORY, "themes")
LOGS_FOLDER = os.path.join(MAIN_DIRECTORY, "logs")
HELP_FOLDER = os.path.join(MAIN_DIRECTORY, "help")

# Настройка количества сохраняемых лог-файлов (опционально)
MAX_LOG_FILES = 50  # можно сделать настраиваемым через реестр

WINDIVERT_FILTER = os.path.join(MAIN_DIRECTORY, "windivert.filter")

# Пути к файлам
WINWS_EXE = os.path.join(EXE_FOLDER, "winws.exe")      # Для BAT режима (Zapret 1)
WINWS2_EXE = os.path.join(EXE_FOLDER, "winws2.exe")    # Для прямого запуска (Zapret 2)
ICON_PATH = os.path.join(ICO_FOLDER, "Zapret2.ico")
ICON_TEST_PATH = os.path.join(ICO_FOLDER, "ZapretDevLogo4.ico")

OTHER_PATH = os.path.join(LISTS_FOLDER, "other.txt")
OTHER2_PATH = os.path.join(LISTS_FOLDER, "other2.txt")
NETROGAT_PATH = os.path.join(LISTS_FOLDER, "netrogat.txt")
NETROGAT2_PATH = os.path.join(LISTS_FOLDER, "netrogat2.txt")

DEFAULT_STRAT = "Alt 2"
REG_LATEST_STRATEGY = "LastStrategy2"
REGISTRY_PATH = r"Software\ZapretReg2"

# Настройки для GitHub стратегий
STRATEGIES_FOLDER = BAT_FOLDER

WIDTH = 1000  # Увеличено для бокового меню в стиле Windows 11
HEIGHT = 950  # Увеличена высота для нового интерфейса

# Discord TCP конфигурации

#DiscordFix (ALT v10).bat
Ankddev10_1 = ""

#$UDP6 = "--filter-udp=50000-65535 --dpi-desync=fake,split2 --dpi-desync-any-protocol --dpi-desync-cutoff=d2 --dpi-desync-fake-quic=quic_test_00.bin --new"

# Отладочная информация (можно убрать в продакшене)
if __name__ == "__main__":
    print(f"MAIN_DIRECTORY: {MAIN_DIRECTORY}")
    print(f"BAT_FOLDER: {BAT_FOLDER}")
    print(f"Существует BAT_FOLDER: {os.path.exists(BAT_FOLDER)}")


def get_window_position():
    """Получает сохраненную позицию окна из реестра"""
    try:
        import winreg
        from log import log

        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH, 0, winreg.KEY_READ)
        try:
            x = winreg.QueryValueEx(key, "WindowX")[0]
            y = winreg.QueryValueEx(key, "WindowY")[0]
            winreg.CloseKey(key)
            return (x, y)
        except FileNotFoundError:
            winreg.CloseKey(key)
            return None
    except Exception as e:
        log(f"Ошибка чтения позиции окна: {e}", "DEBUG")
        return None

def set_window_position(x, y):
    """Сохраняет позицию окна в реестр"""
    try:
        import winreg
        from log import log

        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH)
        winreg.SetValueEx(key, "WindowX", 0, winreg.REG_DWORD, int(x))
        winreg.SetValueEx(key, "WindowY", 0, winreg.REG_DWORD, int(y))
        winreg.CloseKey(key)
        log(f"Позиция окна сохранена: ({x}, {y})", "DEBUG")
        return True
    except Exception as e:
        log(f"Ошибка сохранения позиции окна: {e}", "❌ ERROR")
        return False

def get_window_size():
    """Получает сохраненный размер окна из реестра"""
    try:
        import winreg
        from log import log

        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH, 0, winreg.KEY_READ)
        try:
            width = winreg.QueryValueEx(key, "WindowWidth")[0]
            height = winreg.QueryValueEx(key, "WindowHeight")[0]
            winreg.CloseKey(key)
            return (width, height)
        except FileNotFoundError:
            winreg.CloseKey(key)
            return None
    except Exception as e:
        log(f"Ошибка чтения размера окна: {e}", "DEBUG")
        return None

def set_window_size(width, height):
    """Сохраняет размер окна в реестр"""
    try:
        import winreg
        from log import log
        
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH)
        winreg.SetValueEx(key, "WindowWidth", 0, winreg.REG_DWORD, int(width))
        winreg.SetValueEx(key, "WindowHeight", 0, winreg.REG_DWORD, int(height))
        winreg.CloseKey(key)
        log(f"Размер окна сохранен: ({width}x{height})", "DEBUG")
        return True
    except Exception as e:
        log(f"Ошибка сохранения размера окна: {e}", "❌ ERROR")
        return False
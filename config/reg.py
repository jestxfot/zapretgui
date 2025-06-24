# reg.py ─ универсальный helper для работы с реестром
import winreg

HKCU = winreg.HKEY_CURRENT_USER
HKLM = winreg.HKEY_LOCAL_MACHINE
REGISTRY_KEY = r"SOFTWARE\Zapret"
from log import log

# Специальная константа для обозначения отсутствующего значения
class _UnsetType:
    """Sentinel object для обозначения 'не задано'"""
    def __repr__(self):
        return "<UNSET>"

_UNSET = _UnsetType()

# ───────────── Удаление Windows Terminal ─────────────
_WT_KEY  = r"Software\Zapret"
_WT_NAME = "RemoveWindowsTerminal"     # REG_DWORD (1/0)

def get_remove_windows_terminal() -> bool:
    """True – удалять Windows Terminal при запуске, False – не удалять."""
    val = reg(_WT_KEY, _WT_NAME)
    return bool(val) if val is not None else True   # дефолт = True (удалять)

def set_remove_windows_terminal(enabled: bool) -> bool:
    """Включает/выключает удаление Windows Terminal при запуске."""
    return reg(_WT_KEY, _WT_NAME, 1 if enabled else 0)

def _detect_reg_type(value):
    """Определяет подходящий winreg тип по питоновскому value."""
    if isinstance(value, str):
        return winreg.REG_SZ
    if isinstance(value, int):
        return winreg.REG_DWORD
    if isinstance(value, bytes):
        return winreg.REG_BINARY
    # fallback – строка
    return winreg.REG_SZ


def reg(subkey: str,
        name: str | None = None,
        value=_UNSET,
        *,
        root=HKCU):
    """
    Упрощённый доступ к реестру.

    Аргументы
    ---------
    subkey : str
        Путь относительно root, например 'Software\\Zapret'
    name : str | None
        Имя параметра.  Если None → работаем с default-value.
    value :  _UNSET  → чтение,
             None    → удаление параметра,
             любое другое → запись этого значения.
    root  : winreg.HKEY_*
        Hive (по-умолчанию HKCU).

    Возврат
    -------
    • при чтении – возвращает значение или None, если нет,
    • при записи / удалении – True/False (успех).
    """
    try:
        # --- чтение --------------------------------------------------
        if value is _UNSET:
            with winreg.OpenKey(root, subkey, 0, winreg.KEY_READ) as k:
                data, _ = winreg.QueryValueEx(k, name)
                return data

        # --- удаление -----------------------------------------------
        if value is None:
            # открываем с правом WRITE
            with winreg.OpenKey(root, subkey, 0, winreg.KEY_SET_VALUE) as k:
                winreg.DeleteValue(k, name or "")
            return True

        # --- запись --------------------------------------------------
        k = winreg.CreateKeyEx(root, subkey, 0, winreg.KEY_SET_VALUE)
        reg_type = _detect_reg_type(value)
        winreg.SetValueEx(k, name or "", 0, reg_type, value)
        winreg.CloseKey(k)
        return True

    except FileNotFoundError:
        return None if value is _UNSET else False
    except Exception as e:
        # при желании можете залогировать здесь
        # from log import log; log(f"reg error: {e}", "ERROR")
        return None if value is _UNSET else False


# ------------------------------------------------------------------
# Шорткаты вашей программы
# ------------------------------------------------------------------
def get_last_strategy():
    from config import DEFAULT_STRAT, REG_LATEST_STRATEGY
    return reg(r"Software\Zapret", REG_LATEST_STRATEGY) or DEFAULT_STRAT


def set_last_strategy(name: str) -> bool:
    from config import REG_LATEST_STRATEGY
    return reg(r"Software\Zapret", REG_LATEST_STRATEGY, name)

# ───────────── DPI-автозапуск ─────────────
_DPI_KEY   = r"Software\Zapret"
_DPI_NAME  = "DPIAutoStart"          # REG_DWORD (0/1)

def get_dpi_autostart() -> bool:
    """True – запускать DPI автоматически; False – не запускать."""
    val = reg(_DPI_KEY, _DPI_NAME)
    return bool(val) if val is not None else True  # Default to True if not set

def set_dpi_autostart(state: bool) -> bool:
    """Сохраняет флаг автозапуска DPI в реестре."""
    return reg(_DPI_KEY, _DPI_NAME, 1 if state else 0)

# ───────────── Автозагрузка стратегий ─────────────
_STRAT_KEY  = r"Software\Zapret"
_STRAT_NAME = "StrategyAutoLoad"        # REG_DWORD (1/0)

def get_strategy_autoload() -> bool:
    """True – разрешено скачивать стратегии с GitHub, False – запрещено."""
    val = reg(_STRAT_KEY, _STRAT_NAME)         # None → параметр отсутствует
    return bool(val) if val is not None else True   # дефолт = True

def set_strategy_autoload(enabled: bool) -> bool:
    """Включает/выключает автозагрузку стратегий."""
    return reg(_STRAT_KEY, _STRAT_NAME, 1 if enabled else 0)

def get_auto_download_enabled() -> bool:
    """Проверяет, включена ли автоматическая загрузка при старте"""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY) as key:
            value, _ = winreg.QueryValueEx(key, "AutoDownloadEnabled")
            return bool(value)
    except FileNotFoundError:
        return True  # По умолчанию включено
    except Exception as e:
        log(f"Ошибка чтения настройки автозагрузки: {e}", "ERROR")
        return True

def set_auto_download_enabled(enabled: bool):
    """Устанавливает состояние автоматической загрузки"""
    try:
        # Создаем ключ если его нет
        winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY)
        
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, "AutoDownloadEnabled", 0, winreg.REG_DWORD, int(enabled))
        log(f"Автозагрузка {'включена' if enabled else 'отключена'}", "INFO")
    except Exception as e:
        log(f"Ошибка записи настройки автозагрузки: {e}", "ERROR")


def get_subscription_check_interval() -> int:
    """Возвращает интервал проверки подписки в минутах (по умолчанию 10)"""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY) as key:
            value, _ = winreg.QueryValueEx(key, "SubscriptionCheckInterval")
            return max(1, int(value))  # Минимум 1 минута
    except FileNotFoundError:
        return 10  # По умолчанию 10 минут
    except Exception:
        return 10

def set_subscription_check_interval(minutes: int):
    """Устанавливает интервал проверки подписки в минутах"""
    try:
        winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY)
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, "SubscriptionCheckInterval", 0, winreg.REG_DWORD, int(minutes))
    except Exception as e:
        log(f"Ошибка записи интервала проверки подписки: {e}", "ERROR")
r"""
dpi/zapret2_settings_reset.py - Сброс настроек категории на значения по умолчанию

Настройки категории хранятся в реестре:
- Путь: HKEY_CURRENT_USER\Software\Zapret2Reg\CategorySyndata (или Zapret2DevReg)
- Ключ: category_key (например "youtube_https")
- Формат: JSON строка

Использование:
    from dpi.zapret2_settings_reset import (
        DEFAULT_CATEGORY_SETTINGS,
        get_default_category_settings,
        reset_category_settings,
        reset_all_categories_settings
    )

    # Получить дефолты
    defaults = get_default_category_settings()

    # Сбросить одну категорию
    reset_category_settings("youtube_https")

    # Сбросить все категории
    reset_all_categories_settings()
"""

from log import log


# ═══════════════════════════════════════════════════════════════════════════════
# ДЕФОЛТНЫЕ НАСТРОЙКИ КАТЕГОРИИ
# ═══════════════════════════════════════════════════════════════════════════════

DEFAULT_CATEGORY_SETTINGS = {
    # ═══════ SYNDATA параметры ═══════
    "enabled": True,
    "blob": "tls_google",
    "tls_mod": "none",
    "autottl_delta": -2,
    "autottl_min": 3,
    "autottl_max": 20,
    "tcp_flags_unset": "none",

    # ═══════ OUT RANGE параметры ═══════
    "out_range": 8,
    "out_range_mode": "n",  # "n" (packets count) or "d" (delay)

    # ═══════ SEND параметры ═══════
    "send_enabled": True,
    "send_repeats": 2,
    "send_ip_ttl": 0,
    "send_ip6_ttl": 0,
    "send_ip_id": "none",
    "send_badsum": False,
}


# ═══════════════════════════════════════════════════════════════════════════════
# API ФУНКЦИИ
# ═══════════════════════════════════════════════════════════════════════════════

def get_default_category_settings() -> dict:
    """
    Возвращает словарь с дефолтными настройками категории.

    Returns:
        dict: Копия DEFAULT_CATEGORY_SETTINGS
    """
    return DEFAULT_CATEGORY_SETTINGS.copy()


def reset_category_settings(category_key: str) -> bool:
    """
    Сбрасывает настройки категории на значения по умолчанию.

    Реализация через УДАЛЕНИЕ ключа из реестра, а не запись дефолтов.
    Это позволяет _load_syndata_settings() автоматически применить дефолты
    при следующей загрузке.

    Удаляет настройки из: CategorySyndata, CategoryFilterMode, CategorySort.

    Args:
        category_key: Ключ категории (например "youtube_https")

    Returns:
        True если успешно (включая случай когда ключ не существовал),
        False при ошибке
    """
    try:
        from config import REGISTRY_PATH
        import winreg

        keys_to_clear = [
            f"{REGISTRY_PATH}\\CategorySyndata",
            f"{REGISTRY_PATH}\\CategoryFilterMode",
            f"{REGISTRY_PATH}\\CategorySort",
        ]

        for key_path in keys_to_clear:
            try:
                with winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    key_path,
                    0,
                    winreg.KEY_SET_VALUE
                ) as key:
                    try:
                        winreg.DeleteValue(key, category_key)
                        log(f"Удален ключ {category_key} из {key_path}", "DEBUG")
                    except FileNotFoundError:
                        # Ключ не существует - это нормально
                        pass
            except FileNotFoundError:
                # Родительский ключ не существует - это тоже нормально
                pass

        log(f"Настройки категории {category_key} сброшены", "INFO")
        return True

    except Exception as e:
        log(f"Ошибка сброса настроек категории {category_key}: {e}", "ERROR")
        return False


def reset_all_categories_settings() -> bool:
    """
    Сбрасывает настройки ВСЕХ категорий.

    Удаляет целиком ключи реестра CategorySyndata, CategoryFilterMode, CategorySort.

    Returns:
        True если успешно, False при ошибке
    """
    try:
        from config import REGISTRY_PATH
        import winreg

        subkeys_to_delete = [
            "CategorySyndata",
            "CategoryFilterMode",
            "CategorySort",
        ]

        for subkey in subkeys_to_delete:
            try:
                key_path = f"{REGISTRY_PATH}\\{subkey}"
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key_path)
                log(f"Удален ключ реестра {key_path}", "DEBUG")
            except FileNotFoundError:
                # Ключ не существует - это нормально
                pass
            except Exception as e:
                log(f"Ошибка удаления ключа {subkey}: {e}", "WARNING")

        log("Все настройки категорий сброшены", "INFO")
        return True

    except Exception as e:
        log(f"Ошибка сброса всех настроек категорий: {e}", "ERROR")
        return False


# Алиас для обратной совместимости
reset_all_category_settings = reset_all_categories_settings

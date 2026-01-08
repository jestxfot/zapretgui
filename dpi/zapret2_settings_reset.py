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

    Использует PresetManager для сброса настроек в активном пресете.
    Это автоматически:
    - Сбрасывает syndata на дефолты
    - Устанавливает filter_mode = "hostlist"
    - Устанавливает sort_order = "default"
    - Сохраняет preset файл
    - Вызывает DPI reload через callback

    Args:
        category_key: Ключ категории (например "youtube")

    Returns:
        True если успешно, False при ошибке
    """
    try:
        from preset_zapret2 import PresetManager

        manager = PresetManager()
        success = manager.reset_category_settings(category_key)

        if success:
            log(f"Настройки категории {category_key} сброшены через PresetManager", "INFO")
        else:
            log(f"Не удалось сбросить настройки категории {category_key}", "WARNING")

        return success

    except Exception as e:
        log(f"Ошибка сброса настроек категории {category_key}: {e}", "ERROR")
        import traceback
        log(traceback.format_exc(), "DEBUG")
        return False


def reset_all_categories_settings() -> bool:
    """
    Сбрасывает настройки ВСЕХ категорий.

    Получает список категорий из активного пресета и сбрасывает каждую.

    Returns:
        True если все категории успешно сброшены, False при ошибке
    """
    try:
        from preset_zapret2 import PresetManager

        manager = PresetManager()
        preset = manager.get_active_preset()

        if not preset:
            log("Нет активного пресета для сброса категорий", "WARNING")
            return False

        if not preset.categories:
            log("Нет категорий в активном пресете", "INFO")
            return True

        # Сбрасываем каждую категорию
        all_success = True
        reset_count = 0

        for category_key in list(preset.categories.keys()):
            success = manager.reset_category_settings(category_key)
            if success:
                reset_count += 1
            else:
                all_success = False
                log(f"Ошибка сброса категории {category_key}", "WARNING")

        log(f"Сброшено {reset_count} из {len(preset.categories)} категорий", "INFO")
        return all_success

    except Exception as e:
        log(f"Ошибка сброса всех настроек категорий: {e}", "ERROR")
        import traceback
        log(traceback.format_exc(), "DEBUG")
        return False


# Алиас для обратной совместимости
reset_all_category_settings = reset_all_categories_settings

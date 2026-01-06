# strategy_menu/preset_configuration_zapret2/preset_regenerator.py
"""
Preset Regenerator - генерация файла preset-zapret2.txt

Отвечает за создание и обновление конфигурационного файла для winws2.

Использование:
    from strategy_menu.preset_configuration_zapret2 import preset_regenerator

    # Перегенерировать preset с текущими настройками
    preset_regenerator.regenerate()

    # Получить путь к файлу
    path = preset_regenerator.get_preset_path()
"""

import os
from datetime import datetime
from typing import Optional
from log import log


def get_preset_path() -> str:
    """Возвращает путь к файлу preset-zapret2.txt"""
    from config import PROGRAMDATA_PATH
    return os.path.join(PROGRAMDATA_PATH, "preset-zapret2.txt")


def regenerate() -> bool:
    """
    Перегенерирует preset-zapret2.txt с текущими настройками.

    Читает выбранные стратегии из реестра, комбинирует их
    и записывает результат в preset файл.

    Returns:
        True если успешно, False при ошибке
    """
    try:
        # Получаем текущие выборы из реестра
        from . import strategy_selections
        selections = strategy_selections.get_all()

        # Проверяем есть ли активные стратегии
        has_active = any(v and v != "none" for v in selections.values())
        if not has_active:
            log("Нет активных стратегий для генерации preset", "DEBUG")
            return False

        # Генерируем аргументы через build_full_command
        from .command_builder import build_full_command
        combined = build_full_command(selections)
        args_str = combined.get('args', '')

        if not args_str:
            log("Пустые аргументы после combine_strategies", "WARNING")
            return False

        # Записываем в файл
        preset_path = get_preset_path()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with open(preset_path, 'w', encoding='utf-8') as f:
            f.write(f"# Strategy: Прямой запуск (Запрет 2)\n")
            f.write(f"# Generated: {timestamp}\n")

            # Разбиваем args_str на строки
            for line in args_str.split('\n'):
                line = line.strip()
                if line:
                    f.write(f"{line}\n")

        log(f"Preset файл перегенерирован: {preset_path}", "INFO")
        return True

    except Exception as e:
        log(f"Ошибка перегенерации preset файла: {e}", "ERROR")
        import traceback
        log(traceback.format_exc(), "DEBUG")
        return False


def write_preset(args_str: str, strategy_name: str = "Custom") -> bool:
    """
    Записывает готовую строку аргументов в preset файл.

    Args:
        args_str: Строка аргументов для winws2
        strategy_name: Название стратегии для комментария

    Returns:
        True если успешно
    """
    try:
        preset_path = get_preset_path()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with open(preset_path, 'w', encoding='utf-8') as f:
            f.write(f"# Strategy: {strategy_name}\n")
            f.write(f"# Generated: {timestamp}\n")

            for line in args_str.split('\n'):
                line = line.strip()
                if line:
                    f.write(f"{line}\n")

        log(f"Preset файл записан: {preset_path}", "DEBUG")
        return True

    except Exception as e:
        log(f"Ошибка записи preset файла: {e}", "ERROR")
        return False


def read_preset() -> Optional[str]:
    """
    Читает содержимое preset файла.

    Returns:
        Содержимое файла или None при ошибке
    """
    try:
        preset_path = get_preset_path()
        if os.path.exists(preset_path):
            with open(preset_path, 'r', encoding='utf-8') as f:
                return f.read()
        return None
    except Exception as e:
        log(f"Ошибка чтения preset файла: {e}", "ERROR")
        return None


def exists() -> bool:
    """Проверяет существует ли preset файл"""
    return os.path.exists(get_preset_path())


__all__ = [
    'regenerate',
    'write_preset',
    'read_preset',
    'get_preset_path',
    'exists',
]

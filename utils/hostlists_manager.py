# utils/hostlists_manager.py
"""
Менеджер hostlist-файлов.

- other.txt: рабочий файл пользователя (в пространстве приложения)
- %APPDATA%/zapret/lists_template/other.txt: системный шаблон
"""

from __future__ import annotations

import os
import sys

from log import log
from config import MAIN_DIRECTORY, OTHER_PATH, get_other_template_path


def _fallback_base_domains() -> list[str]:
    return ["youtube.com", "googlevideo.com", "discord.com", "discord.gg"]


def _normalize_newlines(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    if normalized and not normalized.endswith("\n"):
        normalized += "\n"
    return normalized


def _read_text_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _read_effective_domains(path: str) -> list[str]:
    """Читает домены без комментариев/пустых строк."""
    if not os.path.exists(path):
        return []

    result: list[str] = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip().lower()
                if not line or line.startswith("#"):
                    continue
                result.append(line)
    except Exception:
        return []
    return result


def _candidate_source_paths() -> list[str]:
    """Кандидаты для source other.txt (без hardcode абсолютных путей)."""
    candidates: list[str] = []

    # dev-сценарий: соседний проект zapret (например H:\Privacy\zapret\lists\other.txt)
    sibling_source = os.path.join(os.path.dirname(MAIN_DIRECTORY), "zapret", "lists", "other.txt")
    candidates.append(sibling_source)

    # локальный dev-сценарий: <repo>/lists/other.txt
    if not bool(getattr(sys, "frozen", False)):
        candidates.append(os.path.join(MAIN_DIRECTORY, "lists", "other.txt"))

    # уникализируем, сохраняя порядок
    unique: list[str] = []
    for path in candidates:
        if path not in unique:
            unique.append(path)
    return unique


def _find_valid_source_path() -> str | None:
    for path in _candidate_source_paths():
        if _read_effective_domains(path):
            return path
    return None


def get_base_domains() -> list[str]:
    """Возвращает системные базовые домены для other.txt."""
    # Источник №1: системный шаблон
    template_domains = _read_effective_domains(get_other_template_path())
    if template_domains:
        return template_domains

    # Источник №2: source-файл (dev/build)
    source_path = _find_valid_source_path()
    if source_path:
        source_domains = _read_effective_domains(source_path)
        if source_domains:
            return source_domains

    # Аварийный минимум
    log("WARNING: Не найден валидный source other.txt, использую аварийный минимум", "WARNING")
    return _fallback_base_domains()


def get_base_domains_set() -> set[str]:
    """Возвращает set базовых доменов (lowercase)."""
    return {d.strip().lower() for d in get_base_domains() if d and d.strip()}


def build_other_template_content() -> str:
    """Формирует содержимое системного шаблона other.txt."""
    source_path = _find_valid_source_path()
    if source_path:
        try:
            return _normalize_newlines(_read_text_file(source_path))
        except Exception:
            pass

    template_path = get_other_template_path()
    if os.path.exists(template_path):
        try:
            content = _read_text_file(template_path)
            if _read_effective_domains(template_path):
                return _normalize_newlines(content)
        except Exception:
            pass

    domains = sorted(set(_fallback_base_domains()))
    return "\n".join(domains) + "\n"


def _write_text_file(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(_normalize_newlines(content))


def _count_effective_domains(path: str) -> int:
    return len(_read_effective_domains(path))


def ensure_other_template_updated() -> bool:
    """Гарантирует валидный системный шаблон other.txt в lists_template."""
    try:
        template_path = get_other_template_path()
        source_path = _find_valid_source_path()

        if source_path:
            source_content = _normalize_newlines(_read_text_file(source_path))
            current_content = ""
            if os.path.exists(template_path):
                current_content = _normalize_newlines(_read_text_file(template_path))

            if source_content != current_content:
                _write_text_file(template_path, source_content)
                log(f"Обновлен шаблон other.txt из source: {source_path}", "DEBUG")
            return True

        if _count_effective_domains(template_path) > 0:
            return True

        # Если source-файл недоступен, создаём аварийный минимум.
        fallback_content = "\n".join(sorted(set(_fallback_base_domains()))) + "\n"
        _write_text_file(template_path, fallback_content)
        log("Создан аварийный шаблон other.txt (source не найден)", "WARNING")
        return True
    except Exception as e:
        log(f"Ошибка обновления шаблона other.txt: {e}", "ERROR")
        return False


def reset_other_file_from_template() -> bool:
    """Сбрасывает рабочий lists/other.txt из системного шаблона."""
    try:
        if not ensure_other_template_updated():
            return False

        template_path = get_other_template_path()
        content = _read_text_file(template_path)

        _write_text_file(OTHER_PATH, content)
        log("other.txt сброшен из шаблона", "SUCCESS")
        return True
    except Exception as e:
        log(f"Ошибка сброса other.txt из шаблона: {e}", "ERROR")
        return False


def ensure_hostlists_exist() -> bool:
    """Проверяет hostlist-файлы и создаёт other.txt при необходимости."""
    try:
        os.makedirs(os.path.dirname(OTHER_PATH), exist_ok=True)

        if not ensure_other_template_updated():
            return False

        if not os.path.exists(OTHER_PATH):
            log("Создание other.txt из шаблона...", "INFO")
            return reset_other_file_from_template()

        if _count_effective_domains(OTHER_PATH) == 0:
            log("other.txt не содержит доменов, пересоздаем из шаблона", "WARNING")
            return reset_other_file_from_template()

        return True
    except Exception as e:
        log(f"Ошибка создания файлов хостлистов: {e}", "ERROR")
        return False


def startup_hostlists_check() -> bool:
    """Проверка hostlist-файлов при запуске программы."""
    try:
        log("=== Проверка хостлистов при запуске ===", "HOSTLISTS")

        os.makedirs(os.path.dirname(OTHER_PATH), exist_ok=True)

        if not ensure_other_template_updated():
            return False

        if not os.path.exists(OTHER_PATH):
            log("Создаем other.txt из шаблона", "WARNING")
            if not reset_other_file_from_template():
                return False
        else:
            lines_count = _count_effective_domains(OTHER_PATH)

            if lines_count == 0:
                log("other.txt пуст, пересоздаем из шаблона", "WARNING")
                if not reset_other_file_from_template():
                    return False
            else:
                log(f"other.txt: {lines_count} доменов", "INFO")

        return True
    except Exception as e:
        log(f"Ошибка при проверке хостлистов: {e}", "ERROR")
        return False

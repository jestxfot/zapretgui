import os
import re
from typing import List, Tuple
from log import log
from config import NETROGAT_PATH, LISTS_FOLDER

# Базовые домены исключений (добавляются только при создании файла
# или вручную через кнопку "Добавить отсутствующие")
DEFAULT_NETROGAT_DOMAINS = [
    # Государственные
    "gosuslugi.ru",
    "government.ru",
    "mos.ru",
    "nalog.ru",
    # VK / Mail.ru
    "vk.com",
    "vk.ru",
    "vkvideo.ru",
    "vk-portal.net",
    "userapi.com",
    "mail.ru",
    "max.ru",
    "ok.ru",
    "okcdn.ru",
    "mycdn.me",
    "api.mycdn.me",
    "tns-counter.ru",
    "vc.ru",
    "osnova.io",
    # Яндекс
    "ya.ru",
    "yandex.net",
    "yandex.ru",
    "yandex.by",
    "yandex.kz",
    "dzen.ru",
    "rutube.ru",
    # Банки
    "sberbank.ru",
    "sberbank.com",
    "sbrf.ru",
    "sbercloud.ru",
    "vtb.ru",
    "tbank.ru",
    "tinkoff.ru",
    "cdn-tinkoff.ru",
    "t-j.ru",
    "t-static.ru",
    "tinkoffjournal.ru",
    "tjournal.tech",
    "alfabank.ru",
    # Операторы связи
    "megafon.ru",
    "mts.ru",
    # Антивирусы и безопасность
    "kaspersky.com",
    "kaspersky.ru",
    "drweb.ru",
    "drweb.com",
    # Маркетплейсы
    "ozon.ru",
    "ozone.ru",
    "ozonusercontent.com",
    "wildberries.ru",
    "wb.ru",
    "wbbasket.ru",
    # Сервисы
    "deepl.com",
    "ixbt.com",
    "gitflic.ru",
    "searchengines.guru",
    "habr.com",
    "apteka.ru",
    "comss.ru",
    "teletype.in",
    "avtoradio.ru",
    "lifehacker.ru",
    "zapretdpi.ru",
    "beget.com",
    "boosty.to",
    "rzd.ru",
    "tvil.ru",
    "tutu.ru",
    "dp.ru",
    "rustore.ru",
    # СМИ
    "smi2.ru",
    "smi2.net",
    "smi24.net",
    "24smi.net",
    # Техно
    "yadro.ru",
    "createjs.com",
    "cdn.ampproject.org",
    "st.top100.ru",
    "use.fontawesome.com",
    # Punycode домены
    "xn----7sba3awldles.xn--p1ai",
    "xn--80aamekfkttt8n.xn--p1ai",
    "xn--80aneaalhfjfdkj7ah7o.xn--p1ai",
    # Растения (?)
    "rootsplants.co.uk",
    "podviliepitomnik.ru",
    "cvetovod.by",
    "veresk.by",
    # Microsoft
    "microsoft.com",
    "live.com",
    "office.com",
    # Локальные адреса
    "localhost",
    "127.0.0.1",
    # Образование
    "netschool.edu22.info",
    "edu22.info",
    # Конструкторы сайтов
    "tilda.ws",
    "tilda.cc",
    "tildacdn.com",
    # AI сервисы
    "claude.ai",
    "anthropic.com",
    "claude.com",
    "lmarena.ai",
    "ppl-ai-file-upload.s3.amazonaws.com",
]


def _normalize_domain(text: str) -> str | None:
    """Приводит строку к домену, убирает схемы/путь/порт, нижний регистр."""
    s = text.strip()
    if not s or s.startswith("#"):
        return None
    # убираем точку в начале (.com -> com)
    if s.startswith("."):
        s = s[1:]
    # убираем протокол
    if "://" in s:
        s = s.split("://", 1)[1]
    # убираем путь
    s = s.split("/", 1)[0]
    # убираем порт
    s = s.split(":", 1)[0]
    # убираем www.
    if s.startswith("www."):
        s = s[4:]
    # ещё раз точку в начале (на случай если была в URL)
    if s.startswith("."):
        s = s[1:]
    s = s.strip().lower()
    if not s:
        return None
    # Одиночные TLD (com, ru, org) - валидны
    if re.match(r"^[a-z]{2,10}$", s):
        return s
    # Домен с точкой
    if "." in s and re.match(r"^[a-z0-9][a-z0-9\-\.\*]*[a-z0-9]$", s):
        return s
    return None


_NETROGAT_HEADER = """\
# Список доменов-ИСКЛЮЧЕНИЙ (не трогать / не проксировать).
# ВАЖНО: этот файл передаётся winws как --hostlist-exclude.
# Домены из этого списка НЕ обрабатываются запретом — трафик идёт напрямую.
# Здесь должны быть системные, государственные и другие «свои» домены,
# которые ни в коем случае не нужно проксировать/подменять.
# Если файл пустой или отсутствует — winws применит обход ко ВСЕМ сайтам,
# что сломает доступ к банкам, госуслугам, ВКонтакте и т.п.
#
# Формат: один домен на строку, без протокола и пути (например: vk.com).
# Строки, начинающиеся с #, игнорируются.
"""


def ensure_netrogat_exists() -> bool:
    """Создает netrogat.txt если его нет, заполняя дефолтными доменами."""
    try:
        os.makedirs(os.path.dirname(NETROGAT_PATH), exist_ok=True)
        if not os.path.exists(NETROGAT_PATH):
            with open(NETROGAT_PATH, "w", encoding="utf-8") as f:
                f.write(_NETROGAT_HEADER)
                for d in DEFAULT_NETROGAT_DOMAINS:
                    f.write(f"{d}\n")
            log(f"Создан netrogat.txt с {len(DEFAULT_NETROGAT_DOMAINS)} доменами", "INFO")
        return True
    except Exception as e:
        log(f"Ошибка создания netrogat.txt: {e}", "ERROR")
        return False


def load_netrogat() -> List[str]:
    """Загружает домены из netrogat.txt (без комментариев), нормализует и уникализирует."""
    ensure_netrogat_exists()
    domains: list[str] = []
    try:
        with open(NETROGAT_PATH, "r", encoding="utf-8") as f:
            for line in f:
                norm = _normalize_domain(line)
                if norm and norm not in domains:
                    domains.append(norm)
    except Exception as e:
        log(f"Ошибка чтения netrogat.txt: {e}", "ERROR")
    return domains


def save_netrogat(domains: List[str]) -> bool:
    """Сохраняет список доменов в netrogat.txt (отсортированный, уникальный)."""
    try:
        os.makedirs(os.path.dirname(NETROGAT_PATH), exist_ok=True)
        uniq = []
        seen = set()
        for d in domains:
            if d not in seen:
                seen.add(d)
                uniq.append(d)
        with open(NETROGAT_PATH, "w", encoding="utf-8") as f:
            for d in sorted(uniq):
                f.write(f"{d}\n")
        log(f"Сохранено {len(uniq)} доменов в netrogat.txt", "INFO")
        return True
    except Exception as e:
        log(f"Ошибка сохранения netrogat.txt: {e}", "ERROR")
        return False


def add_missing_defaults(current: List[str]) -> Tuple[List[str], int]:
    """Добавляет отсутствующие дефолтные домены к текущему списку, возвращает (новый_список, добавлено)."""
    current_set = set(current)
    added = 0
    for d in DEFAULT_NETROGAT_DOMAINS:
        if d not in current_set:
            current_set.add(d)
            added += 1
    return sorted(current_set), added


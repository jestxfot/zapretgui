# strategy_menu/strategies/blobs.py

"""
Определения блобов для стратегий Zapret 2.
Блобы загружаются один раз и могут использоваться в нескольких стратегиях.

Подход:
1. Все блобы определены в словаре BLOBS (имя -> путь/hex)
2. При сборке командной строки функция extract_and_dedupe_blobs() 
   извлекает --blob=... из args, дедуплицирует их, и возвращает 
   уникальные блобы отдельно от остальных аргументов
"""

import re
import os

# Кэш для блобов - заполняется при первом вызове get_blobs()
_BLOBS_CACHE = None


def get_blobs() -> dict:
    """
    Возвращает словарь блобов с правильными путями.
    Ленивая инициализация - пути вычисляются при первом вызове.
    """
    global _BLOBS_CACHE
    if _BLOBS_CACHE is not None:
        return _BLOBS_CACHE
    
    from config import BIN_FOLDER
    
    def _bin(filename: str) -> str:
        """Создаёт путь к файлу в BIN_FOLDER с префиксом @"""
        path = os.path.join(BIN_FOLDER, filename)
        return f"@{path}"
    
    _BLOBS_CACHE = {
        # ============== TLS ClientHello ==============
        "tls_google": _bin("tls_clienthello_www_google_com.bin"),
        "tls1": _bin("tls_clienthello_1.bin"),
        "tls2": _bin("tls_clienthello_2.bin"),
        "tls2n": _bin("tls_clienthello_2n.bin"),
        "tls3": _bin("tls_clienthello_3.bin"),
        "tls4": _bin("tls_clienthello_4.bin"),
        "tls5": _bin("tls_clienthello_5.bin"),
        "tls6": _bin("tls_clienthello_6.bin"),
        "tls7": _bin("tls_clienthello_7.bin"),
        "tls8": _bin("tls_clienthello_8.bin"),
        "tls9": _bin("tls_clienthello_9.bin"),
        "tls10": _bin("tls_clienthello_10.bin"),
        "tls11": _bin("tls_clienthello_11.bin"),
        "tls12": _bin("tls_clienthello_12.bin"),
        "tls13": _bin("tls_clienthello_13.bin"),
        "tls14": _bin("tls_clienthello_14.bin"),
        "tls17": _bin("tls_clienthello_17.bin"),
        "tls18": _bin("tls_clienthello_18.bin"),
        
        # ============== TLS ClientHello (специальные) ==============
        "tls_sber": _bin("tls_clienthello_sberbank_ru.bin"),
        "tls_vk": _bin("tls_clienthello_vk_com.bin"),
        "tls_vk_kyber": _bin("tls_clienthello_vk_com_kyber.bin"),
        "tls_deepseek": _bin("tls_clienthello_chat_deepseek_com.bin"),
        "dtls_w3": _bin("dtls_clienthello_w3_org.bin"),
        
        # ============== Syndata ==============
        "syndata3": _bin("tls_clienthello_3.bin"),
        "syn_packet": _bin("syn_packet.bin"),
        
        # ============== QUIC Initial ==============
        "quic_google": _bin("quic_initial_www_google_com.bin"),
        "quic_vk": _bin("quic_initial_vk_com.bin"),
        "quic1": _bin("quic_1.bin"),
        "quic2": _bin("quic_2.bin"),
        "quic3": _bin("quic_3.bin"),
        "quic4": _bin("quic_4.bin"),
        "quic5": _bin("quic_5.bin"),
        "quic6": _bin("quic_6.bin"),
        "quic7": _bin("quic_7.bin"),
        "quic_test": _bin("quic_test_00.bin"),
        "fake_quic": _bin("fake_quic.bin"),
        
        # ============== HTTP ==============
        "http_req": _bin("http_req.bin"),
        
        # ============== Default Fakes (fallback) ==============
        # Если встроенные блобы в winws2.exe недоступны, используем hex-заглушки
        "fake_default_udp": "0x00000000000000000000000000000000",  # 16 нулей для UDP
        
        # ============== Hex patterns (inline) ==============
        # Эти блобы задаются как hex-строки, а не файлы
        "hex_0e0e0f0e": "0x0E0E0F0E",
        "hex_0f0e0e0f": "0x0F0E0E0F",
        "hex_0f0f0f0f": "0x0F0F0F0F",
        "hex_00": "0x00",
    }
    
    return _BLOBS_CACHE


# Для обратной совместимости - будет заполнен при первом использовании
# Используйте get_blobs() для гарантированно правильных путей
BLOBS = {}

# Регулярка для поиска --blob=name:value в строке аргументов
BLOB_PATTERN = re.compile(r'--blob=([^:\s]+):([^\s]+)')

# Паттерны для поиска использования блобов в lua-desync аргументах
# :blob=name, seqovl_pattern=name, pattern=name, fakedsplit_pattern=name
BLOB_USAGE_PATTERNS = [
    re.compile(r':blob=([a-zA-Z0-9_]+)'),           # :blob=tls5
    re.compile(r'seqovl_pattern=([a-zA-Z0-9_]+)'),  # seqovl_pattern=tls_google
    re.compile(r'pattern=([a-zA-Z0-9_]+)'),         # pattern=tls7 (но не pattern=0x...)
    re.compile(r'fakedsplit_pattern=([a-zA-Z0-9_]+)'),  # fakedsplit_pattern=tls4
]


def find_used_blobs(args: str) -> set:
    """
    Находит все блобы, используемые в строке аргументов.
    Ищет :blob=name, seqovl_pattern=name, pattern=name и т.д.
    
    Returns:
        Множество имён используемых блобов
    """
    blobs = get_blobs()
    used = set()
    for pattern in BLOB_USAGE_PATTERNS:
        for match in pattern.finditer(args):
            blob_name = match.group(1)
            # Пропускаем hex-значения (0x...) - они не являются именами блобов
            if not blob_name.startswith('0x') and blob_name in blobs:
                used.add(blob_name)
    return used


def generate_blob_definitions(blob_names: set) -> str:
    """
    Генерирует строку с --blob=name:value для всех указанных блобов.
    """
    blobs = get_blobs()
    definitions = []
    for name in sorted(blob_names):  # Сортируем для стабильного порядка
        if name in blobs:
            definitions.append(f"--blob={name}:{blobs[name]}")
    return " ".join(definitions)


def extract_and_dedupe_blobs(args_list: list[str]) -> tuple[str, str]:
    """
    Извлекает все --blob=... из списка строк аргументов,
    дедуплицирует их, и возвращает отдельно.
    
    Args:
        args_list: Список строк с аргументами (от разных стратегий)
        
    Returns:
        Кортеж (blobs_str, remaining_args_str):
        - blobs_str: Уникальные --blob=... объединённые в строку
        - remaining_args_str: Остальные аргументы без --blob=...
    """
    seen_blobs = {}  # name -> full_definition
    remaining_parts = []
    
    for args in args_list:
        if not args:
            continue
            
        # Находим все блобы в этой строке
        for match in BLOB_PATTERN.finditer(args):
            blob_name = match.group(1)
            blob_value = match.group(2)
            full_def = f"--blob={blob_name}:{blob_value}"
            
            # Сохраняем только первое определение каждого блоба
            if blob_name not in seen_blobs:
                seen_blobs[blob_name] = full_def
        
        # Убираем блобы из строки аргументов
        cleaned = BLOB_PATTERN.sub('', args).strip()
        # Убираем множественные пробелы
        cleaned = ' '.join(cleaned.split())
        if cleaned:
            remaining_parts.append(cleaned)
    
    blobs_str = ' '.join(seen_blobs.values())
    remaining_str = ' '.join(remaining_parts)
    
    return blobs_str, remaining_str


def build_args_with_deduped_blobs(args_list: list[str]) -> str:
    """
    Собирает финальную командную строку с дедуплицированными блобами.
    
    1. Извлекает явные --blob=name:value из аргументов
    2. Находит все используемые блобы (:blob=name, seqovl_pattern=name, etc.)
    3. Автоматически добавляет --blob=name:@path для каждого используемого блоба (кроме уже определённых)
    4. Блобы выносятся в начало командной строки
    
    Args:
        args_list: Список строк с аргументами (от разных стратегий/профилей)
        
    Returns:
        Финальная командная строка с блобами в начале
    """
    # Извлекаем явно заданные блобы и получаем их имена
    seen_blob_names = set()
    for args in args_list:
        if args:
            for match in BLOB_PATTERN.finditer(args):
                seen_blob_names.add(match.group(1))
    
    # Извлекаем явно заданные блобы
    explicit_blobs_str, remaining_str = extract_and_dedupe_blobs(args_list)
    
    # Находим все используемые блобы в оставшихся аргументах
    all_used_blobs = set()
    for args in args_list:
        if args:
            all_used_blobs.update(find_used_blobs(args))
    
    # Исключаем блобы которые уже явно определены
    blobs_to_auto_generate = all_used_blobs - seen_blob_names
    
    # Генерируем определения только для недостающих блобов
    auto_blobs_str = generate_blob_definitions(blobs_to_auto_generate)
    
    # Объединяем: явные блобы + автоматические блобы + остальные аргументы
    parts = []
    if explicit_blobs_str:
        parts.append(explicit_blobs_str)
    if auto_blobs_str:
        parts.append(auto_blobs_str)
    if remaining_str:
        parts.append(remaining_str)
    
    return " ".join(parts)


def get_blob_definition(blob_name: str) -> str:
    """
    Возвращает строку определения блоба для командной строки.
    
    Args:
        blob_name: Имя блоба из словаря BLOBS
        
    Returns:
        Строка вида "--blob=name:@path" или "--blob=name:0xHEX"
    """
    blobs = get_blobs()
    if blob_name not in blobs:
        raise ValueError(f"Unknown blob: {blob_name}")
    return f"--blob={blob_name}:{blobs[blob_name]}"


def get_blobs_args(blob_names: list[str]) -> str:
    """
    Возвращает строку с определениями всех указанных блобов.
    Дубликаты автоматически удаляются.
    
    Args:
        blob_names: Список имён блобов
        
    Returns:
        Строка с --blob=... для каждого уникального блоба
    """
    unique_blobs = list(dict.fromkeys(blob_names))  # Сохраняем порядок, убираем дубли
    return " ".join(get_blob_definition(name) for name in unique_blobs)


def collect_blobs_from_strategies(strategies: list[dict]) -> list[str]:
    """
    Собирает все уникальные блобы из списка стратегий.
    
    Args:
        strategies: Список словарей стратегий с полем 'blobs'
        
    Returns:
        Список уникальных имён блобов
    """
    all_blobs = []
    for strategy in strategies:
        if "blobs" in strategy:
            all_blobs.extend(strategy["blobs"])
    # Убираем дубликаты, сохраняя порядок
    return list(dict.fromkeys(all_blobs))


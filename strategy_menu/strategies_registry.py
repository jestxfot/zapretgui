"""
Централизованный реестр всех стратегий и категорий.
Управляет импортом, метаданными и предоставляет единый интерфейс.

Стратегии загружаются из JSON файлов:
- {INDEXJSON_FOLDER}/strategies/builtin/*.json - встроенные стратегии
- {INDEXJSON_FOLDER}/strategies/user/*.json - пользовательские стратегии
"""

from typing import Dict, Tuple, List, Optional, Any
from dataclasses import dataclass
from log import log

# ==================== LAZY IMPORTS ====================

_strategies_cache = {}  # {strategy_type: strategies_dict} - кешируем по типу стратегий
_imported_types = set()  # Какие типы уже загружены
_logged_missing_strategies = set()  # Чтобы не спамить логи одними и теми же предупреждениями

# ==================== КОНСТАНТЫ ФИЛЬТРОВ ====================

# Discord Voice фильтр (используется в base_filter)
DISCORD_VOICE_FILTER = "--filter-l7=discord,stun"


def _load_strategies_from_json(strategy_type: str) -> Dict:
    """
    Загружает стратегии из JSON файлов.
    Сначала builtin, потом user (user перезаписывает builtin).
    """
    try:
        from .strategies.strategy_loader import load_strategies_as_dict
        strategies = load_strategies_as_dict(strategy_type)
        if strategies:
            log(f"Загружено {len(strategies)} стратегий типа '{strategy_type}' из JSON", "DEBUG")
            return strategies
    except Exception as e:
        log(f"Ошибка загрузки JSON стратегий типа '{strategy_type}': {e}", "WARNING")
    
    return {}


def _strip_payload_from_args(args: str) -> str:
    """
    Удаляет --payload=... из аргументов стратегии.
    
    Используется для IPset категорий без фильтра портов,
    чтобы стратегия применялась ко ВСЕМУ трафику, а не только к TLS/HTTP.
    
    Args:
        args: Строка аргументов стратегии
        
    Returns:
        Строка аргументов без --payload=
    """
    import re
    
    # Убираем --payload=... (например: --payload=tls_client_hello или --payload=http_req)
    result = re.sub(r'--payload=[^\s]+\s*', '', args)
    
    # Также убираем --filter-l7=... если есть (это фильтр по типу трафика)
    result = re.sub(r'--filter-l7=[^\s]+\s*', '', result)
    
    # Очищаем множественные пробелы
    result = ' '.join(result.split())
    
    if result != args:
        log(f"Удалены payload фильтры из аргументов (strip_payload=True)", "DEBUG")
    
    return result


def _lazy_import_base_strategies(strategy_type: str) -> Dict:
    """
    Ленивый импорт базовых стратегий по типу из JSON файлов.
    """
    global _strategies_cache, _imported_types
    
    if strategy_type in _imported_types:
        return _strategies_cache.get(strategy_type, {})
    
    strategies = _load_strategies_from_json(strategy_type)
    
    if strategies:
        _strategies_cache[strategy_type] = strategies
        _imported_types.add(strategy_type)
        return strategies
    
    log(f"Не удалось загрузить стратегии типа '{strategy_type}'", "WARNING")
    _imported_types.add(strategy_type)
    return {}

def _get_strategies_for_category(category_key: str) -> Dict:
    """
    Получить стратегии для категории на основе её strategy_type.
    Используется для UI и отображения списка стратегий.
    """
    # Нужно получить strategy_type из CATEGORIES_REGISTRY
    category_info = CATEGORIES_REGISTRY.get(category_key)
    if not category_info:
        log(f"Категория {category_key} не найдена", "⚠ WARNING")
        return {}
    
    return _lazy_import_base_strategies(category_info.strategy_type)


def _lazy_import_all_strategies() -> Dict[str, Dict]:
    """Импортирует ВСЕ базовые стратегии (только если очень нужно)"""
    # Загружаем все типы
    for strategy_type in ["tcp", "udp", "http80", "discord_voice"]:
        _lazy_import_base_strategies(strategy_type)
    
    return _strategies_cache

# ==================== МЕТАДАННЫЕ КАТЕГОРИЙ ====================
@dataclass
class CategoryInfo:
    """Информация о категории стратегий"""
    key: str
    short_name: str
    full_name: str
    emoji: str
    description: str
    tooltip: str
    color: str
    default_strategy: str
    ports: str
    protocol: str
    order: int
    command_order: int
    needs_new_separator: bool = False
    command_group: str = "default"
    icon_name: str = 'fa5s.globe'
    icon_color: str = '#2196F3'
    
    # Фильтр для категории (hostlist, ipset, filter-tcp/udp)
    base_filter: str = ""
    # Тип базовых стратегий: "tcp", "udp", "http80", "discord_voice"
    strategy_type: str = "tcp"
    # Требует ли категория агрессивного режима (все порты)
    # True = скрывается в аккуратных режимах
    requires_all_ports: bool = False
    # Убирать --payload из стратегий (для IPset категорий без фильтра портов)
    # Если True - стратегия применяется ко ВСЕМУ трафику, не только к TLS
    strip_payload: bool = False

# Обновляем реестр категорий с новыми полями:
CATEGORIES_REGISTRY: Dict[str, CategoryInfo] = {
    'youtube': CategoryInfo(
        key='youtube',
        short_name='🎬',
        full_name='YouTube TCP',
        emoji='🎬',
        description='YouTube через TCP протокол (порты 80, 443)',
        tooltip="""🎬 YouTube через TCP протокол (порты 80, 443)
Обходит блокировку обычного YouTube трафика через стандартные веб-порты.
TCP - это надежный протокол передачи данных, используется для загрузки веб-страниц и видео.
Работает с youtube.com и youtu.be.""",
        color='#ff6666',
        default_strategy='multisplit_seqovl_midsld',
        ports='80, 443',
        protocol='TCP',
        order=1,

        command_order=2,
        needs_new_separator=True,
        command_group="youtube",
        icon_name='fa5b.youtube',
        icon_color='#FF0000',
        base_filter="--filter-tcp=80,443 --hostlist=youtube.txt",
        strategy_type="tcp"
    ),
    
    'youtube_udp': CategoryInfo(
        key='youtube_udp',
        short_name='📺',
        full_name='YouTube QUIC',
        emoji='📺',
        description='YouTube через QUIC/UDP протокол (порт 443)',
        tooltip="""🎬 YouTube через QUIC/UDP протокол (порт 443)
Обходит блокировку YouTube при использовании современного протокола QUIC (HTTP/3).
QUIC работает поверх UDP и обеспечивает более быструю загрузку видео.
Многие браузеры автоматически используют QUIC для YouTube.""",
        color='#ff3c00',
        default_strategy='fake_11',
        ports='443',
        protocol='QUIC/UDP',
        order=2,

        command_order=3,
        needs_new_separator=True,
        command_group="youtube",
        icon_name='fa5b.youtube',
        icon_color='#FF0000',
        base_filter="--filter-udp=443 --hostlist=youtube.txt",
        strategy_type="udp"
    ),
    
    'googlevideo_tcp': CategoryInfo(
        key='googlevideo_tcp',
        short_name='📹',
        full_name='GoogleVideo',
        emoji='📹',
        description='YouTube видео с CDN серверов GoogleVideo',
        tooltip="""🎬 YouTube видео с CDN серверов GoogleVideo
Обходит блокировку видеопотоков с серверов *.googlevideo.com (порт 443).
Это серверы доставки контента (CDN), откуда загружаются сами видеофайлы YouTube.
Нужно включать если видео не загружаются при работающем основном YouTube.""",
        color='#ff9900',
        default_strategy='none',
        ports='443',
        protocol='TCP',
        order=3,
  
        command_order=1,
        needs_new_separator=True,
        command_group="youtube",
        icon_name='fa5b.youtube',
        icon_color='#FF0000',
        base_filter="--filter-tcp=443 --hostlist-domains=googlevideo.com",
        strategy_type="tcp"
    ),

    'discord': CategoryInfo(
        key='discord',
        short_name='💬',
        full_name='Discord',
        emoji='💬',
        description='Discord мессенджер (порты 80, 443)',
        tooltip="""💬 Discord мессенджер (порты 80, 443)
Обходит блокировку текстовых чатов и загрузки файлов в Discord.
Работает с основным трафиком Discord через TCP протокол.
Включите если не работают текстовые сообщения и картинки.""",
        color='#7289da',
        default_strategy='dis4',
        ports='80, 443',
        protocol='TCP',
        order=4,

        command_order=5,
        needs_new_separator=True,
        command_group="discord",
        icon_name='fa5b.discord',
        icon_color='#7289DA',
        base_filter="--filter-tcp=443,2053,2083,2087,2096,8443 --hostlist=discord.txt",
        strategy_type="tcp"
    ),

    'discord_voice_udp': CategoryInfo(
        key='discord_voice_udp',
        short_name='🔊',
        full_name='Голосовые звонки/чаты',
        emoji='🔊',
        description='Голосовые звонки для Discord и Telegram (UDP порты)',
        tooltip="""🔊 Голосовые звонки для Discord и Telegram (UDP порты)""",
        color='#9b59b6',
        default_strategy='ipv4_ipv6_dup_autottl',
        ports='stun ports',
        protocol='UDP',
        order=5,
        command_order=6,
        needs_new_separator=True,
        command_group="discord",
        icon_name='fa5s.microphone',
        icon_color='#7289DA',
        # Для простых стратегий discord_voice
        base_filter="--filter-l7=discord,wireguard,stun",
        strategy_type="discord_voice"
    ),

    'udp_discord': CategoryInfo(
        key='udp_discord',
        short_name='💬',
        full_name='Discord UDP',
        emoji='💬',
        description='UDP протокол Discord мессенджер (порт 443)',
        tooltip="""💬 UDP для веб интерфейса дискорда, обычно не нужен но пусть будет.""",
        color='#7289da',
        default_strategy='none',
        ports='443',
        protocol='TCP',
        order=6,

        command_order=7,
        needs_new_separator=True,
        command_group="discord",
        icon_name='fa5b.discord',
        icon_color='#7289DA',
        base_filter="--filter-udp=443 --hostlist=discord.txt",
        strategy_type="udp"
    ),

    'update_discord': CategoryInfo(
        key='update_discord',
        short_name='💬',
        full_name='Update Discord',
        emoji='💬',
        description='Обновления Discord мессенджер (порт 443)',
        tooltip="""💬 Пробивает прицельно отдельно апдейт дискорда. Полезно когда сайт discord.com грузится, а приложение Windows постоянно ищет обновления.""",
        color='#7289da',
        default_strategy='none',
        ports='443',
        protocol='TCP',
        order=7,
        command_order=4,
        needs_new_separator=True,
        command_group="discord",
        icon_name='fa5b.discord',
        icon_color='#7289DA',
        base_filter="--filter-tcp=443 --hostlist-domains=updates.discord.com",
        strategy_type="tcp"
    ),

    'telegram_tcp': CategoryInfo(
        key='telegram_tcp',
        short_name='✈',
        full_name='Telegram (TCP)',
        emoji='✈',
        description='Telegram (веб версия и сайты)',
        tooltip="""✈ Telegram (веб версия и сайты)
Обходит блокировку САЙТОВ и веб версии в Telegram. НЕ ПОДХОДИТ ДЛЯ ПРИЛОЖЕНИЯ!
Включите если не работают сайты telegram.org и другие.""",
        color='#9b59b6',
        default_strategy='none',
        ports='80, 443',
        protocol='TCP',
        order=8,
        command_order=8,
        needs_new_separator=True,
        command_group="telegram",
        icon_name='fa5b.telegram',
        icon_color="#3CA7FF",
        base_filter="--filter-tcp=80,443 --hostlist=telegram.txt",
        strategy_type="tcp"
    ),

    'whatsapp_tcp': CategoryInfo(
        key='whatsapp_tcp',
        short_name='📱',
        full_name='WhatsApp',
        emoji='📱',
        description='WhatsApp интерфейс (порты 80, 443)',
        tooltip="""📱 WhatsApp интерфейс (порты 80, 443)
Обходит блокировку веб-интерфейса и приложения WhatsApp.
Работает с основным трафиком WhatsApp через TCP протокол.
Включите если не работают сообщения и медиа в WhatsApp.""",
        color='#25D366',
        default_strategy='none',
        ports='80, 443',
        protocol='TCP',
        order=10,
        command_order=10,
        needs_new_separator=True,
        command_group="messengers",
        icon_name='fa5b.whatsapp',
        icon_color='#25D366',
        base_filter="--filter-tcp=80,443 --ipset=ipset-whatsapp.txt",
        strategy_type="tcp"
    ),
    
    'soundcloud_tcp': CategoryInfo(
        key='soundcloud_tcp',
        short_name='🎵',
        full_name='SoundCloud',
        emoji='🎵',
        description='SoundCloud (порт 443)',
        tooltip="""🎵 SoundCloud (порт 443)
Обходит блокировку SoundCloud через стандартные веб-порты.
Работает с основным трафиком SoundCloud через TCP протокол.""",
        color='#ff5500',
        default_strategy='other_seqovl',
        ports='443',
        protocol='TCP',
        order=11,

        command_order=11,
        needs_new_separator=True,
        command_group="music",
        icon_name='fa5b.soundcloud',
        icon_color='#FF5500',
        base_filter="--filter-tcp=443 --hostlist=soundcloud.txt",
        strategy_type="tcp"
    ),

    'github_tcp': CategoryInfo(
        key='github_tcp',
        short_name='🐙',
        full_name='GitHub',
        emoji='🐙',
        description='GitHub (порты 80, 443)',
        tooltip="""🐙 GitHub (порты 80, 443)
Обходит блокировку GitHub через стандартные веб-порты.
Работает с основным трафиком GitHub через TCP протокол.""",
        color="#808080",
        default_strategy='other_seqovl',
        ports='443',
        protocol='TCP',
        order=12,

        command_order=12,
        needs_new_separator=True,
        command_group="github",
        icon_name='fa5b.github',
        icon_color="#FCFCFC",
        base_filter="--filter-tcp=443 --hostlist=github.txt",
        strategy_type="tcp"
    ),

    'rutracker_tcp': CategoryInfo(
        key='rutracker_tcp',
        short_name='🛠',
        full_name='Rutracker.org',
        emoji='🛠',
        description='Rutracker (порты 80, 443)',
        tooltip="""🛠 Rutracker (порты 80, 443)
Обходит блокировку торрент-трекера Rutracker через стандартные веб-порты.
Работает с основным трафиком Rutracker через TCP протокол.""",
        color='#6c5ce7',
        default_strategy='multisplit_split_pos_1',
        ports='80, 443',
        protocol='TCP',
        order=13,

        command_order=13,
        needs_new_separator=True,
        command_group="trackers",
        icon_name='fa5s.download',
        icon_color="#457AEB",
        base_filter="--filter-tcp=80,443 --ipset=ipset-rutracker.txt",
        strategy_type="tcp"
    ),

    'rutor_tcp': CategoryInfo(
        key='rutor_tcp',
        short_name='🛠',
        full_name='Rutor.info (.is)',
        emoji='🛠',
        description='Rutor.info (порты 80, 443)',
        tooltip="""🛠 Rutor.info (порты 80, 443)
Обходит блокировку торрент-трекера Rutor.info через стандартные веб-порты.
Работает с основным трафиком Rutor.info через TCP протокол.""",
        color='#6c5ce7',
        default_strategy='multisplit_split_pos_1',
        ports='80, 443',
        protocol='TCP',
        order=14,

        command_order=14,
        needs_new_separator=True,
        command_group="trackers",
        icon_name='fa5s.download',
        icon_color="#457AEB",
        base_filter="--filter-tcp=80,443 --hostlist=rutor.txt",
        strategy_type="tcp"
    ),

    'ntcparty_tcp': CategoryInfo(
        key='ntcparty_tcp',
        short_name='🛠',
        full_name='NtcParty',
        emoji='🛠',
        description='NtcParty (порты 80, 443)',
        tooltip="""🛠 NtcParty (порты 80, 443)
Обходит блокировку технического форума NtcParty отдельно от основных хостлистов.
Работает с основным трафиком NtcParty через TCP протокол.""",
        color="#d9d8e0",
        default_strategy='other_seqovl',
        ports='80, 443',
        protocol='TCP',
        order=15,

        command_order=15,
        needs_new_separator=True,
        command_group="trackers",
        icon_name='fa5s.tools',
        icon_color='#6C5CE7',
        base_filter="--filter-tcp=80,443 --ipset-ip=130.255.77.28",
        strategy_type="tcp"
    ),
    
    'twitch_tcp': CategoryInfo(
        key='twitch_tcp',
        short_name='🎙',
        full_name='Twitch',
        emoji='🎙',
        description='Twitch стриминг (порты 80, 443)',
        tooltip="""🎙 Twitch стриминг (порты 80, 443)
Обходит блокировку Twitch стримов через стандартные веб-порты.
Работает с основным трафиком Twitch через TCP протокол.
Включите если не работают стримы на Twitch.""",
        color='#9146ff',
        default_strategy='none',
        ports='80, 443',
        protocol='TCP',
        order=16,

        command_order=16,
        needs_new_separator=True,
        command_group="streaming",
        icon_name='fa5b.twitch',
        icon_color='#9146FF',
        base_filter="--filter-tcp=443 --hostlist=twitch.txt",
        strategy_type="tcp"
    ),

    'speedtest_tcp': CategoryInfo(
        key='speedtest_tcp',
        short_name='🌐',
        full_name='Speedtest',
        emoji='🌐',
        description='Speedtest (порт 443)',
        tooltip="""🌐 Speedtest (порт 443)
Обходит блокировку Speedtest через стандартные веб-порты.
Работает с основным трафиком Speedtest через TCP протокол.""",
        color='#9146ff',
        default_strategy='other_seqovl',
        ports= '443',
        protocol='TCP',
        order=17,

        command_order=17,
        needs_new_separator=True,
        command_group="hostlists",
        icon_name='fa5s.tachometer-alt',
        icon_color="#4671FF",
        base_filter="--filter-tcp=443,8080 --hostlist=speedtest.txt",
        strategy_type="tcp"
    ),

    'steam_tcp': CategoryInfo(
        key='steam_tcp',
        short_name='🎮',
        full_name='Steam',
        emoji='🎮',
        description='Steam (порты 80, 443)',
        tooltip="""🎮 Steam (порты 80, 443)
Обходит блокировку Steam через стандартные веб-порты.
Работает с основным трафиком Steam через TCP протокол.""",
        color='#9146ff',
        default_strategy='other_seqovl',
        ports= '80, 443',
        protocol='TCP',
        order=18,

        command_order=18,
        needs_new_separator=True,
        command_group="hostlists",
        icon_name='fa5b.steam',
        icon_color="#7390F0",
        base_filter="--filter-tcp=80,443 --hostlist=steam.txt",
        strategy_type="tcp"
    ),

    'itch_tcp': CategoryInfo(
        key='itch_tcp',
        short_name='🎮',
        full_name='Itch.io TCP',
        emoji='🎮',
        description='Itch.io (порты 80, 443)',
        tooltip="""🎮 Itch.io (порты 80, 443)
Обходит блокировку Itch.io через стандартные веб-порты.
Работает с основным трафиком Itch.io через TCP протокол.""",
        color='#ff4757',
        default_strategy='disorder2_badseq_tls_google',
        ports='443',
        protocol='TCP',
        order=19,

        command_order=19,
        needs_new_separator=True,
        command_group="games",
        icon_name='fa5b.itch-io',
        icon_color='#FA5C5C',
        base_filter="--filter-tcp=443 --hostlist=itch.txt",
        strategy_type="tcp"
    ),

    'google_tcp': CategoryInfo(
        key='google_tcp',
        short_name='🌐',
        full_name='Google TCP',
        emoji='🌐',
        description='Google TCP (порты 443, 853)',
        tooltip="""🌐 Google TCP (порты 443, 853)
        Обходит блокировки основных сайтов и сервисов Google""",
        color='#4285F4',
        default_strategy='none',
        ports='80, 443',
        protocol='TCP',
        order=20,

        command_order=20,
        needs_new_separator=True,
        command_group="hostlists",
        icon_name='fa5b.google',
        icon_color="#4285F4",
        base_filter="--filter-tcp=80,443 --hostlist=google.txt",
        strategy_type="tcp"
    ),

    'phasmophobia_udp': CategoryInfo(
        key='phasmophobia_udp',
        short_name='🎮',
        full_name='Phasmophobia UDP',
        emoji='🎮',
        description='Phasmophobia UDP (порты 5056, 27002)',
        tooltip="""🎮 Phasmophobia UDP (порты 5056, 27002)
Обходит блокировку Phasmophobia через игровые порты.
Работает с основным трафиком Phasmophobia через UDP протокол.
⚠️ Требует агрессивного режима фильтрации!""",
        color='#ff4757',
        default_strategy='fake_2_n2_test',
        ports='5056, 27002',
        protocol='UDP',
        order=21,

        command_order=21,
        needs_new_separator=True,
        command_group="games",
        icon_name='fa5s.ghost',
        icon_color='#8B4789',
        base_filter="--filter-udp=5056,27002",
        strategy_type="udp",
        requires_all_ports=True
    ),

    'battlefield_6_udp': CategoryInfo(
        key='battlefield_6_udp',
        short_name='🎮',
        full_name='Battlefield 6 UDP',
        emoji='🎮',
        description='Battlefield 6 UDP (порты 21000-21999)',
        tooltip="""🎮 Battlefield UDP (порты 21000-21999)
Обходит блокировку Battlefield через игровые порты.
Работает с основным трафиком Battlefield через UDP протокол.
⚠️ Требует агрессивного режима фильтрации!""",
        color='#ff4757',
        default_strategy='fake_2_n2_test',
        ports='21000-21999',
        protocol='UDP',
        order=22,

        command_order=22,
        needs_new_separator=True,
        command_group="games",
        icon_name='fa5s.fighter-jet',
        icon_color='#8B4789',
        base_filter="--filter-udp=21000-21999",
        strategy_type="udp",
        requires_all_ports=True
    ),

    'warp_tcp': CategoryInfo(
        key='warp_tcp',
        short_name='🎮',
        full_name='Warp TCP',
        emoji='🎮',
        description='Warp TCP (порты 443, 853)',
        tooltip="""🎮 Warp TCP (порты 443, 853)
Обходит блокировку Warp через стандартные веб-порты.
Работает с основным трафиком Warp через UDP протокол.""",
        color='#ff4757',
        default_strategy='other_seqovl',
        ports='443, 853',
        protocol='TCP',
        order=23,

        command_order=23,
        needs_new_separator=True,
        command_group="hostlists",
        icon_name='fa5b.cloudflare',
        icon_color="#FD7A3E",
        base_filter="--filter-tcp=443,853 --ipset-ip=162.159.36.1,162.159.46.1,2606:4700:4700::1111,2606:4700:4700::1001",
        strategy_type="tcp",
        requires_all_ports=True
    ),

    'other': CategoryInfo(
        key='other',
        short_name='🌐',
        full_name='Hostlist (HTTPS)',
        emoji='🌐',
        description='Заблокированные сайты из списка (порты 80, 443)',
        tooltip="""🌐 Заблокированные сайты из списка (порты 80, 443)
Обходит блокировку сайтов из файла other.txt через TCP.
Включает сотни популярных заблокированных сайтов и сервисов.
Можно редактировать список сайтов во вкладке Hostlist.""",
        color='#66ff66',
        default_strategy='other_seqovl',
        ports='80, 443',
        protocol='TCP',
        order=24,

        command_order=24,
        needs_new_separator=True,
        command_group="hostlists",
        icon_name='fa5b.chrome',
        icon_color='#2696F1',
        base_filter="--filter-tcp=443 --hostlist=netrogat.txt --new --filter-tcp=443 --hostlist=other.txt --hostlist=other2.txt --hostlist=russia-blacklist.txt --hostlist=porn.txt",
        strategy_type="tcp"
    ),
    
    'hostlist_80port': CategoryInfo(
        key='hostlist_80port',
        short_name='🌐',
        full_name='Hostlist (HTTP)',
        emoji='🌐',
        description='Заблокированные сайты из списка (порт 80)',
        tooltip="""🌐 Заблокированные сайты из списка (порт 80)
Обходит блокировку сайтов из файла other.txt через HTTP (порт 80).
Полезно если провайдер блокирует только HTTP трафик, а HTTPS оставляет открытым.
Можно редактировать список сайтов во вкладке Hostlist.""",
        color='#00ffcc',
        default_strategy='fake_multisplit_2_fake_http',
        ports='80',
        protocol='TCP',
        order=25,

        command_order=25,
        needs_new_separator=True,
        command_group="hostlists",
        icon_name='fa5b.chrome',
        icon_color="#2696F1",
        base_filter="--filter-tcp=80",
        strategy_type="http80"
    ),

    'ipset_tcp_cloudflare': CategoryInfo(
        key='ipset_tcp_cloudflare',
        short_name='☁️',
        full_name='IPset TCP (CloudFlare)',
        emoji='☁️',
        description='Сервера CloudFlare (все порты)',
        tooltip="""☁️ Используйте если нужно разблокировать сервера этого ресурса
⚠️ Требует агрессивного режима фильтрации!""",
        color='#ffa500',
        default_strategy='none',
        ports='all ports',
        protocol='TCP',
        order=26,

        command_order=26,
        needs_new_separator=True,
        command_group="ipsets",
        icon_name='fa5b.cloudflare',
        icon_color='#FFA500',
        base_filter="--filter-tcp=80,443,444-65535 --ipset=cloudflare-ipset.txt --ipset=ipset-cloudflare1.txt --ipset=ipset-cloudflare.txt",
        strategy_type="tcp",
        requires_all_ports=True
    ),

    'ipset_zapretkvn': CategoryInfo(
        key='ipset_zapretkvn',
        short_name='🐋',
        full_name='ZapretKVN',
        emoji='🐋',
        description='Сервера ZapretKVN (все порты)',
        tooltip="""🐋 Сервера ZapretKVN (все порты)
Обходит блокировку сервисов ZapretKVN через TCP.
Работает когда провайдер блокирует не домены, а конкретные IP.
Полезно для сервисов ZapretKVN.
⚠️ Требует агрессивного режима фильтрации!
📝 Стратегии применяются ко ВСЕМУ трафику (без фильтра payload)""",
        color='#6fa8dc',
        default_strategy='none',
        ports='all ports',
        protocol='TCP',
        order=27,

        command_order=27,
        needs_new_separator=True,
        command_group="ipsets",
        icon_name='fa5b.docker',  # Docker logo = whale 🐳
        icon_color='#6fa8dc',
        base_filter="--ipset=ipset-zapretkvn.txt",
        strategy_type="tcp",
        requires_all_ports=True,
        strip_payload=True  # Убираем --payload для применения ко всему трафику
    ),

    'ipset': CategoryInfo(
        key='ipset',
        short_name='🔢',
        full_name='IPset TCP (Games)',
        emoji='🔢',
        description='Блокировка по IP адресам (все порты)',
        tooltip="""🔢 Блокировка по IP адресам (все порты)
Обходит блокировку сервисов по их IP адресам через TCP.
Работает когда провайдер блокирует не домены, а конкретные IP.
Полезно для сервисов с фиксированными IP адресами.
⚠️ Требует агрессивного режима фильтрации!""",
        color='#ffa500',
        default_strategy='none',
        ports='all ports',
        protocol='TCP',
        order=27,

        command_order=27,
        needs_new_separator=True,
        command_group="ipsets",
        icon_name='fa5s.network-wired',
        icon_color='#FFA500',
        base_filter="--filter-tcp=80,443,444-65535 --ipset=russia-youtube-rtmps.txt --ipset=ipset-all.txt --ipset=ipset-base.txt --ipset=ipset-all2.txt --ipset=ipset-discord.txt --ipset-exclude=ipset-dns.txt",
        strategy_type="tcp",
        requires_all_ports=True
    ),

    'ovh_udp': CategoryInfo(
        key='ovh_udp',
        short_name='🛡',
        full_name='OVH UDP',
        emoji='🛡',
        description='OVH UDP (игровые сервера провайдера ОВХ)',
        tooltip="""🛡 OVH UDP (игровые сервера провайдера ОВХ)
Обходит блокировку сервисов по их IP адресам через UDP.
Работает когда провайдер блокирует не домены, а конкретные IP.
Полезно для сервисов с фиксированными IP адресами.
⚠️ Требует агрессивного режима фильтрации!""",
        color="#e69f08",
        default_strategy='none',
        ports='all ports',
        protocol='UDP',
        order=28,

        command_order=28,
        needs_new_separator=True,
        command_group="ipsets",
        icon_name='fa5s.gamepad',
        icon_color="#F1BB25",
        base_filter="--filter-udp=* --ipset=ipset-ovh.txt",
        strategy_type="udp",
        requires_all_ports=True
    ),

    'ipset_udp': CategoryInfo(
        key='ipset_udp',
        short_name='🎮',
        full_name='IPset UDP (Games)',
        emoji='🎮',
        description='Блокировка по IP адресам (UDP для игр)',
        tooltip="""🔢 Блокировка по IP адресам (UDP для игр)
Обходит блокировку сервисов по их IP адресам через UDP.
Работает когда провайдер блокирует не домены, а конкретные IP.
Полезно для сервисов с фиксированными IP адресами.
⚠️ Требует агрессивного режима фильтрации!""",
        color='#006eff',
        default_strategy='none',
        ports='all ports',
        protocol='UDP',
        order=29,

        command_order=29,
        needs_new_separator=False,  # IPset UDP последний
        command_group="ipsets",
        icon_name='fa5s.gamepad',
        icon_color="#D49B00",
        base_filter="--filter-udp=* --ipset=ipset-all.txt --ipset=ipset-base.txt --ipset=ipset-all2.txt --ipset=cloudflare-ipset.txt --ipset=ipset-cloudflare1.txt --ipset=ipset-cloudflare.txt --ipset-exclude=ipset-dns.txt",
        strategy_type="udp",
        requires_all_ports=True
    ),
}

# Режимы которые требуют агрессивной фильтрации (все порты)
AGGRESSIVE_MODES = {"windivert_all", "wf-l3-all"}
# Режимы аккуратной фильтрации (ограниченные порты)
CAREFUL_MODES = {"windivert-discord-media-stun-sites", "wf-l3"}

def get_category_icon(category_key: str):
    """Возвращает Font Awesome иконку для категории"""
    import qtawesome as qta
    
    category = CATEGORIES_REGISTRY.get(category_key)
    if category:
        try:
            icon_name = category.icon_name
            if icon_name and icon_name.startswith(('fa5s.', 'fa5b.', 'fa.', 'mdi.')):
                return qta.icon(icon_name, color=category.icon_color)
        except Exception as e:
            log(f"Ошибка создания иконки для {category_key}: {e}", "⚠ WARNING")
    
    # Безопасный fallback
    try:
        return qta.icon('fa5s.globe', color='#2196F3')
    except:
        return None
    
# ==================== ОСНОВНЫЕ ФУНКЦИИ ====================

class StrategiesRegistry:
    """Главный класс для управления всеми стратегиями"""
    
    def __init__(self):
        self._categories = CATEGORIES_REGISTRY

    @property
    def strategies(self) -> Dict[str, Dict]:
        """
        Получение всех стратегий (загружает ВСЕ типы)
        ⚠️ Используйте get_category_strategies() для лучшей производительности
        """
        return _lazy_import_all_strategies()
    
    @property
    def categories(self) -> Dict[str, CategoryInfo]:
        """Получение всех категорий"""
        return self._categories

    def get_category_strategies(self, category_key: str) -> Dict[str, Any]:
        """Получить стратегии для категории"""
        category_info = self._categories.get(category_key)
        if not category_info:
            return {}
        return _lazy_import_base_strategies(category_info.strategy_type)
    
    def get_category_info(self, category_key: str) -> Optional[CategoryInfo]:
        """Получить информацию о категории"""
        return self._categories.get(category_key)

    def get_strategy_args_safe(self, category_key: str, strategy_id: str) -> Optional[str]:
        """
        Получить полные аргументы стратегии.
        
        Логика:
        1. Если strategy_id == "none" - возвращаем пустую строку
        2. Для discord_voice - если args содержит --filter - используем как есть
        3. Для остальных - склеиваем base_filter + техника
        4. Если strip_payload=True - убираем --payload= из аргументов
        """
        # Проверка на none
        if strategy_id == "none":
            return ""
        
        category_info = self.get_category_info(category_key)
        if not category_info:
            log(f"Категория {category_key} не найдена", "⚠ WARNING")
            return None
        
        strategy_type = category_info.strategy_type
        base_filter = category_info.base_filter
        
        # Получаем стратегию из BASE файла
        base_strategies = _lazy_import_base_strategies(strategy_type)
        strategy = base_strategies.get(strategy_id)
        
        if not strategy:
            # Логируем только один раз за сессию (чтобы не спамить)
            warn_key = f"{strategy_type}:{strategy_id}"
            if warn_key not in _logged_missing_strategies:
                _logged_missing_strategies.add(warn_key)
                log(f"Стратегия {strategy_id} не найдена в типе {strategy_type}", "DEBUG")
            return None
        
        base_args = strategy.get("args", "")
        
        # Если args пустой - категория отключена
        if not base_args:
            return ""
        
        # ✅ Если strip_payload=True - убираем --payload= из аргументов
        # Это нужно для IPset категорий без фильтра портов,
        # чтобы стратегия применялась ко ВСЕМУ трафику, а не только к TLS
        if category_info.strip_payload:
            base_args = _strip_payload_from_args(base_args)
        
        # Для discord_voice - проверяем, содержит ли args уже фильтры
        if strategy_type == "discord_voice":
            if "--filter-" in base_args or "--new" in base_args:
                # Сложная стратегия с полной командой
                return base_args
            # Простая стратегия - добавляем base_filter
        
        # Склеиваем: base_filter + техника
        if base_filter and base_args:
            return f"{base_filter} {base_args}"
        elif base_filter:
            return base_filter
        else:
            return base_args

    def get_strategy_name_safe(self, category_key: str, strategy_id: str) -> str:
        """Получить имя стратегии"""
        if strategy_id == "none":
            return "⛔ Отключено"
        
        category_info = self.get_category_info(category_key)
        if not category_info:
            return strategy_id or "Unknown"
        
        base_strategies = _lazy_import_base_strategies(category_info.strategy_type)
        strategy = base_strategies.get(strategy_id)
        
        if strategy:
            return strategy.get('name', strategy_id)
        return strategy_id or "Unknown"
    
    def get_default_selections(self) -> Dict[str, str]:
        """Получить стратегии по умолчанию для всех категорий"""
        return {
            key: info.default_strategy
            for key, info in self._categories.items()
        }
    
    def get_none_strategies(self) -> Dict[str, str]:
        """Получить 'none' стратегии для всех категорий"""
        # Теперь для всех категорий используется единая стратегия "none"
        return {
            key: "none"
            for key in self._categories.keys()
        }

    def get_all_category_keys(self) -> List[str]:
        """Получить все ключи категорий в порядке сортировки"""
        return sorted(self._categories.keys(), key=lambda k: self._categories[k].order)
    
    def get_tab_names_dict(self) -> Dict[str, Tuple[str, str]]:
        """Получить словарь имен табов (короткое, полное)"""
        return {
            key: (info.short_name, info.full_name)
            for key, info in self._categories.items()
        }
    
    def get_tab_tooltips_dict(self) -> Dict[str, str]:
        """Получить словарь подсказок для табов"""
        return {
            key: info.tooltip
            for key, info in self._categories.items()
        }
    
    def get_category_colors_dict(self) -> Dict[str, str]:
        """Получить словарь цветов для категорий"""
        return {
            key: info.color
            for key, info in self._categories.items()
        }

    def get_all_category_keys_by_command_order(self) -> List[str]:
        """Получить все ключи категорий в порядке командной строки"""
        return sorted(self._categories.keys(), key=lambda k: self._categories[k].command_order)
    
    def get_visible_category_keys(self, base_args_mode: str) -> List[str]:
        """
        Получить ключи категорий, видимых для данного режима фильтрации.
        
        Args:
            base_args_mode: Режим фильтрации ('windivert-discord-media-stun-sites', 'wf-l3', 
                           'windivert_all', 'wf-l3-all')
        
        Returns:
            Список ключей категорий, отсортированных по order
        """
        # Аккуратные режимы скрывают категории с requires_all_ports=True
        is_careful_mode = base_args_mode in CAREFUL_MODES
        
        visible_keys = []
        for key, info in self._categories.items():
            # Если аккуратный режим и категория требует все порты - скрываем
            if is_careful_mode and info.requires_all_ports:
                continue
            visible_keys.append(key)
        
        return sorted(visible_keys, key=lambda k: self._categories[k].order)
    
    def is_category_visible(self, category_key: str, base_args_mode: str) -> bool:
        """Проверяет, видна ли категория для данного режима"""
        category_info = self._categories.get(category_key)
        if not category_info:
            return False
        
        is_careful_mode = base_args_mode in CAREFUL_MODES
        
        # Если аккуратный режим и категория требует все порты - скрываем
        if is_careful_mode and category_info.requires_all_ports:
            return False
        
        return True
    
    def get_hidden_categories_for_mode(self, base_args_mode: str) -> List[str]:
        """Возвращает список скрытых категорий для данного режима"""
        is_careful_mode = base_args_mode in CAREFUL_MODES
        
        if not is_careful_mode:
            return []
        
        return [
            key for key, info in self._categories.items()
            if info.requires_all_ports
        ]
    
    def is_category_enabled_by_filters(self, category_key: str) -> bool:
        """
        Проверяет, включена ли категория на основе текущих настроек фильтров.
        Возвращает True если категория должна быть видна.
        """
        from strategy_menu import (
            get_wf_tcp_80_enabled, get_wf_tcp_443_enabled,
            get_wf_udp_443_enabled, get_wf_tcp_all_ports_enabled,
            get_wf_udp_all_ports_enabled, get_wf_raw_discord_media_enabled,
            get_wf_raw_stun_enabled
        )
        
        category_info = self._categories.get(category_key)
        if not category_info:
            return False
        
        protocol = category_info.protocol
        base_filter = category_info.base_filter
        requires_all = category_info.requires_all_ports
        
        # HTTP 80 port
        if category_key == 'hostlist_80port':
            return get_wf_tcp_80_enabled()
        
        # Discord Voice UDP (raw filters)
        if category_key == 'discord_voice_udp':
            return get_wf_raw_discord_media_enabled() or get_wf_raw_stun_enabled()
        
        # UDP категории
        if protocol in ('UDP', 'QUIC/UDP'):
            # UDP 443 (QUIC) - youtube_udp, udp_discord
            if '443' in category_info.ports and not requires_all:
                return get_wf_udp_443_enabled()
            # UDP all ports - игры и ipset
            if requires_all or '*' in base_filter:
                return get_wf_udp_all_ports_enabled()
            return get_wf_udp_443_enabled()
        
        # TCP категории
        if protocol == 'TCP':
            # TCP all ports - ipset категории
            if requires_all:
                return get_wf_tcp_all_ports_enabled()
            # TCP 443 - основные категории
            return get_wf_tcp_443_enabled()
        
        return True
    
    def get_enabled_category_keys(self) -> List[str]:
        """Получить ключи категорий, включенных по текущим фильтрам"""
        enabled = []
        for key in self._categories.keys():
            if self.is_category_enabled_by_filters(key):
                enabled.append(key)
        return sorted(enabled, key=lambda k: self._categories[k].order)

# ==================== ГЛОБАЛЬНЫЙ ЭКЗЕМПЛЯР ====================

# Создаем глобальный экземпляр реестра
registry = StrategiesRegistry()

# ==================== ФУНКЦИИ СОВМЕСТИМОСТИ ====================

def get_strategies_registry() -> StrategiesRegistry:
    """Получить глобальный экземпляр реестра"""
    return registry

def get_category_strategies(category_key: str) -> Dict[str, Any]:
    """Совместимость: получить стратегии категории"""
    return registry.get_category_strategies(category_key)

def get_category_info(category_key: str) -> Optional[CategoryInfo]:
    """Совместимость: получить информацию о категории"""
    return registry.get_category_info(category_key)

def get_all_strategies() -> Dict[str, Dict]:
    """Совместимость: получить все стратегии"""
    return registry.strategies

def get_tab_names() -> Dict[str, Tuple[str, str]]:
    """Совместимость: получить имена табов"""
    return registry.get_tab_names_dict()

def get_tab_tooltips() -> Dict[str, str]:
    """Совместимость: получить подсказки табов"""
    return registry.get_tab_tooltips_dict()

def get_default_selections() -> Dict[str, str]:
    """Совместимость: получить стратегии по умолчанию"""
    return registry.get_default_selections()

# ==================== ЭКСПОРТ ====================

__all__ = [
    'StrategiesRegistry',
    'CategoryInfo',
    'CATEGORIES_REGISTRY',
    'AGGRESSIVE_MODES',
    'CAREFUL_MODES',
    'registry',
    'get_strategies_registry',
    'get_category_strategies',
    'get_category_info', 
    'get_all_strategies',
    'get_tab_names',
    'get_tab_tooltips',
    'get_default_selections',
    'get_category_icon',
    'is_category_enabled_by_filters',
    'get_enabled_category_keys',
]

def is_category_enabled_by_filters(category_key: str) -> bool:
    """Совместимость: проверить включена ли категория по фильтрам"""
    return registry.is_category_enabled_by_filters(category_key)

def get_enabled_category_keys() -> List[str]:
    """Совместимость: получить включенные категории"""
    return registry.get_enabled_category_keys()
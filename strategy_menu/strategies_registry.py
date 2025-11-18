"""
Централизованный реестр всех стратегий и категорий.
Управляет импортом, метаданными и предоставляет единый интерфейс.
"""

from typing import Dict, Tuple, List, Optional, Any
from dataclasses import dataclass
from log import log

# ==================== LAZY IMPORTS ====================

_strategies_cache = {}  # {category_key: strategies_dict}
_imported_categories = set()  # Какие категории уже загружены

def _lazy_import_category_strategies(category_key: str) -> Dict:
    """Ленивый импорт стратегий ОДНОЙ категории"""
    global _strategies_cache, _imported_categories
    
    # Проверяем кэш
    if category_key in _imported_categories:
        return _strategies_cache.get(category_key, {})
    
    try:
        # Импортируем только нужную категорию
        if category_key == 'youtube':
            from .strategies.YOUTUBE_TCP_STRATEGIES import YOUTUBE_TCP_STRATEGIES
            _strategies_cache['youtube'] = YOUTUBE_TCP_STRATEGIES
            
        elif category_key == 'youtube_udp':
            from .strategies.YOUTUBE_UDP_STRATEGIES import YOUTUBE_QUIC_STRATEGIES
            _strategies_cache['youtube_udp'] = YOUTUBE_QUIC_STRATEGIES
            
        elif category_key == 'googlevideo_tcp':
            from .strategies.GOOGLEVIDEO_TCP_STRATEGIES import GOOGLEVIDEO_STRATEGIES
            _strategies_cache['googlevideo_tcp'] = GOOGLEVIDEO_STRATEGIES
            
        elif category_key == 'discord':
            from .strategies.DISCORD_TCP_STRATEGIES import DISCORD_TCP_STRATEGIES
            _strategies_cache['discord'] = DISCORD_TCP_STRATEGIES
            
        elif category_key == 'discord_voice_udp':
            from .strategies.DISCORD_VOICE_STRATEGIES import DISCORD_VOICE_STRATEGIES
            _strategies_cache['discord_voice_udp'] = DISCORD_VOICE_STRATEGIES
            
        elif category_key == 'udp_discord':
            from .strategies.DISCORD_UPD_STRATEGIES import DISCORD_UPD_STRATEGIES
            _strategies_cache['udp_discord'] = DISCORD_UPD_STRATEGIES
            
        elif category_key == 'update_discord':
            from .strategies.UPDATES_DISCORD_TCP_STRATEGIES import UPDATES_DISCORD_TCP_STRATEGIES
            _strategies_cache['update_discord'] = UPDATES_DISCORD_TCP_STRATEGIES
            
        elif category_key == 'telegram_tcp':
            from .strategies.TELEGRAM_TCP_STRATEGIES import TELEGRAM_TCP_STRATEGIES
            _strategies_cache['telegram_tcp'] = TELEGRAM_TCP_STRATEGIES
            
        elif category_key == 'telegram_call':
            from .strategies.TELEGRAM_CALL_STRATEGIES import TELEGRAM_CALL_STRATEGIES
            _strategies_cache['telegram_call'] = TELEGRAM_CALL_STRATEGIES
            
        elif category_key == 'soundcloud_tcp':
            from .strategies.SOUNDCLOUD_TCP_STRATEGIES import SOUNDCLOUD_STRATEGIES
            _strategies_cache['soundcloud_tcp'] = SOUNDCLOUD_STRATEGIES
            
        elif category_key == 'github_tcp':
            from .strategies.GITHUB_TCP_STRATEGIES import GITHUB_TCP_STRATEGIES
            _strategies_cache['github_tcp'] = GITHUB_TCP_STRATEGIES
            
        elif category_key == 'rutracker_tcp':
            from .strategies.RUTRACKER_TCP_STRATEGIES import RUTRACKER_TCP_STRATEGIES
            _strategies_cache['rutracker_tcp'] = RUTRACKER_TCP_STRATEGIES
            
        elif category_key == 'rutor_tcp':
            from .strategies.RUTOR_TCP_STRATEGIES import RUTOR_TCP_STRATEGIES
            _strategies_cache['rutor_tcp'] = RUTOR_TCP_STRATEGIES
            
        elif category_key == 'ntcparty_tcp':
            from .strategies.NTCPARTY_TCP_STRATEGIES import NTCPARTY_TCP_STRATEGIES
            _strategies_cache['ntcparty_tcp'] = NTCPARTY_TCP_STRATEGIES
            
        elif category_key == 'twitch_tcp':
            from .strategies.TWITCH_TCP_STRATEGIES import TWITCH_TCP_STRATEGIES
            _strategies_cache['twitch_tcp'] = TWITCH_TCP_STRATEGIES
            
        elif category_key == 'speedtest_tcp':
            from .strategies.SPEEDTEST_TCP_STRATEGIES import SPEEDTEST_TCP_STRATEGIES
            _strategies_cache['speedtest_tcp'] = SPEEDTEST_TCP_STRATEGIES
            
        elif category_key == 'steam_tcp':
            from .strategies.STEAM_TCP_STRATEGIES import STEAM_TCP_STRATEGIES
            _strategies_cache['steam_tcp'] = STEAM_TCP_STRATEGIES
            
        elif category_key == 'itch_tcp':
            from .strategies.ITCH_TCP_STRATEGIES import ITCH_TCP_STRATEGIES
            _strategies_cache['itch_tcp'] = ITCH_TCP_STRATEGIES

        elif category_key == 'google_tcp':
            from .strategies.GOOGLE_TCP_STRATEGIES import GOOGLE_TCP_STRATEGIES
            _strategies_cache['google_tcp'] = GOOGLE_TCP_STRATEGIES
            
        elif category_key == 'phasmophobia_udp':
            from .strategies.PHASMOPHOBIA_UDP_STRATEGIES import PHASMOPHOBIA_UDP_STRATEGIES
            _strategies_cache['phasmophobia_udp'] = PHASMOPHOBIA_UDP_STRATEGIES
            
        elif category_key == 'warp_tcp':
            from .strategies.WARP_STRATEGIES import WARP_STRATEGIES
            _strategies_cache['warp_tcp'] = WARP_STRATEGIES
            
        elif category_key == 'other':
            from .strategies.OTHER_STRATEGIES import OTHER_STRATEGIES
            _strategies_cache['other'] = OTHER_STRATEGIES
            
        elif category_key == 'hostlist_80port':
            from .strategies.HOSTLIST_80PORT_STRATEGIES import HOSTLIST_80PORT_STRATEGIES
            _strategies_cache['hostlist_80port'] = HOSTLIST_80PORT_STRATEGIES

        elif category_key == 'ipset_tcp_cloudflare':
            from .strategies.IPSET_CLOUDFLARE_STRATEGIES import IPSET_CLOUDFLARE_STRATEGIES
            _strategies_cache['ipset_tcp_cloudflare'] = IPSET_CLOUDFLARE_STRATEGIES

        elif category_key == 'ipset':
            from .strategies.IPSET_TCP_STRATEGIES import IPSET_TCP_STRATEGIES
            _strategies_cache['ipset'] = IPSET_TCP_STRATEGIES

        elif category_key == 'ovh_udp':
            from .strategies.OVH_UDP_STRATEGIES import OVH_UDP_STRATEGIES
            _strategies_cache['ovh_udp'] = OVH_UDP_STRATEGIES

        elif category_key == 'ipset_udp':
            from .strategies.IPSET_UDP_STRATEGIES import IPSET_UDP_STRATEGIES
            _strategies_cache['ipset_udp'] = IPSET_UDP_STRATEGIES
        
        else:
            log(f"Неизвестная категория: {category_key}", "⚠ WARNING")
            _strategies_cache[category_key] = {}
        
        _imported_categories.add(category_key)
        log(f"Стратегии категории '{category_key}' загружены ({len(_strategies_cache.get(category_key, {}))} шт)", "DEBUG")
        
    except ImportError as e:
        log(f"Ошибка импорта стратегий категории '{category_key}': {e}", "❌ ERROR")
        _strategies_cache[category_key] = {}
        _imported_categories.add(category_key)
    
    return _strategies_cache.get(category_key, {})

def _lazy_import_all_strategies() -> Dict[str, Dict]:
    """Импортирует ВСЕ стратегии (только если очень нужно)"""
    global _strategies_cache
    
    # Импортируем все категории
    for category_key in CATEGORIES_REGISTRY.keys():
        if category_key not in _imported_categories:
            _lazy_import_category_strategies(category_key)
    
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
    none_strategy: str
    ports: str
    protocol: str
    order: int  # Порядок в UI
    
    command_order: int  # Порядок в командной строке
    needs_new_separator: bool = False  # Нужен ли --new после этой категории
    command_group: str = "default"  # Группа команд (команды в одной группе идут подряд)

    icon_name: str = 'fa5s.globe'  # Font Awesome иконка по умолчанию
    icon_color: str = '#2196F3'    # Цвет иконки по умолчанию

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
        none_strategy='youtube_tcp_none',
        ports='80, 443',
        protocol='TCP',
        order=1,

        command_order=2,
        needs_new_separator=True,
        command_group="youtube",
        icon_name='fa5b.youtube',
        icon_color='#FF0000'
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
        none_strategy='youtube_udp_none',
        ports='443',
        protocol='QUIC/UDP',
        order=2,

        command_order=3,
        needs_new_separator=True,
        command_group="youtube",
        icon_name='fa5b.youtube',
        icon_color='#FF0000'
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
        default_strategy='googlevideo_tcp_none',
        none_strategy='googlevideo_tcp_none',
        ports='443',
        protocol='TCP',
        order=3,
  
        command_order=1,
        needs_new_separator=True,
        command_group="google",
        icon_name='fa5b.google',
        icon_color='#4285F4'
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
        none_strategy='discord_tcp_none',
        ports='80, 443',
        protocol='TCP',
        order=4,

        command_order=5,
        needs_new_separator=True,
        command_group="discord",
        icon_name='fa5b.discord',
        icon_color='#7289DA'
    ),

    'discord_voice_udp': CategoryInfo(
        key='discord_voice_udp',
        short_name='🔊',
        full_name='Discord Voice',
        emoji='🔊',
        description='Discord голосовые звонки (UDP порты)',
        tooltip="""🔊 Discord голосовые звонки (UDP порты)
Обходит блокировку голосовой связи и видеозвонков в Discord.
Использует UDP протокол для передачи голоса в реальном времени.
Включите если не работают голосовые каналы и звонки.""",
        color='#9b59b6',
        default_strategy='ipv4_dup2_autottl_cutoff_n3',
        none_strategy='discord_voice_udp_none',
        ports='stun ports',
        protocol='UDP',
        order=5,

        command_order=6,
        needs_new_separator=True,
        command_group="discord",
        icon_name='fa5s.microphone',
        icon_color='#7289DA'
    ),

    'udp_discord': CategoryInfo(
        key='udp_discord',
        short_name='💬',
        full_name='Discord UDP',
        emoji='💬',
        description='UDP протокол Discord мессенджер (порт 443)',
        tooltip="""💬 UDP для веб интерфейса дискорда, обычно не нужен но пусть будет.""",
        color='#7289da',
        default_strategy='udp_discord_tcp_none',
        none_strategy='udp_discord_tcp_none',
        ports='443',
        protocol='TCP',
        order=6,

        command_order=7,
        needs_new_separator=True,
        command_group="discord",
        icon_name='fa5b.discord',
        icon_color='#7289DA'
    ),

    'update_discord': CategoryInfo(
        key='update_discord',
        short_name='💬',
        full_name='Update Discord',
        emoji='💬',
        description='Обновления Discord мессенджер (порт 443)',
        tooltip="""💬 Пробивает прицельно отдельно апдейт дискорда. Полезно когда сайт discord.com грузится, а приложение Windows постоянно ищет обновления.""",
        color='#7289da',
        default_strategy='update_discord_tcp_none',
        none_strategy='update_discord_tcp_none',
        ports='443',
        protocol='TCP',
        order=7,
        command_order=4,
        needs_new_separator=True,
        command_group="discord",
        icon_name='fa5b.discord',
        icon_color='#7289DA'
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
        default_strategy='telegram_tcp_none',
        none_strategy='telegram_tcp_none',
        ports='80, 443',
        protocol='TCP',
        order=8,
        command_order=8,
        needs_new_separator=True,
        command_group="telegram",
        icon_name='fa5b.telegram',
        icon_color="#3CA7FF"
    ),

    'telegram_call': CategoryInfo(
        key='telegram_call',
        short_name='🔊',
        full_name='Telegram Call',
        emoji='🔊',
        description='Telegram голосовые звонки (UDP порты)',
        tooltip="""🔊 Telegram голосовые звонки (UDP порты)
Обходит блокировку голосовой связи и видеозвонков в Telegram.
Использует UDP протокол для передачи голоса в реальном времени.
Включите если не работают голосовые каналы и звонки.""",
        color='#9b59b6',
        default_strategy='dronator_43',
        none_strategy='telegram_call_none',
        ports='stun ports',
        protocol='UDP',
        order=9,
        command_order=9,
        needs_new_separator=True,
        command_group="telegram",
        icon_name='fa5b.telegram',
        icon_color="#3CA7FF"
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
        none_strategy='soundcloud_tcp_none',
        ports='443',
        protocol='TCP',
        order=10,

        command_order=10,
        needs_new_separator=True,
        command_group="music",
        icon_name='fa5b.soundcloud',
        icon_color='#FF5500',
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
        none_strategy='github_tcp_none',
        ports='443',
        protocol='TCP',
        order=10,

        command_order=10,
        needs_new_separator=True,
        command_group="github",
        icon_name='fa5b.github',
        icon_color="#FCFCFC",
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
        none_strategy='rutracker_tcp_none',
        ports='80, 443',
        protocol='TCP',
        order=11,

        command_order=11,
        needs_new_separator=True,
        command_group="trackers",
        icon_name='fa5s.download',
        icon_color="#457AEB",
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
        none_strategy='rutor_tcp_none',
        ports='80, 443',
        protocol='TCP',
        order=12,

        command_order=12,
        needs_new_separator=True,
        command_group="trackers",
        icon_name='fa5s.download',
        icon_color="#457AEB",
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
        none_strategy='ntcparty_tcp_none',
        ports='80, 443',
        protocol='TCP',
        order=13,

        command_order=13,
        needs_new_separator=True,
        command_group="trackers",
        icon_name='fa5s.tools',
        icon_color='#6C5CE7',
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
        default_strategy='twitch_tcp_none',
        none_strategy='twitch_tcp_none',
        ports='80, 443',
        protocol='TCP',
        order=14,

        command_order=14,
        needs_new_separator=True,
        command_group="streaming",
        icon_name='fa5b.twitch',
        icon_color='#9146FF',
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
        none_strategy='speedtest_tcp_none',
        ports= '443',
        protocol='TCP',
        order=15,

        command_order=15,
        needs_new_separator=True,
        command_group="hostlists",
        icon_name='fa5s.tachometer-alt',
        icon_color="#4671FF",
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
        none_strategy='steam_tcp_none',
        ports= '80, 443',
        protocol='TCP',
        order=16,

        command_order=16,
        needs_new_separator=True,
        command_group="hostlists",
        icon_name='fa5b.steam',
        icon_color="#7390F0",
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
        none_strategy='itch_tcp_none',
        ports='443',
        protocol='TCP',
        order=17,

        command_order=17,
        needs_new_separator=True,
        command_group="games",
        icon_name='fa5b.itch-io',
        icon_color='#FA5C5C'
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
        default_strategy='google_tcp_none',
        none_strategy='google_tcp_none',
        ports='80, 443',
        protocol='TCP',
        order=18,

        command_order=18,
        needs_new_separator=True,
        command_group="hostlists",
        icon_name='fa5b.google',
        icon_color="#4285F4"
    ),

    'phasmophobia_udp': CategoryInfo(
        key='phasmophobia_udp',
        short_name='🎮',
        full_name='Phasmophobia UDP',
        emoji='🎮',
        description='Phasmophobia UDP (порты 443)',
        tooltip="""🎮 Phasmophobia UDP (порты 443)
Обходит блокировку Phasmophobia через стандартные веб-порты.
Работает с основным трафиком Phasmophobia через UDP протокол.""",
        color='#ff4757',
        default_strategy='fake_2_n2_test',
        none_strategy='phasmophobia_udp_none',
        ports='443',
        protocol='UDP',
        order=19,

        command_order=19,
        needs_new_separator=True,
        command_group="games",
        icon_name='fa5s.ghost',
        icon_color='#8B4789'
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
        none_strategy='warp_none',
        ports='443, 853',
        protocol='TCP',
        order=20,

        command_order=20,
        needs_new_separator=True,
        command_group="hostlists",
        icon_name='fa5b.cloudflare',
        icon_color="#FD7A3E"
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
        none_strategy='other_tcp_none',
        ports='80, 443',
        protocol='TCP',
        order=21,

        command_order=21,
        needs_new_separator=True,
        command_group="hostlists",
        icon_name='fa5b.chrome',
        icon_color='#2696F1',
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
        none_strategy='hostlist_80port_none',
        ports='80',
        protocol='TCP',
        order=22,

        command_order=22,
        needs_new_separator=True,
        command_group="hostlists",
        icon_name='fa5b.chrome',
        icon_color="#2696F1",
    ),

    'ipset_tcp_cloudflare': CategoryInfo(
        key='ipset_tcp_cloudflare',
        short_name='☁️',
        full_name='IPset TCP (CloudFlare)',
        emoji='☁️',
        description='Сервера CloudFlare (все порты)',
        tooltip="""☁️ Используйте если нужно разблокировать сервера этого ресурса""",
        color='#ffa500',
        default_strategy='ipset_tcp_none',
        none_strategy='ipset_tcp_none',
        ports='all ports',
        protocol='TCP',
        order=23,

        command_order=23,
        needs_new_separator=True,
        command_group="ipsets",
        icon_name='fa5b.cloudflare',
        icon_color='#FFA500',
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
Полезно для сервисов с фиксированными IP адресами.""",
        color='#ffa500',
        default_strategy='ipset_tcp_none',
        none_strategy='ipset_tcp_none',
        ports='all ports',
        protocol='TCP',
        order=24,

        command_order=24,
        needs_new_separator=True,
        command_group="ipsets",
        icon_name='fa5s.network-wired',
        icon_color='#FFA500',
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
Полезно для сервисов с фиксированными IP адресами.""",
        color="#e69f08",
        default_strategy='ovh_udp_none',
        none_strategy='ovh_udp_none',
        ports='all ports',
        protocol='UDP',
        order=25,

        command_order=25,
        needs_new_separator=True,
        command_group="ipsets",
        icon_name='fa5s.gamepad',
        icon_color="#F1BB25",
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
Полезно для сервисов с фиксированными IP адресами.""",
        color='#006eff',
        default_strategy='ipset_udp_none',
        none_strategy='ipset_udp_none',
        ports='all ports',
        protocol='UDP',
        order=26,

        command_order=26,
        needs_new_separator=False,  # IPset UDP последний
        command_group="ipsets",
        icon_name='fa5s.gamepad',
        icon_color="#D49B00",
    ),
}

def get_category_icon(category_key: str):
    """Возвращает Font Awesome иконку для категории"""
    import qtawesome as qta
    
    category = CATEGORIES_REGISTRY.get(category_key)
    if category:
        return qta.icon(category.icon_name, color=category.icon_color)
    else:
        # Иконка по умолчанию
        return qta.icon('fa5s.globe', color='#2196F3')
    
# ==================== ОСНОВНЫЕ ФУНКЦИИ ====================

class StrategiesRegistry:
    """Главный класс для управления всеми стратегиями"""
    
    def __init__(self):
        self._categories = CATEGORIES_REGISTRY
    
    @property
    def strategies(self) -> Dict[str, Dict]:
        """
        Получение всех стратегий (загружает ВСЕ категории)
        ⚠️ Используйте get_category_strategies() для лучшей производительности
        """
        return _lazy_import_all_strategies()
    
    @property
    def categories(self) -> Dict[str, CategoryInfo]:
        """Получение всех категорий"""
        return self._categories
    
    def get_category_strategies(self, category_key: str) -> Dict[str, Any]:
        """
        Получить стратегии для конкретной категории
        ✅ Оптимизировано - загружает только нужную категорию
        """
        return _lazy_import_category_strategies(category_key)
    
    def get_category_info(self, category_key: str) -> Optional[CategoryInfo]:
        """Получить информацию о категории"""
        return self._categories.get(category_key)
    
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
    
    def get_default_selections(self) -> Dict[str, str]:
        """Получить стратегии по умолчанию для всех категорий"""
        return {
            key: info.default_strategy
            for key, info in self._categories.items()
        }
    
    def get_none_strategies(self) -> Dict[str, str]:
        """Получить 'none' стратегии для всех категорий"""
        return {
            key: info.none_strategy
            for key, info in self._categories.items()
        }
    
    def add_new_category(self, 
                        key: str,
                        short_name: str,
                        full_name: str,
                        strategies_dict: Dict,
                        emoji: str = "🔧",
                        description: str = "",
                        tooltip: str = "",
                        color: str = "#888888",
                        default_strategy: str = "",
                        none_strategy: str = "",
                        ports: str = "",
                        protocol: str = "",
                        order: int = 999,
                        command_order: int = 999,
                        needs_new_separator: bool = False,
                        command_group: str = "default",
                        icon_name: str = 'fa5s.globe',
                        icon_color: str = '#2196F3') -> bool:
        """
        Добавить новую категорию динамически
        """
        try:
            # Добавляем информацию о категории
            self._categories[key] = CategoryInfo(
                key=key,
                short_name=short_name,
                full_name=full_name,
                emoji=emoji,
                description=description,
                tooltip=tooltip,
                color=color,
                default_strategy=default_strategy,
                none_strategy=none_strategy,
                ports=ports,
                protocol=protocol,
                order=order,
                command_order=command_order,
                needs_new_separator=needs_new_separator,
                command_group=command_group,
                icon_name=icon_name,
                icon_color=icon_color
            )
            
            # Добавляем стратегии в кэш
            _strategies_cache[key] = strategies_dict
            _imported_categories.add(key)
            
            log(f"Добавлена новая категория: {key} ({full_name})", "INFO")
            return True
            
        except Exception as e:
            log(f"Ошибка добавления категории {key}: {e}", "❌ ERROR")
            return False
    
    def remove_category(self, key: str) -> bool:
        """Удалить категорию"""
        try:
            if key in self._categories:
                del self._categories[key]
            
            if key in _strategies_cache:
                del _strategies_cache[key]
                
            if key in _imported_categories:
                _imported_categories.remove(key)
            
            log(f"Удалена категория: {key}", "INFO")
            return True
            
        except Exception as e:
            log(f"Ошибка удаления категории {key}: {e}", "❌ ERROR")
            return False
    
    def get_strategy_safe(self, category_key: str, strategy_id: str) -> Optional[Dict]:
        """Безопасно получить стратегию"""
        try:
            category_strategies = self.get_category_strategies(category_key)
            return category_strategies.get(strategy_id)
        except Exception as e:
            log(f"Ошибка получения стратегии {strategy_id} из {category_key}: {e}", "⚠ WARNING")
            return None
    
    def get_strategy_args_safe(self, category_key: str, strategy_id: str) -> Optional[str]:
        """Безопасно получить аргументы стратегии"""
        strategy = self.get_strategy_safe(category_key, strategy_id)
        if strategy:
            return strategy.get("args", "")
        return None
    
    def get_strategy_name_safe(self, category_key: str, strategy_id: str) -> str:
        """Безопасно получить имя стратегии"""
        strategy = self.get_strategy_safe(category_key, strategy_id)
        if strategy:
            return strategy.get('name', strategy_id)
        return strategy_id or "Unknown"

    def get_all_category_keys_by_command_order(self) -> List[str]:
        """Получить все ключи категорий в порядке командной строки"""
        return sorted(self._categories.keys(), key=lambda k: self._categories[k].command_order)

    def get_command_groups(self) -> Dict[str, List[str]]:
        """Получить группы команд"""
        groups = {}
        for key, info in self._categories.items():
            group = info.command_group
            if group not in groups:
                groups[group] = []
            groups[group].append(key)
        
        # Сортируем категории в каждой группе по command_order
        for group in groups:
            groups[group].sort(key=lambda k: self._categories[k].command_order)
        
        return groups

    @staticmethod
    def get_category_icon(category_key: str):
        """Возвращает Font Awesome иконку для категории"""
        return get_category_icon(category_key)
    
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
    'registry',
    'get_strategies_registry',
    'get_category_strategies',
    'get_category_info', 
    'get_all_strategies',
    'get_tab_names',
    'get_tab_tooltips',
    'get_default_selections',
    'get_category_icon',
]
# strategy_menu/__init__.py

import winreg
import json
from log import log
from config import reg

REGISTRY_PATH = r"Software\ZapretReg2"
DIRECT_PATH = r"Software\ZapretReg2\DirectMethod"

def get_strategy_launch_method():
    """Получает метод запуска стратегий из реестра bat"""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH) as key:
            value, _ = winreg.QueryValueEx(key, "StrategyLaunchMethod")
            return value
    except:
        return "bat"

def set_strategy_launch_method(method: str):
    """Сохраняет метод запуска стратегий в реестр"""
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH) as key:
            winreg.SetValueEx(key, "StrategyLaunchMethod", 0, winreg.REG_SZ, method)
            log(f"Метод запуска стратегий изменен на: {method}", "INFO")
            return True
    except Exception as e:
        log(f"Ошибка сохранения метода запуска: {e}", "❌ ERROR")
        return False

# ───────────── Избранные стратегии ─────────────
def get_favorite_strategies():
    """Получает список ID избранных стратегий"""
    try:
        # Получаем строку из реестра
        result = reg(REGISTRY_PATH, "FavoriteStrategies")
        if result:
            # Десериализуем JSON строку в список
            return json.loads(result)
        return []
    except Exception as e:
        log(f"Ошибка загрузки избранных стратегий: {e}", "DEBUG")
        return []

def add_favorite_strategy(strategy_id):
    """Добавляет стратегию в избранные"""
    try:
        favorites = get_favorite_strategies()
        if strategy_id not in favorites:
            favorites.append(strategy_id)
            # Сериализуем список в JSON строку и сохраняем
            reg(REGISTRY_PATH, "FavoriteStrategies", json.dumps(favorites))
            log(f"Стратегия {strategy_id} добавлена в избранные", "DEBUG")
            return True
        return False
    except Exception as e:
        log(f"Ошибка добавления стратегии в избранные: {e}", "ERROR")
        return False

def remove_favorite_strategy(strategy_id):
    """Удаляет стратегию из избранных"""
    try:
        favorites = get_favorite_strategies()
        if strategy_id in favorites:
            favorites.remove(strategy_id)
            # Сериализуем список в JSON строку и сохраняем
            reg(REGISTRY_PATH, "FavoriteStrategies", json.dumps(favorites))
            log(f"Стратегия {strategy_id} удалена из избранных", "DEBUG")
            return True
        return False
    except Exception as e:
        log(f"Ошибка удаления стратегии из избранных: {e}", "ERROR")
        return False

def is_favorite_strategy(strategy_id):
    """Проверяет, является ли стратегия избранной"""
    favorites = get_favorite_strategies()
    return strategy_id in favorites

def toggle_favorite_strategy(strategy_id):
    """Переключает статус избранной стратегии"""
    if is_favorite_strategy(strategy_id):
        remove_favorite_strategy(strategy_id)
        return False
    else:
        add_favorite_strategy(strategy_id)
        return True

def clear_favorite_strategies():
    """Очищает список избранных стратегий"""
    try:
        reg(REGISTRY_PATH, "FavoriteStrategies", json.dumps([]))
        log("Список избранных стратегий очищен", "DEBUG")
        return True
    except Exception as e:
        log(f"Ошибка очистки избранных стратегий: {e}", "ERROR")
        return False

def get_tabs_pinned() -> bool:
    """Получает состояние закрепления боковой панели табов"""
    result = reg(DIRECT_PATH, "TabsPinned")
    if result is not None:
        try:
            return bool(int(result))
        except (ValueError, TypeError):
            return False
    return True

def set_tabs_pinned(pinned: bool) -> bool:
    """Сохраняет состояние закрепления боковой панели табов"""
    success = reg(DIRECT_PATH, "TabsPinned", int(pinned))
    if success:
        log(f"Настройка закрепления табов сохранена: {'закреплено' if pinned else 'не закреплено'}", "INFO")
    else:
        log(f"Ошибка сохранения настройки закрепления табов", "❌ ERROR")
    return success
        
# ───────────── Настройки прямого метода ─────────────

def get_base_args_selection() -> str:
    """Получает выбранный вариант базовых аргументов"""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, DIRECT_PATH) as key:
            value, _ = winreg.QueryValueEx(key, "BaseArgsSelection")
            return value
    except:
        return "windivert_all"

def set_base_args_selection(selection: str) -> bool:
    """Сохраняет выбранный вариант базовых аргументов"""
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, DIRECT_PATH) as key:
            winreg.SetValueEx(key, "BaseArgsSelection", 0, winreg.REG_SZ, selection)
            log(f"Базовые аргументы изменены на: {selection}", "INFO")
            return True
    except Exception as e:
        log(f"Ошибка сохранения базовых аргументов: {e}", "❌ ERROR")
        return False
    
def get_allzone_hostlist_enabled() -> bool:
    """Получает состояние настройки замены other.txt на allzone.txt"""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, DIRECT_PATH) as key:
            value, _ = winreg.QueryValueEx(key, "AllzoneHostlistEnabled")
            return bool(value)
    except:
        return False  # По умолчанию выключено

def get_game_filter_enabled() -> bool:
    """Получает состояние настройки Game Filter (расширение портов)"""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, DIRECT_PATH) as key:
            value, _ = winreg.QueryValueEx(key, "GameFilterEnabled")
            return bool(value)
    except:
        return True # По умолчанию включено

def get_wssize_enabled():
    """Получает настройку включения параметра --wssize из реестра"""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, DIRECT_PATH) as key:
            value, _ = winreg.QueryValueEx(key, "WSSizeEnabled")
            return bool(value)
    except:
        return False # По умолчанию выключено
    
def set_allzone_hostlist_enabled(enabled: bool):
    """Сохраняет состояние настройки замены other.txt на allzone.txt"""
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, DIRECT_PATH) as key:
            winreg.SetValueEx(key, "AllzoneHostlistEnabled", 0, winreg.REG_DWORD, int(enabled))
            log(f"Настройка allzone.txt сохранена: {enabled}", "INFO")
            return True
    except Exception as e:
        log(f"Ошибка сохранения настройки allzone.txt: {e}", "❌ ERROR")
        return False

def set_game_filter_enabled(enabled: bool):
    """Сохраняет состояние настройки Game Filter (расширение портов)"""
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, DIRECT_PATH) as key:
            winreg.SetValueEx(key, "GameFilterEnabled", 0, winreg.REG_DWORD, int(enabled))
            log(f"Настройка Game Filter сохранена: {enabled}", "INFO")
            return True
    except Exception as e:
        log(f"Ошибка сохранения настройки Game Filter: {e}", "❌ ERROR")
        return False

def set_wssize_enabled(enabled: bool):
    """Сохраняет настройку включения параметра --wssize в реестр"""
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, DIRECT_PATH) as key:
            winreg.SetValueEx(key, "WSSizeEnabled", 0, winreg.REG_DWORD, int(enabled))
            log(f"Настройка wssize_enabled сохранена: {enabled}", "INFO")
            return True
    except Exception as e:
        log(f"Ошибка сохранения настройки wssize_enabled: {e}", "❌ ERROR")
        return False
        

# ───────────── Выбранные стратегии для прямого запуска ─────────────
_DIRECT_STRATEGY_KEY = r"Software\ZapretReg2\DirectStrategy"
_DIRECT_YOUTUBE_NAME = "DirectStrategyYoutube"
_DIRECT_YOUTUBE_UDP_NAME = "DirectStrategyYoutubeUDP"
_DIRECT_GOOGLEVIDEO_NAME = "DirectStrategyGoogleVideo"
_DIRECT_DISCORD_NAME = "DirectStrategyDiscord"
_DIRECT_DISCORD_VOICE_NAME = "DirectStrategyDiscordVoice"
_DIRECT_RUTRACKER_TCP_NAME = "DirectStrategyRutrackerTcp"
_DIRECT_NTCPARTY_TCP_NAME = "DirectStrategyNtcPartyTcp"
_DIRECT_TWITCH_TCP_NAME = "DirectStrategyTwitchTCP"
_DIRECT_OTHER_NAME = "DirectStrategyOther"
_DIRECT_HOSTLIST_80PORT_NAME = "DirectStrategyHostlist80Port"
_DIRECT_IPSET_NAME = "DirectStrategyIpset"
_DIRECT_IPSET_UDP_NAME = "DirectStrategyIpsetUdp"
_DIRECT_phasmophobia_udp_NAME = "DirectStrategyRockstarLauncherTcp"

def get_direct_strategy_selections() -> dict:
    """Возвращает сохраненные выборы стратегий для прямого запуска"""
    try:
        youtube = reg(_DIRECT_STRATEGY_KEY, _DIRECT_YOUTUBE_NAME)
        youtube_udp = reg(_DIRECT_STRATEGY_KEY, _DIRECT_YOUTUBE_UDP_NAME)
        googlevideo_tcp = reg(_DIRECT_STRATEGY_KEY, _DIRECT_GOOGLEVIDEO_NAME)
        discord = reg(_DIRECT_STRATEGY_KEY, _DIRECT_DISCORD_NAME)
        discord_voice_udp = reg(_DIRECT_STRATEGY_KEY, _DIRECT_DISCORD_VOICE_NAME)
        rutracker_tcp = reg(_DIRECT_STRATEGY_KEY, _DIRECT_RUTRACKER_TCP_NAME)
        ntcparty_tcp = reg(_DIRECT_STRATEGY_KEY, _DIRECT_NTCPARTY_TCP_NAME)
        twitch_tcp = reg(_DIRECT_STRATEGY_KEY, _DIRECT_TWITCH_TCP_NAME)
        phasmophobia_udp = reg(_DIRECT_STRATEGY_KEY, _DIRECT_phasmophobia_udp_NAME)
        other = reg(_DIRECT_STRATEGY_KEY, _DIRECT_OTHER_NAME)
        hostlist_80port = reg(_DIRECT_STRATEGY_KEY, _DIRECT_HOSTLIST_80PORT_NAME)
        ipset = reg(_DIRECT_STRATEGY_KEY, _DIRECT_IPSET_NAME)
        ipset_udp = reg(_DIRECT_STRATEGY_KEY, _DIRECT_IPSET_UDP_NAME)
        
        # Возвращаем значения по умолчанию если что-то не найдено
        from strategy_menu.strategy_lists_separated import get_default_selections
        default_selections = get_default_selections()
        
        selections = {
            'youtube': youtube if youtube else default_selections.get('youtube'),
            'youtube_udp': youtube_udp if youtube_udp else default_selections.get('youtube_udp'),
            'googlevideo_tcp': googlevideo_tcp if googlevideo_tcp else default_selections.get('googlevideo_tcp'),
            'discord': discord if discord else default_selections.get('discord'),
            'discord_voice_udp': discord_voice_udp if discord_voice_udp else default_selections.get('discord_voice_udp'),
            'rutracker_tcp': rutracker_tcp if rutracker_tcp else default_selections.get('rutracker_tcp'),
            'ntcparty_tcp': ntcparty_tcp if ntcparty_tcp else default_selections.get('ntcparty_tcp'),
            'twitch_tcp': twitch_tcp if twitch_tcp else default_selections.get('twitch_tcp'),
            'phasmophobia_udp': phasmophobia_udp if phasmophobia_udp else default_selections.get('phasmophobia_udp'),
            'other': other if other else default_selections.get('other'),
            'hostlist_80port': hostlist_80port if hostlist_80port else default_selections.get('hostlist_80port'),
            'ipset': ipset if ipset else default_selections.get('ipset'),
            'ipset_udp': ipset_udp if ipset_udp else default_selections.get('ipset_udp'),
        }
        
        log(f"Загружены выборы стратегий из реестра: {selections}", "DEBUG")
        return selections
        
    except Exception as e:
        log(f"Ошибка загрузки выборов стратегий: {e}", "❌ ERROR")
        # Возвращаем значения по умолчанию
        from strategy_menu.strategy_lists_separated import get_default_selections
        return get_default_selections()

def set_direct_strategy_selections(selections: dict) -> bool:
    """Сохраняет выборы стратегий для прямого запуска в реестр"""
    try:
        success = True
        
        if 'youtube' in selections:
            success &= reg(_DIRECT_STRATEGY_KEY, _DIRECT_YOUTUBE_NAME, selections['youtube'])

        if 'youtube_udp' in selections:
            success &= reg(_DIRECT_STRATEGY_KEY, _DIRECT_YOUTUBE_UDP_NAME, selections['youtube_udp'])

        if 'googlevideo_tcp' in selections:
            success &= reg(_DIRECT_STRATEGY_KEY, _DIRECT_GOOGLEVIDEO_NAME, selections['googlevideo_tcp'])
        
        if 'discord' in selections:
            success &= reg(_DIRECT_STRATEGY_KEY, _DIRECT_DISCORD_NAME, selections['discord'])
        
        if 'discord_voice_udp' in selections:
            success &= reg(_DIRECT_STRATEGY_KEY, _DIRECT_DISCORD_VOICE_NAME, selections['discord_voice_udp'])

        if 'rutracker_tcp' in selections:
            success &= reg(_DIRECT_STRATEGY_KEY, _DIRECT_RUTRACKER_TCP_NAME, selections['rutracker_tcp'])

        if 'ntcparty_tcp' in selections:
            success &= reg(_DIRECT_STRATEGY_KEY, _DIRECT_NTCPARTY_TCP_NAME, selections['ntcparty_tcp'])

        if 'twitch_tcp' in selections:
            success &= reg(_DIRECT_STRATEGY_KEY, _DIRECT_TWITCH_TCP_NAME, selections['twitch_tcp'])

        if 'phasmophobia_udp' in selections:
            success &= reg(_DIRECT_STRATEGY_KEY, _DIRECT_phasmophobia_udp_NAME, selections['phasmophobia_udp'])

        if 'other' in selections:
            success &= reg(_DIRECT_STRATEGY_KEY, _DIRECT_OTHER_NAME, selections['other'])

        if 'hostlist_80port' in selections:
            success &= reg(_DIRECT_STRATEGY_KEY, _DIRECT_HOSTLIST_80PORT_NAME, selections['hostlist_80port'])

        if 'ipset' in selections:
            success &= reg(_DIRECT_STRATEGY_KEY, _DIRECT_IPSET_NAME, selections['ipset'])

        if 'ipset_udp' in selections:
            success &= reg(_DIRECT_STRATEGY_KEY, _DIRECT_IPSET_UDP_NAME, selections['ipset_udp'])
        
        if success:
            log(f"Сохранены выборы стратегий в реестр: {selections}", "DEBUG")
        else:
            log("Ошибка при сохранении некоторых выборов стратегий", "⚠ WARNING")
            
        return success
        
    except Exception as e:
        log(f"Ошибка сохранения выборов стратегий: {e}", "❌ ERROR")
        return False

def get_direct_strategy_youtube() -> str:
    """Возвращает сохраненную YouTube стратегию"""
    result = reg(_DIRECT_STRATEGY_KEY, _DIRECT_YOUTUBE_NAME)
    if result:
        return result
    
    # Значение по умолчанию
    from strategy_menu.strategy_lists_separated import get_default_selections
    return get_default_selections().get('youtube', 'multisplit_seqovl_midsld')

def set_direct_strategy_youtube(strategy_id: str) -> bool:
    """Сохраняет выбранную YouTube стратегию"""
    return reg(_DIRECT_STRATEGY_KEY, _DIRECT_YOUTUBE_NAME, strategy_id)

def get_direct_strategy_youtube_udp() -> str:
    """Возвращает сохраненную YouTube UDP (QUIC) стратегию"""
    result = reg(_DIRECT_STRATEGY_KEY, _DIRECT_YOUTUBE_UDP_NAME)
    if result:
        return result
    
    # Значение по умолчанию
    from strategy_menu.strategy_lists_separated import get_default_selections
    return get_default_selections().get('youtube_udp', 'fake_11')

def set_direct_strategy_youtube_udp(strategy_id: str) -> bool:
    """Сохраняет выбранную YouTube UDP (QUIC) стратегию"""
    return reg(_DIRECT_STRATEGY_KEY, _DIRECT_YOUTUBE_UDP_NAME, strategy_id)

def get_direct_strategy_googlevideo() -> str:
    """Возвращает сохраненную GoogleVideo стратегию"""
    result = reg(_DIRECT_STRATEGY_KEY, _DIRECT_GOOGLEVIDEO_NAME)
    if result:
        return result
    
    # Значение по умолчанию
    from strategy_menu.strategy_lists_separated import get_default_selections
    return get_default_selections().get('googlevideo_tcp', 'googlevideo_tcp_none')

def set_direct_strategy_googlevideo(strategy_id: str) -> bool:
    """Сохраняет выбранную GoogleVideo стратегию"""
    return reg(_DIRECT_STRATEGY_KEY, _DIRECT_GOOGLEVIDEO_NAME, strategy_id)

def get_direct_strategy_discord() -> str:
    """Возвращает сохраненную Discord стратегию"""
    result = reg(_DIRECT_STRATEGY_KEY, _DIRECT_DISCORD_NAME)
    if result:
        return result
    
    # Значение по умолчанию
    from strategy_menu.strategy_lists_separated import get_default_selections
    return get_default_selections().get('discord', 'dis4')

def set_direct_strategy_discord(strategy_id: str) -> bool:
    """Сохраняет выбранную Discord стратегию"""
    return reg(_DIRECT_STRATEGY_KEY, _DIRECT_DISCORD_NAME, strategy_id)

def get_direct_strategy_discord_voice() -> str:
    """Возвращает сохраненную Discord Voice стратегию"""
    result = reg(_DIRECT_STRATEGY_KEY, _DIRECT_DISCORD_VOICE_NAME)
    if result:
        return result
    
    # Значение по умолчанию
    from strategy_menu.strategy_lists_separated import get_default_selections
    return get_default_selections().get('discord_voice_udp', 'ipv4_dup2_autottl_cutoff_n3')

def set_direct_strategy_discord_voice(strategy_id: str) -> bool:
    """Сохраняет выбранную Discord Voice стратегию"""
    return reg(_DIRECT_STRATEGY_KEY, _DIRECT_DISCORD_VOICE_NAME, strategy_id)

def get_direct_strategy_rutracker_tcp() -> str:
    """Возвращает сохраненную Rutracker TCP стратегию"""
    result = reg(_DIRECT_STRATEGY_KEY, _DIRECT_RUTRACKER_TCP_NAME)
    if result:
        return result
    
    # Значение по умолчанию
    from strategy_menu.strategy_lists_separated import get_default_selections
    return get_default_selections().get('rutracker_tcp', 'multisplit_split_pos_1')

def set_direct_strategy_rutracker_tcp(strategy_id: str) -> bool:
    """Сохраняет выбранную Rutracker TCP стратегию"""
    return reg(_DIRECT_STRATEGY_KEY, _DIRECT_RUTRACKER_TCP_NAME, strategy_id)

def get_direct_strategy_ntcparty_tcp() -> str:
    """Возвращает сохраненную NtcParty TCP стратегию"""
    result = reg(_DIRECT_STRATEGY_KEY, _DIRECT_NTCPARTY_TCP_NAME)
    if result:
        return result
    
    # Значение по умолчанию
    from strategy_menu.strategy_lists_separated import get_default_selections
    return get_default_selections().get('ntcparty_tcp', 'other_seqovl')

def set_direct_strategy_ntcparty_tcp(strategy_id: str) -> bool:
    """Сохраняет выбранную NtcParty TCP стратегию"""
    return reg(_DIRECT_STRATEGY_KEY, _DIRECT_NTCPARTY_TCP_NAME, strategy_id)

def get_direct_strategy_twitch_tcp() -> str:
    """Возвращает сохраненную Twitch TCP стратегию"""
    result = reg(_DIRECT_STRATEGY_KEY, _DIRECT_TWITCH_TCP_NAME)
    if result:
        return result
    
    # Значение по умолчанию
    from strategy_menu.strategy_lists_separated import get_default_selections
    return get_default_selections().get('twitch_tcp', 'twitch_tcp_none')

def set_direct_strategy_twitch_tcp(strategy_id: str) -> bool:
    """Сохраняет выбранную Twitch TCP стратегию"""
    return reg(_DIRECT_STRATEGY_KEY, _DIRECT_TWITCH_TCP_NAME, strategy_id)

def get_direct_strategy_phasmophobia_udp() -> str:
    """Возвращает сохраненную Phasmophobia UDP стратегию"""
    result = reg(_DIRECT_STRATEGY_KEY, _DIRECT_phasmophobia_udp_NAME)
    if result:
        return result
    
    # Значение по умолчанию
    from strategy_menu.strategy_lists_separated import get_default_selections
    return get_default_selections().get('phasmophobia_udp', 'fake_2_n2_google')

def set_direct_strategy_phasmophobia_udp(strategy_id: str) -> bool:
    """Сохраняет выбранную Phasmophobia UDP стратегию"""
    return reg(_DIRECT_STRATEGY_KEY, _DIRECT_phasmophobia_udp_NAME, strategy_id)

def get_direct_strategy_other() -> str:
    """Возвращает сохраненную стратегию для остальных сайтов"""
    result = reg(_DIRECT_STRATEGY_KEY, _DIRECT_OTHER_NAME)
    if result:
        return result
    
    # Значение по умолчанию
    from strategy_menu.strategy_lists_separated import get_default_selections
    return get_default_selections().get('other', 'other_seqovl')

def set_direct_strategy_other(strategy_id: str) -> bool:
    """Сохраняет выбранную стратегию для остальных сайтов"""
    return reg(_DIRECT_STRATEGY_KEY, _DIRECT_OTHER_NAME, strategy_id)

def get_direct_strategy_hostlist_80port() -> str:
    """Возвращает сохраненную стратегию для hostlist_80port"""
    result = reg(_DIRECT_STRATEGY_KEY, _DIRECT_HOSTLIST_80PORT_NAME)
    if result:
        return result
    
    # Значение по умолчанию
    from strategy_menu.strategy_lists_separated import get_default_selections
    return get_default_selections().get('hostlist_80port', 'fake_multisplit_2_fake_http')

def set_direct_strategy_hostlist_80port(strategy_id: str) -> bool:
    """Сохраняет выбранную стратегию для hostlist_80port"""
    return reg(_DIRECT_STRATEGY_KEY, _DIRECT_HOSTLIST_80PORT_NAME, strategy_id)

def get_direct_strategy_ipset() -> str:
    """Возвращает сохраненную IPset стратегию"""
    result = reg(_DIRECT_STRATEGY_KEY, _DIRECT_IPSET_NAME)
    if result:
        return result
    
    # Значение по умолчанию
    from strategy_menu.strategy_lists_separated import get_default_selections
    return get_default_selections().get('ipset', 'other_seqovl')

def set_direct_strategy_ipset(strategy_id: str) -> bool:
    """Сохраняет выбранную IPset стратегию"""
    return reg(_DIRECT_STRATEGY_KEY, _DIRECT_IPSET_NAME, strategy_id)

def get_direct_strategy_udp_ipset() -> str:
    """Возвращает сохраненную UDP IPset стратегию"""
    result = reg(_DIRECT_STRATEGY_KEY, "DirectStrategyUdpIpset")
    if result:
        return result
    
    # Значение по умолчанию
    from strategy_menu.strategy_lists_separated import get_default_selections
    return get_default_selections().get('ipset_udp', 'fake_2_n2_google')

def set_direct_strategy_udp_ipset(strategy_id: str) -> bool:
    """Сохраняет выбранную UDP IPset стратегию"""
    return reg(_DIRECT_STRATEGY_KEY, "DirectStrategyUdpIpset", strategy_id)

from .RUTRACKER_TCP_STRATEGIES import RUTRACKER_TCP_STRATEGIES
from .NTCPARTY_TCP_STRATEGIES import NTCPARTY_TCP_STRATEGIES
from .OTHER_STRATEGIES import OTHER_STRATEGIES
from .TWITCH_TCP_STRATEGIES import TWITCH_TCP_STRATEGIES
from .YOUTUBE_TCP_STRATEGIES import YOUTUBE_TCP_STRATEGIES
from .IPSET_TCP_STRATEGIES import IPSET_TCP_STRATEGIES
from .IPSET_UDP_STRATEGIES import IPSET_UDP_STRATEGIES
from .GOOGLEVIDEO_TCP_STRATEGIES import GOOGLEVIDEO_STRATEGIES
from .PHASMOPHOBIA_UDP_STRATEGIES import PHASMOPHOBIA_UDP_STRATEGIES
from .HOSTLIST_80PORT_STRATEGIES import HOSTLIST_80PORT_STRATEGIES


all = [
    'GOOGLEVIDEO_STRATEGIES',
    'OTHER_STRATEGIES',
    'RUTRACKER_TCP_STRATEGIES',
    'NTCPARTY_TCP_STRATEGIES',
    'TWITCH_TCP_STRATEGIES',
    'YOUTUBE_TCP_STRATEGIES',
    'IPSET_TCP_STRATEGIES',
    'IPSET_UDP_STRATEGIES',
    'PHASMOPHOBIA_UDP_STRATEGIES',
    'HOSTLIST_80PORT_STRATEGIES',
    'get_tabs_pinned',
    'set_tabs_pinned',
]
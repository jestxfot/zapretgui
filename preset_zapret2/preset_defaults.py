# preset_zapret2/preset_defaults.py
"""
Built-in default preset template.

This file contains the default preset content as a Python constant,
which allows us to:
1. Always restore default.txt from code (no external file dependency)
2. Guarantee that default.txt is never corrupted
3. Provide a recovery mechanism for users

The content is copied to:
- presets/Default.txt (for preset list)
- preset-zapret2.txt (when Default is active)
"""

from typing import Optional

DEFAULT_PRESET_CONTENT = r"""# Preset: Default
# ActivePreset: Default

--lua-init=@lua/zapret-lib.lua
--lua-init=@lua/zapret-antidpi.lua
--lua-init=@lua/zapret-auto.lua
--lua-init=@lua/custom_funcs.lua
--ipcache-lifetime=8400
--ipcache-hostname=1 
--wf-tcp-out=80,443,1080,2053,2083,2087,2096,8443
--wf-udp-out=80,443
--wf-raw-part=@windivert.filter/windivert_part.discord_media.txt
--wf-raw-part=@windivert.filter/windivert_part.stun.txt
--wf-raw-part=@windivert.filter/windivert_part.wireguard.txt
--blob=tls_google:@bin/tls_clienthello_www_google_com.bin
--blob=tls1:@bin/tls_clienthello_1.bin
--blob=tls2:@bin/tls_clienthello_2.bin
--blob=tls2n:@bin/tls_clienthello_2n.bin
--blob=tls3:@bin/tls_clienthello_3.bin
--blob=tls4:@bin/tls_clienthello_4.bin
--blob=tls5:@bin/tls_clienthello_5.bin
--blob=tls6:@bin/tls_clienthello_6.bin
--blob=tls7:@bin/tls_clienthello_7.bin
--blob=tls8:@bin/tls_clienthello_8.bin
--blob=tls9:@bin/tls_clienthello_9.bin
--blob=tls10:@bin/tls_clienthello_10.bin
--blob=tls11:@bin/tls_clienthello_11.bin
--blob=tls12:@bin/tls_clienthello_12.bin
--blob=tls13:@bin/tls_clienthello_13.bin
--blob=tls14:@bin/tls_clienthello_14.bin
--blob=tls17:@bin/tls_clienthello_17.bin
--blob=tls18:@bin/tls_clienthello_18.bin
--blob=tls_sber:@bin/tls_clienthello_sberbank_ru.bin
--blob=tls_vk:@bin/tls_clienthello_vk_com.bin
--blob=tls_vk_kyber:@bin/tls_clienthello_vk_com_kyber.bin
--blob=tls_deepseek:@bin/tls_clienthello_chat_deepseek_com.bin
--blob=tls_max:@bin/tls_clienthello_max_ru.bin
--blob=tls_iana:@bin/tls_clienthello_iana_org.bin
--blob=tls_4pda:@bin/tls_clienthello_4pda_to.bin
--blob=tls_gosuslugi:@bin/tls_clienthello_gosuslugi_ru.bin
--blob=syndata3:@bin/tls_clienthello_3.bin
--blob=syn_packet:@bin/syn_packet.bin
--blob=dtls_w3:@bin/dtls_clienthello_w3_org.bin
--blob=quic_google:@bin/quic_initial_www_google_com.bin
--blob=quic_vk:@bin/quic_initial_vk_com.bin
--blob=quic1:@bin/quic_1.bin
--blob=quic2:@bin/quic_2.bin
--blob=quic3:@bin/quic_3.bin
--blob=quic4:@bin/quic_4.bin
--blob=quic5:@bin/quic_5.bin
--blob=quic6:@bin/quic_6.bin
--blob=quic7:@bin/quic_7.bin
--blob=quic_test:@bin/quic_test_00.bin
--blob=fake_tls:@bin/fake_tls_1.bin
--blob=fake_tls_1:@bin/fake_tls_1.bin
--blob=fake_tls_2:@bin/fake_tls_2.bin
--blob=fake_tls_3:@bin/fake_tls_3.bin
--blob=fake_tls_4:@bin/fake_tls_4.bin
--blob=fake_tls_5:@bin/fake_tls_5.bin
--blob=fake_tls_6:@bin/fake_tls_6.bin
--blob=fake_tls_7:@bin/fake_tls_7.bin
--blob=fake_tls_8:@bin/fake_tls_8.bin
--blob=fake_quic:@bin/fake_quic.bin
--blob=fake_quic_1:@bin/fake_quic_1.bin
--blob=fake_quic_2:@bin/fake_quic_2.bin
--blob=fake_quic_3:@bin/fake_quic_3.bin
--blob=fake_default_udp:0x00000000000000000000000000000000
--blob=http_req:@bin/http_iana_org.bin
--blob=hex_0e0e0f0e:0x0E0E0F0E
--blob=hex_0f0e0e0f:0x0F0E0E0F
--blob=hex_0f0f0f0f:0x0F0F0F0F
--blob=hex_00:0x00

--filter-tcp=80,443
--ipset=lists/ipset-youtube.txt
--out-range=-n8
--lua-desync=send:repeats=2
--lua-desync=syndata:blob=tls_google:ip_autottl=-2,3-20
--lua-desync=multidisorder_legacy:pos=1,midsld

--new

--filter-udp=443
--ipset=lists/ipset-youtube.txt
--out-range=-n8
--payload=all
--lua-desync=fake:repeats=6:blob=fake_default_quic

--new

--filter-tcp=80,443,1080,2053,2083,2087,2096,8443
--ipset=lists/ipset-discord.txt
--out-range=-n8
--lua-desync=send:repeats=2
--lua-desync=syndata:blob=tls_google:ip_autottl=-2,3-20
--lua-desync=multidisorder_legacy:pos=1,midsld

--new

--filter-l7=stun,discord
--payload=stun,discord_ip_discovery
--out-range=-n8
--lua-desync=fake:blob=quic_google:ip_autottl=-2,3-20:ip6_autottl=-2,3-20:payload=all:repeats=10

--new

--filter-tcp=80,443
--ipset=lists/ipset-telegram.txt
--out-range=-n8
--lua-desync=send:repeats=2
--lua-desync=syndata:blob=tls_google:ip_autottl=-2,3-20
--lua-desync=pass

--new

--filter-tcp=80,443
--ipset-ip=130.255.77.28
--out-range=-n20
--lua-desync=send:repeats=2
--lua-desync=syndata:blob=tls_google:ip_autottl=-2,3-20
--lua-desync=fake:blob=tls14:tcp_ack=-66000:tcp_ts_up:ip_autottl=-1,3-20:ip6_autottl=-1,3-20:tls_mod=rnd,dupsid,sni=fonts.google.com
--lua-desync=multidisorder:pos=7,sld+1:tcp_ack=-66000:tcp_ts_up:ip_autottl=-1,3-20:ip6_autottl=-1,3-20
"""

GAMING_PRESET_CONTENT = r"""# Preset: Gaming
# ActivePreset: Gaming

--lua-init=@lua/zapret-lib.lua
--lua-init=@lua/zapret-antidpi.lua
--lua-init=@lua/zapret-auto.lua
--lua-init=@lua/custom_funcs.lua
--ipcache-lifetime=8400
--ipcache-hostname=1 
--wf-tcp-out=80,444-65535
--wf-udp-out=80,444-65535
--wf-raw-part=@windivert.filter/windivert_part.discord_media.txt
--wf-raw-part=@windivert.filter/windivert_part.stun.txt
--wf-raw-part=@windivert.filter/windivert_part.wireguard.txt
--blob=tls_google:@bin/tls_clienthello_www_google_com.bin
--blob=tls1:@bin/tls_clienthello_1.bin
--blob=tls2:@bin/tls_clienthello_2.bin
--blob=tls2n:@bin/tls_clienthello_2n.bin
--blob=tls3:@bin/tls_clienthello_3.bin
--blob=tls4:@bin/tls_clienthello_4.bin
--blob=tls5:@bin/tls_clienthello_5.bin
--blob=tls6:@bin/tls_clienthello_6.bin
--blob=tls7:@bin/tls_clienthello_7.bin
--blob=tls8:@bin/tls_clienthello_8.bin
--blob=tls9:@bin/tls_clienthello_9.bin
--blob=tls10:@bin/tls_clienthello_10.bin
--blob=tls11:@bin/tls_clienthello_11.bin
--blob=tls12:@bin/tls_clienthello_12.bin
--blob=tls13:@bin/tls_clienthello_13.bin
--blob=tls14:@bin/tls_clienthello_14.bin
--blob=tls17:@bin/tls_clienthello_17.bin
--blob=tls18:@bin/tls_clienthello_18.bin
--blob=tls_sber:@bin/tls_clienthello_sberbank_ru.bin
--blob=tls_vk:@bin/tls_clienthello_vk_com.bin
--blob=tls_vk_kyber:@bin/tls_clienthello_vk_com_kyber.bin
--blob=tls_deepseek:@bin/tls_clienthello_chat_deepseek_com.bin
--blob=tls_max:@bin/tls_clienthello_max_ru.bin
--blob=tls_iana:@bin/tls_clienthello_iana_org.bin
--blob=tls_4pda:@bin/tls_clienthello_4pda_to.bin
--blob=tls_gosuslugi:@bin/tls_clienthello_gosuslugi_ru.bin
--blob=syndata3:@bin/tls_clienthello_3.bin
--blob=syn_packet:@bin/syn_packet.bin
--blob=dtls_w3:@bin/dtls_clienthello_w3_org.bin
--blob=quic_google:@bin/quic_initial_www_google_com.bin
--blob=quic_vk:@bin/quic_initial_vk_com.bin
--blob=quic1:@bin/quic_1.bin
--blob=quic2:@bin/quic_2.bin
--blob=quic3:@bin/quic_3.bin
--blob=quic4:@bin/quic_4.bin
--blob=quic5:@bin/quic_5.bin
--blob=quic6:@bin/quic_6.bin
--blob=quic7:@bin/quic_7.bin
--blob=quic_test:@bin/quic_test_00.bin
--blob=fake_tls:@bin/fake_tls_1.bin
--blob=fake_tls_1:@bin/fake_tls_1.bin
--blob=fake_tls_2:@bin/fake_tls_2.bin
--blob=fake_tls_3:@bin/fake_tls_3.bin
--blob=fake_tls_4:@bin/fake_tls_4.bin
--blob=fake_tls_5:@bin/fake_tls_5.bin
--blob=fake_tls_6:@bin/fake_tls_6.bin
--blob=fake_tls_7:@bin/fake_tls_7.bin
--blob=fake_tls_8:@bin/fake_tls_8.bin
--blob=fake_quic:@bin/fake_quic.bin
--blob=fake_quic_1:@bin/fake_quic_1.bin
--blob=fake_quic_2:@bin/fake_quic_2.bin
--blob=fake_quic_3:@bin/fake_quic_3.bin
--blob=fake_default_udp:0x00000000000000000000000000000000
--blob=http_req:@bin/http_iana_org.bin
--blob=hex_0e0e0f0e:0x0E0E0F0E
--blob=hex_0f0e0e0f:0x0F0E0E0F
--blob=hex_0f0f0f0f:0x0F0F0F0F
--blob=hex_00:0x00

--filter-tcp=80,443
--ipset=lists/ipset-youtube.txt
--out-range=-n8
--lua-desync=send:repeats=2
--lua-desync=syndata:blob=tls_google:ip_autottl=-2,3-20
--lua-desync=multidisorder_legacy:pos=1,midsld

--new

--filter-udp=443
--ipset=lists/ipset-youtube.txt
--out-range=-n8
--payload=all
--lua-desync=fake:repeats=6:blob=fake_default_quic

--new

--filter-tcp=80,443,1080,2053,2083,2087,2096,8443
--ipset=lists/ipset-discord.txt
--out-range=-n8
--lua-desync=send:repeats=2
--lua-desync=syndata:blob=tls_google:ip_autottl=-2,3-20
--lua-desync=multidisorder_legacy:pos=1,midsld

--new

--filter-l7=stun,discord
--payload=stun,discord_ip_discovery
--out-range=-n8
--lua-desync=fake:blob=quic_google:ip_autottl=-2,3-20:ip6_autottl=-2,3-20:payload=all:repeats=10

--new

--filter-tcp=80,443
--ipset=lists/ipset-telegram.txt
--out-range=-n8
--lua-desync=send:repeats=2
--lua-desync=syndata:blob=tls_google:ip_autottl=-2,3-20
--lua-desync=pass

--new

--filter-tcp=80,443
--ipset-ip=130.255.77.28
--out-range=-n20
--lua-desync=send:repeats=2
--lua-desync=syndata:blob=tls_google:ip_autottl=-2,3-20
--lua-desync=fake:blob=tls14:tcp_ack=-66000:tcp_ts_up:ip_autottl=-1,3-20:ip6_autottl=-1,3-20:tls_mod=rnd,dupsid,sni=fonts.google.com
--lua-desync=multidisorder:pos=7,sld+1:tcp_ack=-66000:tcp_ts_up:ip_autottl=-1,3-20:ip6_autottl=-1,3-20

--new

--filter-tcp=80,443
--hostlist=lists/roblox.txt
--out-range=-n8
--lua-desync=send:repeats=2
--lua-desync=syndata:blob=tls_google:ip_autottl=-2,3-20
--lua-desync=fake:blob=tls_google:tcp_ts=1:repeats=8:payload=tls_client_hello
--lua-desync=multisplit:pos=1:seqovl=681:seqovl_pattern=tls_google:payload=tls_client_hello

--new

--filter-udp=443,49152-65535
--ipset=lists/ipset-roblox.txt
--out-range=-n8
--payload=all
--lua-desync=fake:blob=quic_google:ip_autottl=-2,3-20:ip6_autottl=-2,3-20:payload=all:repeats=10

--new

--filter-tcp=80,443-65535
--ipset=lists/russia-youtube-rtmps.txt
--ipset=lists/ipset-all.txt
--ipset=lists/ipset-base.txt
--ipset=lists/ipset-discord.txt
--ipset-exclude=lists/ipset-dns.txt
--out-range=-n8
--lua-desync=send:repeats=2
--lua-desync=syndata:blob=tls_google:ip_autottl=-2,3-20
--lua-desync=multisplit:seqovl=700:seqovl_pattern=tls_google:tcp_flags_unset=ack

--new

--filter-udp=*
--ipset=lists/ipset-all.txt
--ipset=lists/ipset-base.txt
--ipset=lists/cloudflare-ipset.txt
--ipset=lists/ipset-cloudflare1.txt
--ipset=lists/ipset-cloudflare.txt
--ipset-exclude=lists/ipset-dns.txt
--out-range=-n8
--payload=all
--lua-desync=fake:blob=quic_google:ip_autottl=-2,3-20:ip6_autottl=-2,3-20:payload=all:repeats=10
"""


BUILTIN_PRESET_TEMPLATES: dict[str, str] = {
    "Default": DEFAULT_PRESET_CONTENT,
    "Gaming": GAMING_PRESET_CONTENT,
}

_BUILTIN_PRESET_TEMPLATE_BY_KEY: dict[str, str] = {
    canonical.lower(): content for canonical, content in BUILTIN_PRESET_TEMPLATES.items()
}

_BUILTIN_PRESET_CANONICAL_NAME_BY_KEY: dict[str, str] = {
    canonical.lower(): canonical for canonical in BUILTIN_PRESET_TEMPLATES.keys()
}


def get_builtin_preset_content(name: str) -> Optional[str]:
    key = (name or "").strip().lower()
    if not key:
        return None
    return _BUILTIN_PRESET_TEMPLATE_BY_KEY.get(key)


def get_builtin_preset_canonical_name(name: str) -> Optional[str]:
    key = (name or "").strip().lower()
    if not key:
        return None
    return _BUILTIN_PRESET_CANONICAL_NAME_BY_KEY.get(key)


def is_builtin_preset_name(name: str) -> bool:
    return get_builtin_preset_canonical_name(name) is not None


# ═══════════════════════════════════════════════════════════════════════════════
# DEFAULT SETTINGS PARSER
# ═══════════════════════════════════════════════════════════════════════════════

_DEFAULT_SETTINGS_CACHE = None


def get_default_category_settings() -> dict:
    """
    Парсит DEFAULT_PRESET_CONTENT и возвращает дефолтные настройки для всех категорий.

    Возвращает словарь вида:
    {
        "youtube": {
            "filter_mode": "hostlist",
            "tcp_enabled": True,
            "tcp_port": "80,443",
            "tcp_args": "--lua-desync=multidisorder_legacy:pos=1,midsld",
            "udp_enabled": False,
        },
        "YouTube QUIC": {
            "filter_mode": "ipset",
            "tcp_enabled": False,
            "udp_enabled": True,
            "udp_port": "443",
            "udp_args": "--lua-desync=multidisorder_legacy:pos=1,midsld",
        },
        ...
    }

    Кэширует результат при первом вызове.

    Returns:
        dict: Словарь с дефолтными настройками категорий
    """
    global _DEFAULT_SETTINGS_CACHE

    # Возвращаем из кэша если уже парсили
    if _DEFAULT_SETTINGS_CACHE is not None:
        return _DEFAULT_SETTINGS_CACHE

    from .txt_preset_parser import parse_preset_content

    try:
        # Парсим DEFAULT_PRESET_CONTENT
        preset_data = parse_preset_content(DEFAULT_PRESET_CONTENT)

        # Конвертируем CategoryBlock в удобный формат
        settings = {}

        for block in preset_data.categories:
            category_name = block.category

            if category_name not in settings:
                settings[category_name] = {
                    "filter_mode": block.filter_mode,
                    "tcp_enabled": False,
                    "tcp_port": "",
                    "tcp_args": "",
                    "udp_enabled": False,
                    "udp_port": "",
                    "udp_args": "",
                    # Parsed per-protocol overrides from DEFAULT_PRESET_CONTENT.
                    # Keys are compatible with SyndataSettings.from_dict().
                    "syndata_overrides_tcp": {},
                    "syndata_overrides_udp": {},
                }

            cat_settings = settings[category_name]

            # Merge per-protocol overrides (if any) from the block.
            # NOTE: txt_preset_parser extracts these separately from strategy_args,
            # so we must take them from block.syndata_dict.
            overrides = getattr(block, "syndata_dict", None) or {}
            if overrides:
                target = "syndata_overrides_tcp" if block.protocol == "tcp" else "syndata_overrides_udp"
                cat_settings[target].update(overrides)

            # Записываем настройки по протоколу
            if block.protocol == "tcp":
                cat_settings["tcp_enabled"] = True
                cat_settings["tcp_port"] = block.port
                cat_settings["tcp_args"] = block.strategy_args
                # TCP filter_mode имеет приоритет (обычно hostlist)
                cat_settings["filter_mode"] = block.filter_mode
            elif block.protocol == "udp":
                cat_settings["udp_enabled"] = True
                cat_settings["udp_port"] = block.port
                cat_settings["udp_args"] = block.strategy_args
                # Обновляем filter_mode для UDP только если TCP нет
                if not cat_settings["tcp_enabled"]:
                    cat_settings["filter_mode"] = block.filter_mode

        # Кэшируем результат
        _DEFAULT_SETTINGS_CACHE = settings
        return settings

    except Exception as e:
        # Если парсинг не удался, возвращаем пустой словарь
        from log import log
        log(f"Failed to parse DEFAULT_PRESET_CONTENT: {e}", "ERROR")
        return {}


def get_category_default_filter_mode(category_name: str) -> str:
    """
    Возвращает дефолтный filter_mode для категории из DEFAULT_PRESET_CONTENT.

    Args:
        category_name: Имя категории (например "youtube", "YouTube QUIC")

    Returns:
        str: "hostlist", "ipset" или "hostlist" (fallback)
    """
    settings = get_default_category_settings()

    if category_name in settings:
        return settings[category_name].get("filter_mode", "hostlist")

    # Fallback: hostlist
    return "hostlist"


def parse_syndata_from_args(args_str: str) -> dict:
    """
    Парсит syndata настройки из строки аргументов.

    Извлекает параметры из строк вида:
    - --lua-desync=send:repeats=2:ttl=0
    - --lua-desync=syndata:blob=tls_google:ip_autottl=-2,3-20
    - --out-range=-n8

    Args:
        args_str: Строка с аргументами (может содержать несколько строк)

    Returns:
        dict: Словарь с параметрами syndata/send/out_range
    """
    result = {
        "enabled": False,
        "blob": "tls_google",
        "tls_mod": "none",
        "autottl_delta": 0,
        "autottl_min": 3,
        "autottl_max": 20,
        "tcp_flags_unset": "none",
        "out_range": 0,
        "out_range_mode": "n",
        "send_enabled": False,
        "send_repeats": 0,
        "send_ip_ttl": 0,
        "send_ip6_ttl": 0,
        "send_ip_id": "none",
        "send_badsum": False,
    }

    import re

    # Парсим --lua-desync=syndata:...
    syndata_match = re.search(r'--lua-desync=syndata:([^\n]+)', args_str)
    if syndata_match:
        result["enabled"] = True
        syndata_str = syndata_match.group(1)

        # blob=tls_google
        blob_match = re.search(r'blob=([^:]+)', syndata_str)
        if blob_match:
            result["blob"] = blob_match.group(1)

        # ip_autottl=-2,3-20
        autottl_match = re.search(r'ip_autottl=(-?\d+),(\d+)-(\d+)', syndata_str)
        if autottl_match:
            result["autottl_delta"] = int(autottl_match.group(1))
            result["autottl_min"] = int(autottl_match.group(2))
            result["autottl_max"] = int(autottl_match.group(3))

        # tls_mod=...
        tls_mod_match = re.search(r'tls_mod=([^:]+)', syndata_str)
        if tls_mod_match:
            result["tls_mod"] = tls_mod_match.group(1)

    # Парсим --lua-desync=send:...
    send_match = re.search(r'--lua-desync=send:([^\n]+)', args_str)
    if send_match:
        result["send_enabled"] = True
        send_str = send_match.group(1)

        # repeats=2
        repeats_match = re.search(r'repeats=(\d+)', send_str)
        if repeats_match:
            result["send_repeats"] = int(repeats_match.group(1))

        # ttl=...
        ttl_match = re.search(r'ttl=(\d+)', send_str)
        if ttl_match:
            result["send_ip_ttl"] = int(ttl_match.group(1))

        # ttl6=...
        ttl6_match = re.search(r'ttl6=(\d+)', send_str)
        if ttl6_match:
            result["send_ip6_ttl"] = int(ttl6_match.group(1))

        # badsum=true
        if 'badsum=true' in send_str:
            result["send_badsum"] = True

    # Парсим --out-range=-n8 или -d10
    out_range_match = re.search(r'--out-range=-([nd])(\d+)', args_str)
    if out_range_match:
        result["out_range_mode"] = out_range_match.group(1)
        result["out_range"] = int(out_range_match.group(2))

    return result


def get_category_default_syndata(category_name: str, protocol: str = "tcp") -> dict:
    """
    Возвращает дефолтные syndata настройки для категории из DEFAULT_PRESET_CONTENT.

    Args:
        category_name: Имя категории (например "youtube", "discord")
        protocol: "tcp" или "udp" (udp также покрывает QUIC/L7)

    Returns:
        dict: Словарь с параметрами (enabled, blob, autottl_*, send_*, out_range)
    """
    # Base defaults come from code (UI expectations), then overridden by
    # any values present in DEFAULT_PRESET_CONTENT (e.g. out-range for discord_voice).
    from .preset_model import SyndataSettings

    proto = (protocol or "").strip().lower()
    if proto in ("udp", "quic", "l7", "raw"):
        base = SyndataSettings.get_defaults_udp().to_dict()
        key = "syndata_overrides_udp"
    else:
        base = SyndataSettings.get_defaults().to_dict()
        key = "syndata_overrides_tcp"

    settings = get_default_category_settings()
    overrides = (settings.get(category_name) or {}).get(key) or {}
    if isinstance(overrides, dict) and overrides:
        base.update(overrides)

    return base

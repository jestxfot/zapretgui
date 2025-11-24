# strategy_menu/strategy_lists_separated.py

from .constants import LABEL_RECOMMENDED, LABEL_GAME, LABEL_CAUTION, LABEL_EXPERIMENTAL, LABEL_STABLE
from log import log

"""
Censorliber, [08.08.2025 1:02]
ну окей начнем с дискодра и ютуба

Censorliber, [08.08.2025 1:02]
а там добавим возможность отключения для обхода части сайтов

Censorliber, [08.08.2025 1:02]
хз как

Censorliber, [08.08.2025 1:02]
чет тту без идей

Censorliber, [08.08.2025 1:02]
или делать нулевую стратегию в качестве затычки в коде чтобы проще было или... прям кнопку добавлять
"""

"""
------ добавить в остьальное tcp по всем портам --------------------
--filter-tcp=4950-4955 --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=8 --dpi-desync-fooling=md5sig,badseq --new

--filter-udp=443-9000 --ipset=ipset-all.txt --hostlist-domains=riotcdn.net,playvalorant.com,riotgames.com,pvp.net,rgpub.io,rdatasrv.net,riotcdn.com,riotgames.es,RiotClientServices.com,LeagueofLegends.com --dpi-desync=fake --dpi-desync-repeats=6 --dpi-desync-fake-quic=quic_initial_www_google_com.bin --new

------ ВАЖНЫЕ И НЕОБЫЧНЫЕ СТРАТЕГИИ по идее надо писать syndata в конце в порядке исключения для всех доменов--------------------
--filter-tcp=443 --dpi-desync=fake --dpi-desync-fooling=badsum --dpi-desync-fake-tls-mod=rnd,rndsni,padencap
--filter-tcp=443 --dpi-desync=fake --dpi-desync-ttl=4 --dpi-desync-fake-tls-mod=rnd,rndsni,padencap
--filter-tcp=443 --dpi-desync=split --dpi-desync-split-pos=1 --dpi-desync-autottl --dpi-desync-fooling=badseq --dpi-desync-repeats=8 --new
--filter-tcp=443 --dpi-desync=split --dpi-desync-split-pos=1 --dpi-desync-autottl --dpi-desync-fooling=badseq --dpi-desync-repeats=8 --dpi-desync-fake-tls-mod=rnd,dupsid,sni=www.google.com

--filter-tcp=443 --dpi-desync=split2 --dpi-desync-split-seqovl=681 --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq,hopbyhop2 --dpi-desync-split-seqovl-pattern=tls_clienthello_www_google_com.bin

--filter-tcp=443 --dpi-desync=split2 --dpi-desync-split-seqovl=681 --dpi-desync-split-pos=1 --dpi-desync-repeats=2 --dpi-desync-fooling=badseq,hopbyhop2 --dpi-desync-split-seqovl-pattern=tls_clienthello_www_google_com.bin

--filter-tcp=443 --dpi-desync=split2 --dpi-desync-repeats=2 --dpi-desync-split-seqovl=681 --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq,hopbyhop2 --dpi-desync-split-seqovl-pattern=tls_clienthello_www_google_com.bin --new
--filter-tcp=443 --dpi-desync=fake,split2 --dpi-desync-repeats=6 --dpi-desync-fooling=md5sig --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --new
--filter-tcp=443 --dpi-desync=fake,split2 --dpi-desync-split-seqovl=1 --dpi-desync-split-tls=sniext --dpi-desync-fake-tls=tls_clienthello_2.bin --dpi-desync-ttl=2 --new
--filter-tcp=443 --dpi-desync=fake,split2 --dpi-desync-split-seqovl=681 --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq --dpi-desync-repeats=8 --dpi-desync-split-seqovl-pattern=tls_clienthello_www_google_com.bin --dpi-desync-fake-tls-mod=rnd,dupsid,sni=www.google.com --new
--filter-tcp=443 --dpi-desync=fake,multidisorder --dpi-desync-split-pos=midsld --dpi-desync-repeats=6 --dpi-desync-fooling=badseq,md5sig --new bol-van
--filter-tcp=443 --dpi-desync=fake,multidisorder --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=midsld+1 --dpi-desync-fooling=md5sig,badseq --dpi-desync-fake-tls=tls_clienthello_5.bin --dpi-desync-fake-tls-mod=rnd --dpi-desync-autottl --new
--filter-tcp=443 --dpi-desync=fake,multidisorder --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=sld+1 --dpi-desync-fake-tls=0x0F0F0E0F --dpi-desync-fake-tls=tls_clienthello_9.bin --dpi-desync-fake-tls-mod=rnd,dupsid --dpi-desync-fooling=md5sig --dpi-desync-autottl --dup=2 --dup-fooling=md5sig --dup-autottl --dup-cutoff=n3 --new
--filter-tcp=443 --dpi-desync=fake,fakedsplit --dpi-desync-split-pos=1 --dpi-desync-fake-tls=tls_clienthello_7.bin
--filter-tcp=443 --dpi-desync=fake,fakedsplit --dpi-desync-split-pos=1 --dpi-desync-fake-tls=tls_clienthello_7.bin --dpi-desync-fooling=badseq --dpi-desync-autottl
--filter-tcp=443 --dpi-desync=fake,fakedsplit --dpi-desync-split-pos=1 --dpi-desync-fake-tls=tls_clienthello_9.bin
--filter-tcp=443 --dpi-desync=fake,fakedsplit --dpi-desync-split-pos=1 --dpi-desync-fake-tls=tls_clienthello_9.bin --dpi-desync-fooling=badseq --dpi-desync-autottl
--filter-tcp=443 --dpi-desync=fake,disorder2 --dpi-desync-autottl=2 --dpi-desync-fooling=badseq --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin

---------- LABEL_GAME ----------------
--filter-tcp=443 --dpi-desync=multisplit --dpi-desync-split-seqovl=293 --dpi-desync-split-seqovl-pattern=tls_clienthello_12.bin --new
--filter-tcp=443 --dpi-desync=multisplit --dpi-desync-split-seqovl=308 --dpi-desync-split-seqovl-pattern=tls_clienthello_15.bin --new
--filter-tcp=443 --dpi-desync=multisplit --dpi-desync-split-seqovl=308 --dpi-desync-split-seqovl-pattern=tls_clienthello_5.bin --dup=2 --dup-cutoff=n3 --new
--filter-tcp=443 --payload=tls_client_hello --out-range=-n3 --lua-desync=send:repeats=2 --out-range=-d10 --lua-desync=multisplit:seqovl=226:seqovl_pattern=bin_tls18 --new

--comment Cloudflare WARP(1.1.1.1, 1.0.0.1)
--filter-tcp=443 --ipset-ip=162.159.36.1,162.159.46.1,2606:4700:4700::1111,2606:4700:4700::1001 --filter-l7=tls --dpi-desync=fake --dpi-desync-fake-tls=0x00 --dpi-desync-start=n2 --dpi-desync-cutoff=n3 --dpi-desync-fooling=md5sig --new

--comment WireGuard
--filter-l7=wireguard --dpi-desync=fake --dpi-desync-fake-wireguard=0x00 --dpi-desync-cutoff=n2

----------------------- LABEL_WARP -------------------------------
--filter-tcp=443 --dpi-desync=fake,multisplit --dpi-desync-split-seqovl=1 --dpi-desync-fooling=md5sig,badseq 
--filter-tcp=443 --dpi-desync=fake,multisplit --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=1 --dpi-desync-fake-tls=tls_clienthello_vk_com.bin --dpi-desync-ttl=5 --new
--filter-tcp=443 --dpi-desync=fake,multisplit --dpi-desync-fooling=md5sig --dpi-desync-autottl --new
--filter-tcp=443 --dpi-desync=fake,multisplit --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls=0x0F0F0E0F --dpi-desync-fake-tls=tls_clienthello_9.bin --dpi-desync-fake-tls-mod=rnd,dupsid --dpi-desync-fooling=md5sig --dpi-desync-autottl --dup=2 --dup-fooling=md5sig --dup-autottl --dup-cutoff=n3 --new
--filter-tcp=443 --dpi-desync=fake,multisplit --dpi-desync-split-seqovl=1 --dpi-desync-fooling=md5sig,badseq --dpi-desync-fake-tls=tls_clienthello_7.bin --dpi-desync-fake-tls-mod=rnd,padencap --dpi-desync-autottl --new

--filter-tcp=443 --dpi-desync=fakeddisorder --dpi-desync-split-pos=2,midsld --dpi-desync-fakedsplit-pattern=tls_clienthello_1.bin --dpi-desync-fooling=badseq --new
--filter-tcp=443 --dpi-desync=fakeddisorder --dpi-desync-split-pos=2,midsld+1 --dpi-desync-fakedsplit-pattern=tls_clienthello_4.bin --dpi-desync-fooling=badseq --new

--filter-tcp=443 --dpi-desync=fakedsplit --dpi-desync-fooling=badseq --dpi-desync-split-pos=2,midsld-1 --dpi-desync-fakedsplit-pattern=tls_clienthello_4.bin --new
--filter-tcp=443 --dpi-desync=fakedsplit --dpi-desync-split-pos=7 --dpi-desync-fakedsplit-pattern=tls_clienthello_5.bin --dpi-desync-fooling=md5sig --dpi-desync-autottl --dup=2 --dup-fooling=md5sig --dup-autottl --dup-cutoff=n3 --new


--filter-tcp=443 --ipcache-hostname --dpi-desync=syndata,fake,multisplit --dpi-desync-split-pos=sld+1 --dpi-desync-fake-syndata=tls_clienthello_7.bin --dpi-desync-fake-tls=0x0F0F0E0F --dpi-desync-fake-tls=tls_clienthello_9.bin --dpi-desync-fake-tls-mod=rnd,dupsid --dpi-desync-fooling=md5sig --dpi-desync-autottl --dup=2 --dup-fooling=md5sig --dup-autottl --dup-cutoff=n3 --new

--filter-tcp=443 --dpi-desync=syndata --new
--filter-tcp=443 --dpi-desync=syndata,multisplit --dpi-desync-split-seqovl=1 --dpi-desync-fake-syndata=tls_clienthello_16.bin --dup=2 --dup-cutoff=n3 --new
--filter-tcp=443 --dpi-desync=syndata,multisplit --dpi-desync-split-seqovl=2 --dpi-desync-fake-syndata=tls_clienthello_16.bin --dup=2 --dup-cutoff=n3 --new

--filter-tcp=2099,5222,5223,8393-8400 --ipset=ipset-cloudflare.txt --dpi-desync=syndata --new

--filter-udp=5000-5500 --ipset=ipset-lol-ru.txt --dpi-desync=fake --dpi-desync-repeats=6 --new

--filter-tcp=2099 --ipset=ipset-lol-ru.txt --dpi-desync=syndata --new
--filter-tcp=5222,5223 --ipset=ipset-lol-euw.txt --dpi-desync=syndata --new
--filter-udp=5000-5500 --ipset=ipset-lol-euw.txt --dpi-desync=fake --dpi-desync-repeats=6

--filter-tcp=2000-8400 --dpi-desync=syndata
--filter-tcp=5222 --ipset="%LISTS%ipset-cloudflare.txt" --dpi-desync=syndata --new ^
--filter-tcp=5223 --ipset="%LISTS%ipset-cloudflare.txt" --dpi-desync=syndata --new ^

--filter-udp=8886 --ipset-ip=188.114.96.0/22 --dpi-desync=fake --dpi-desync-any-protocol --dpi-desync-fake-unknown-udp=quic_4.bin --dpi-desync-cutoff=d2 --dpi-desync-autottl --new
"""

from .strategies_registry import registry

def combine_strategies(*args, **kwargs) -> dict:
    """
    Объединяет выбранные стратегии в одну общую с правильным порядком командной строки
    """
    
    if kwargs and not args:
        log("Используется новый способ вызова combine_strategies", "DEBUG")
        category_strategies = kwargs
    elif not args and not kwargs:
        log("Используются значения по умолчанию", "DEBUG")
        category_strategies = registry.get_default_selections()
    else:
        raise ValueError("Нельзя одновременно использовать позиционные и именованные аргументы")
    
    # Получаем базовые аргументы
    from strategy_menu import get_base_args_selection
    base_args_type = get_base_args_selection()
    
    BASE_ARGS_OPTIONS = {
        "windivert_all": "--wf-raw=@windivert.all.txt",
        "windivert-discord-media-stun-sites": "--wf-raw=@windivert.discord_media+stun+sites.txt",
        "wf-l3": "--wf-l3=ipv4,ipv6 --wf-tcp=80,443,2053,2083,2087,2096,8080,8443 --wf-udp=443,1400,19294-19344,50000-50100",
        "wf-l3-all": "--wf-l3=ipv4,ipv6 --wf-tcp=80,443,444-65535 --wf-udp=443,444-65535",
        "none": ""
    }
    
    base_args = BASE_ARGS_OPTIONS.get(base_args_type, BASE_ARGS_OPTIONS["windivert_all"])
    
    # ✅ НОВАЯ ЛОГИКА: Собираем аргументы в порядке командной строки
    args_parts = []
    if base_args:
        args_parts.append(base_args)
    
    # Получаем категории в порядке командной строки
    category_keys_ordered = registry.get_all_category_keys_by_command_order()
    none_strategies = registry.get_none_strategies()
    
    descriptions = []
    
    for category_key in category_keys_ordered:
        strategy_id = category_strategies.get(category_key)
        
        if not strategy_id:
            continue
            
        # Пропускаем "none" стратегии
        none_id = none_strategies.get(category_key)
        if strategy_id == none_id:
            continue
            
        # Получаем аргументы стратегии
        args = registry.get_strategy_args_safe(category_key, strategy_id)
        if args:
            args_parts.append(args)
            
            # ✅ ДОБАВЛЯЕМ --new РАЗДЕЛИТЕЛЬ ЕСЛИ НУЖНО
            category_info = registry.get_category_info(category_key)
            if category_info and category_info.needs_new_separator:
                args_parts.append("--new")
            
            # Добавляем в описание
            strategy_name = registry.get_strategy_name_safe(category_key, strategy_id)
            if category_info:
                descriptions.append(f"{category_info.emoji} {strategy_name}")
    
    # Объединяем все части через пробел
    combined_args = " ".join(args_parts)
    
    # Формируем описание
    combined_description = " | ".join(descriptions) if descriptions else "Пользовательская комбинация"
    
    log(f"Создана комбинированная стратегия в командном порядке: {combined_args}", "DEBUG")
    
    return {
        "name": "Комбинированная стратегия",
        "description": combined_description,
        "version": "1.0", 
        "provider": "universal",
        "author": "Combined",
        "updated": "2024",
        "all_sites": True,
        "args": combined_args,
        "_is_builtin": True,
        **{f"_{key}_id": strategy_id for key, strategy_id in category_strategies.items()}
    }
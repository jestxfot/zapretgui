# strategy_menu/strategy_lists_separated.py

from .constants import LABEL_RECOMMENDED, LABEL_GAME, LABEL_CAUTION, LABEL_EXPERIMENTAL, LABEL_STABLE
from log import log

try:
    from .TWITCH_TCP_STRATEGIES import TWITCH_TCP_STRATEGIES
except ImportError as e:
    log(f"Ошибка импорта TWITCH_TCP_STRATEGIES: {e}", "❌ ERROR")
    TWITCH_TCP_STRATEGIES = {}

try:
    from .GOOGLEVIDEO_TCP_STRATEGIES import GOOGLEVIDEO_STRATEGIES
except ImportError as e:
    log(f"Ошибка импорта GOOGLEVIDEO_TCP_STRATEGIES: {e}", "❌ ERROR")
    GOOGLEVIDEO_TCP_STRATEGIES = {}

try:
    from .YOUTUBE_TCP_STRATEGIES import YOUTUBE_TCP_STRATEGIES
except ImportError as e:
    log(f"Ошибка импорта YOUTUBE_TCP_STRATEGIES: {e}", "❌ ERROR")
    YOUTUBE_TCP_STRATEGIES = {}

try:
    from .OTHER_STRATEGIES import OTHER_STRATEGIES
except ImportError as e:
    log(f"Ошибка импорта OTHER_STRATEGIES: {e}", "❌ ERROR")
    OTHER_STRATEGIES = {}

try:
    from .RUTRACKER_TCP_STRATEGIES import RUTRACKER_TCP_STRATEGIES
except ImportError as e:
    log(f"Ошибка импорта RUTRACKER_TCP_STRATEGIES: {e}", "❌ ERROR")
    RUTRACKER_TCP_STRATEGIES = {}

try:
    from .NTCPARTY_TCP_STRATEGIES import NTCPARTY_TCP_STRATEGIES
except ImportError as e:
    log(f"Ошибка импорта NTCPARTY_TCP_STRATEGIES: {e}", "❌ ERROR")
    NTCPARTY_TCP_STRATEGIES = {}

try:
    from .IPSET_TCP_STRATEGIES import IPSET_TCP_STRATEGIES
except ImportError as e:
    log(f"Ошибка импорта IPSET_TCP_STRATEGIES: {e}", "❌ ERROR")
    IPSET_TCP_STRATEGIES = {}

try:
    from .IPSET_UDP_STRATEGIES import IPSET_UDP_STRATEGIES
except ImportError as e:
    log(f"Ошибка импорта IPSET_UDP_STRATEGIES: {e}", "❌ ERROR")
    IPSET_UDP_STRATEGIES = {}

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
--filter-tcp=443 --dpi-desync=split --dpi-desync-split-pos=1 --dpi-desync-autottl --dpi-desync-fooling=badseq --dpi-desync-repeats=8 --dpi-desync-fake-tls-mod=rnd,dupsid,sni=www.google.com --new
--filter-tcp=443 --dpi-desync=split2 --dpi-desync-split-seqovl=681 --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq,hopbyhop2 --dpi-desync-split-seqovl-pattern=tls_clienthello_www_google_com.bin --new
--filter-tcp=443 --dpi-desync=split2 --dpi-desync-repeats=2 --dpi-desync-split-seqovl=681 --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq,hopbyhop2 --dpi-desync-split-seqovl-pattern=tls_clienthello_www_google_com.bin --new
--filter-tcp=443 --dpi-desync=fake,split2 --dpi-desync-repeats=6 --dpi-desync-fooling=md5sig --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --new
--filter-tcp=443 --dpi-desync=fake,split2 --dpi-desync-split-seqovl=1 --dpi-desync-split-tls=sniext --dpi-desync-fake-tls=tls_clienthello_2.bin --dpi-desync-ttl=2 --new
--filter-tcp=443 --dpi-desync=fake,split2 --dpi-desync-split-seqovl=681 --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq --dpi-desync-repeats=8 --dpi-desync-split-seqovl-pattern=tls_clienthello_www_google_com.bin --dpi-desync-fake-tls-mod=rnd,dupsid,sni=www.google.com --new
--filter-tcp=443 --dpi-desync=fake,multidisorder --dpi-desync-split-pos=midsld --dpi-desync-repeats=6 --dpi-desync-fooling=badseq,md5sig --new
--filter-tcp=443 --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=11 --dpi-desync-fooling=md5sig --dpi-desync-fake-tls-mod=rnd,dupsid,sni=www.google.com --new
--filter-tcp=443 --dpi-desync=fake,multidisorder --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=midsld+1 --dpi-desync-fooling=md5sig,badseq --dpi-desync-fake-tls=tls_clienthello_5.bin --dpi-desync-fake-tls-mod=rnd --dpi-desync-autottl --new
--filter-tcp=443 --dpi-desync=fake,multidisorder --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=sld+1 --dpi-desync-fake-tls=0x0F0F0E0F --dpi-desync-fake-tls=tls_clienthello_9.bin --dpi-desync-fake-tls-mod=rnd,dupsid --dpi-desync-fooling=md5sig --dpi-desync-autottl --dup=2 --dup-fooling=md5sig --dup-autottl --dup-cutoff=n3 --new
--filter-tcp=443 --dpi-desync=fake,fakedsplit --dpi-desync-split-pos=1 --dpi-desync-fake-tls=tls_clienthello_7.bin
--filter-tcp=443 --dpi-desync=fake,fakedsplit --dpi-desync-split-pos=1 --dpi-desync-fake-tls=tls_clienthello_7.bin --dpi-desync-fooling=badseq --dpi-desync-autottl
--filter-tcp=443 --dpi-desync=fake,fakedsplit --dpi-desync-split-pos=1 --dpi-desync-fake-tls=tls_clienthello_9.bin
--filter-tcp=443 --dpi-desync=fake,fakedsplit --dpi-desync-split-pos=1 --dpi-desync-fake-tls=tls_clienthello_9.bin --dpi-desync-fooling=badseq --dpi-desync-autottl
--filter-tcp=443 --dpi-desync=fake,disorder2 --dpi-desync-autottl=2 --dpi-desync-fooling=badseq --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin

---------- LABEL_GAME ----------------
--filter-tcp=443 --dpi-desync=multisplit --dpi-desync-split-seqovl=211 --dpi-desync-split-seqovl-pattern=tls_clienthello_5.bin --new
--filter-tcp=443 --dpi-desync=multisplit --dpi-desync-split-seqovl=293 --dpi-desync-split-seqovl-pattern=tls_clienthello_12.bin --new
--filter-tcp=443 --dpi-desync=multisplit --dpi-desync-split-seqovl=308 --dpi-desync-split-seqovl-pattern=tls_clienthello_15.bin --new
--filter-tcp=443 --dpi-desync=multisplit --dpi-desync-split-seqovl=308 --dpi-desync-split-seqovl-pattern=tls_clienthello_5.bin --dup=2 --dup-cutoff=n3 --new
--filter-tcp=443 --dpi-desync=multisplit --dpi-desync-split-seqovl=226 --dpi-desync-split-seqovl-pattern=tls_clienthello_18.bin --dup=2 --dup-cutoff=n3 --new
--filter-tcp=443 --dpi-desync=multisplit --dpi-desync-split-seqovl=286 --dpi-desync-split-seqovl-pattern=tls_clienthello_11.bin --dup=2 --dup-cutoff=n3 --new

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

# 80 порт не используется для QUIC, только 443 UDP
YOUTUBE_BASE_ARG_UDP = "--filter-udp=443 --hostlist=youtube.txt"

YOUTUBE_QUIC_STRATEGIES = {
    "fake_11": {
        "name": "fake 11 повторов",
        "description": "Базовая стратегия с 11 повторами fake пакетов",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""{YOUTUBE_BASE_ARG_UDP} --dpi-desync=fake --dpi-desync-repeats=11 --new"""
    },
    "fake_2_quic_test_00": {
        "name": "fake 2 повторов quic_test_00",
        "description": "2 повтора с тестовым QUIC пакетом",
        "author": "hz",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG_UDP} --dpi-desync=fake --dpi-desync-repeats=2 --dpi-desync-cutoff=n2 --dpi-desync-fake-quic=quic_test_00.bin --new"""
    },
    "fake_11_quic_bin": {
        "name": "fake 11 повторов (Google QUIC)",
        "description": "11 повтора с Google QUIC и cutoff после 11 пакетов",
        "author": "hz",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG_UDP} --dpi-desync=fake --dpi-desync-repeats=11 --dpi-desync-fake-quic=quic_initial_www_google_com.bin --new"""
    },
    "fake_2_n2": {
        "name": "fake 2 повторов (Google QUIC) cutoff=n2",
        "description": "2 повтора с Google QUIC и cutoff после 2 пакетов",
        "author": "hz",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG_UDP} --dpi-desync=fake --dpi-desync-repeats=2 --dpi-desync-cutoff=n2 --dpi-desync-fake-quic=quic_initial_www_google_com.bin --new"""
    },
    "fake_repeat_2_quic": {
        "name": "fake 2 повторов (Google QUIC) cutoff=n2",
        "description": "2 повтора с Google QUIC и cutoff после 2 пакетов",
        "author": "hz",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG_UDP} --hostlist-domains=youtube.com,youtu.be,ytimg.com,googlevideo.com,googleapis.com,gvt1.com,video.google.com --dpi-desync=fake --dpi-desync-repeats=2 --dpi-desync-fake-quic=fake_quic.bin --new"""
    },
    
    "fake_4_google": {
        "name": "fake 4 повтора (Google QUIC)",
        "description": "4 повтора с fake QUIC пакетом Google",
        "author": "hz",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG_UDP} --dpi-desync=fake --dpi-desync-repeats=4 --dpi-desync-fake-quic=quic_initial_www_google_com.bin --new"""
    },
    
    "fake_4_quic1": {
        "name": "fake 4 повтора (QUIC 1)",
        "description": "4 повтора с альтернативным QUIC пакетом",
        "author": "hz",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG_UDP} --dpi-desync=fake --dpi-desync-repeats=4 --dpi-desync-fake-quic=quic_1.bin --new"""
    },
    
    "fake_15_ttl0_md5sig": {
        "name": "fake 15 повторов TTL=0 (md5sig+badsum)",
        "description": "Агрессивная стратегия с 15 повторами, TTL=0 и двумя методами fooling",
        "author": "hz",
        "label": LABEL_EXPERIMENTAL,
        "args": f"""{YOUTUBE_BASE_ARG_UDP} --dpi-desync=fake --dpi-desync-repeats=15 --dpi-desync-ttl=0 --dpi-desync-any-protocol --dpi-desync-cutoff=d4 --dpi-desync-fooling=md5sig,badsum --dpi-desync-fake-quic=quic_initial_www_google_com.bin --new"""
    },
    
    "fake_15_ttl0_badsum": {
        "name": "fake 15 повторов TTL=0 (badsum)",
        "description": "Агрессивная стратегия с 15 повторами, TTL=0 и badsum",
        "author": "hz",
        "label": LABEL_EXPERIMENTAL,
        "args": f"""{YOUTUBE_BASE_ARG_UDP} --dpi-desync=fake --dpi-desync-repeats=15 --dpi-desync-ttl=0 --dpi-desync-any-protocol --dpi-desync-cutoff=d4 --dpi-desync-fooling=badsum --dpi-desync-fake-quic=quic_initial_www_google_com.bin --new"""
    },
    
    "fake_6_google": {
        "name": "fake 6 повторов (Google QUIC)",
        "description": "6 повторов с fake QUIC пакетом Google",
        "author": "hz",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG_UDP} --dpi-desync=fake --dpi-desync-fake-quic=quic_initial_www_google_com.bin --dpi-desync-repeats=6 --new"""
    },
    
    "fake_ipfrag2_quic5": {
        "name": "fake+ipfrag2 (QUIC 5)",
        "description": "Комбинация fake и ipfrag2 с QUIC 5",
        "author": "hz",
        "label": LABEL_STABLE,
        "args": f"""{YOUTUBE_BASE_ARG_UDP} --dpi-desync=fake,ipfrag2 --dpi-desync-fake-quic=quic_5.bin --dpi-desync-cutoff=n3 --dpi-desync-repeats=3 --new"""
    },
    
    "fake_ipfrag2_quic3": {
        "name": "fake+ipfrag2 (QUIC 3)",
        "description": "Комбинация fake и ipfrag2 с QUIC 3",
        "author": "hz",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG_UDP} --dpi-desync=fake,ipfrag2 --dpi-desync-fake-quic=quic_3.bin --dpi-desync-cutoff=n3 --dpi-desync-repeats=2 --new"""
    },
    
    "fake_ipfrag2_quic7": {
        "name": "fake+ipfrag2 (QUIC 7)",
        "description": "Комбинация fake и ipfrag2 с QUIC 7",
        "author": "hz",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG_UDP} --dpi-desync=fake,ipfrag2 --dpi-desync-fake-quic=quic_7.bin --dpi-desync-cutoff=n3 --dpi-desync-repeats=3 --new"""
    },
    
    "fake_udplen_inc2": {
        "name": "fake+udplen increment=2",
        "description": "UDP длина +2 с QUIC 3",
        "author": "hz",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG_UDP} --dpi-desync=fake,udplen --dpi-desync-udplen-increment=2 --dpi-desync-fake-quic=quic_3.bin --dpi-desync-cutoff=n3 --dpi-desync-repeats=2 --new"""
    },
    
    "fake_udplen_inc4_quic3": {
        "name": "fake+udplen increment=4 (QUIC 3)",
        "description": "UDP длина +4 с QUIC 3",
        "author": "hz",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG_UDP} --dpi-desync=fake,udplen --dpi-desync-udplen-increment=4 --dpi-desync-fake-quic=quic_3.bin --dpi-desync-cutoff=n3 --dpi-desync-repeats=2 --new"""
    },
    
    "fake_udplen_inc4_quic4": {
        "name": "fake+udplen increment=4 (QUIC 4)",
        "description": "UDP длина +4 с QUIC 4",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""{YOUTUBE_BASE_ARG_UDP} --dpi-desync=fake,udplen --dpi-desync-udplen-increment=4 --dpi-desync-fake-quic=quic_4.bin --dpi-desync-cutoff=n3 --dpi-desync-repeats=2 --new"""
    },
    
    "fake_udplen_pattern_0F0F": {
        "name": "fake+udplen pattern 0x0F0F0E0F",
        "description": "UDP с паттерном 0x0F0F0E0F и QUIC 6",
        "author": "hz",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG_UDP} --dpi-desync=fake,udplen --dpi-desync-udplen-increment=8 --dpi-desync-udplen-pattern=0x0F0F0E0F --dpi-desync-fake-quic=quic_6.bin --dpi-desync-cutoff=n3 --dpi-desync-repeats=2 --new"""
    },
    
    "fake_udplen_pattern_0F0F_autottl": {
        "name": "fake+udplen pattern 0x0F0F0E0F (AutoTTL)",
        "description": "UDP с паттерном 0x0F0F0E0F, QUIC 6 и AutoTTL",
        "author": "hz",
        "label": LABEL_EXPERIMENTAL,
        "args": f"""{YOUTUBE_BASE_ARG_UDP} --dpi-desync=fake,udplen --dpi-desync-udplen-increment=8 --dpi-desync-udplen-pattern=0x0F0F0E0F --dpi-desync-fake-quic=quic_6.bin --dpi-desync-cutoff=n3 --dpi-desync-repeats=2 --dpi-desync-autottl --new"""
    },
    
    "fake_udplen_pattern_0E0F": {
        "name": "fake+udplen pattern 0x0E0F0E0F",
        "description": "UDP с паттерном 0x0E0F0E0F и QUIC 7",
        "author": "hz",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG_UDP} --dpi-desync=fake,udplen --dpi-desync-udplen-increment=8 --dpi-desync-udplen-pattern=0x0E0F0E0F --dpi-desync-fake-quic=quic_7.bin --dpi-desync-cutoff=n3 --dpi-desync-repeats=2 --new"""
    },
    
    "fake_udplen_pattern_FEA8": {
        "name": "fake+udplen pattern 0xFEA82025",
        "description": "UDP с паттерном 0xFEA82025 и QUIC 4",
        "author": "hz",
        "label": LABEL_CAUTION,
        "args": f"""{YOUTUBE_BASE_ARG_UDP} --dpi-desync=fake,udplen --dpi-desync-udplen-increment=8 --dpi-desync-udplen-pattern=0xFEA82025 --dpi-desync-fake-quic=quic_4.bin --dpi-desync-cutoff=n4 --dpi-desync-repeats=2 --new"""
    },
    
    "fake_udplen_inc25": {
        "name": "fake+udplen increment=25",
        "description": "UDP длина +25 с QUIC 5",
        "author": "hz",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG_UDP} --dpi-desync=fake,udplen --dpi-desync-udplen-increment=25 --dpi-desync-fake-quic=quic_5.bin --dpi-desync-repeats=2 --dpi-desync-cutoff=n3 --new"""
    },
    
    "fake_split2_udplen25": {
        "name": "fake+split2 udplen=25",
        "description": "Комбинация fake и split2 с UDP длиной +25",
        "author": "hz",
        "label": LABEL_EXPERIMENTAL,
        "args": f"""{YOUTUBE_BASE_ARG_UDP} --dpi-desync=fake,split2 --dpi-desync-repeats=10 --dpi-desync-udplen-increment=25 --dpi-desync-fake-quic=quic_initial_www_google_com.bin --new"""
    },
    
    "fake_tamper_google": {
        "name": "fake+tamper (Google QUIC)",
        "description": "Комбинация fake и tamper с Google QUIC",
        "author": "hz",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG_UDP} --dpi-desync=fake,tamper --dpi-desync-repeats=11 --dpi-desync-fake-quic=quic_initial_www_google_com.bin --new"""
    },
    
    "fake_tamper_autottl": {
        "name": "fake+tamper (AutoTTL=2)",
        "description": "Комбинация fake и tamper с AutoTTL=2",
        "author": "hz",
        "label": LABEL_STABLE,
        "args": f"""{YOUTUBE_BASE_ARG_UDP} --dpi-desync=fake,tamper --dpi-desync-autottl=2 --dpi-desync-repeats=11 --new"""
    },
    "youtube_udp_none": {
        "name": "Не применять для YouTube QUIC",
        "description": "Отключить обработку YouTube QUIC",
        "author": "System",
        "label": None,
        "args": ""  # Пустая строка = не добавлять аргументы
    }
}

DISCORD_STRATEGIES = {
    "dis4": {
        "name": "general (alt v2) 1.6.1",
        "description": "Устаревший split2 с seqovl 652 и паттерном 4",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""--filter-tcp=80,443 --hostlist=discord.txt --dpi-desync=split2 --dpi-desync-split-seqovl=652 --dpi-desync-split-pos=2 --dpi-desync-split-seqovl-pattern=tls_clienthello_www_google_com.bin --new"""
    },
    "multisplit_fake_tls_badseq": {
        "name": "multisplit fake tls и badseq",
        "description": "Хорошая базовая комлектация для старта",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=80,443 --hostlist=discord.txt --dpi-desync=fake,multisplit --dpi-desync-split-pos=sld+1 --dpi-desync-fake-tls=0x0F0F0E0F --dpi-desync-fake-tls=tls_clienthello_14.bin --dpi-desync-fake-tls-mod=rnd,dupsid --dpi-desync-fooling=badseq --dpi-desync-autottl --dup=2 --dup-fooling=badseq --dup-autottl --dup-cutoff=n3 --new"""
    },
    "multisplit_fake_tls_md5sig": {
        "name": "multisplit fake tls и md5sig",
        "description": "Хорошая базовая комлектация для старта",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=80,443 --hostlist=discord.txt --dpi-desync=fake,multisplit --dpi-desync-split-pos=sld+1 --dpi-desync-fake-tls=0x0F0F0E0F --dpi-desync-fake-tls=tls_clienthello_14.bin --dpi-desync-fake-tls-mod=rnd,dupsid --dpi-desync-fooling=md5sig --dpi-desync-autottl --dup=2 --dup-fooling=md5sig --dup-autottl --dup-cutoff=n3 --new"""
    },
    "multidisorder_md5sig_pos": {
        "name": "multidisorder md5sig и сплит",
        "description": "Дисордер стратегия с фуллингом md5sig нарезкой и повтором 6",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=80,443 --hostlist=discord.txt --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=6 --dpi-desync-fooling=badseq,md5sig --new"""
    },
    "multidisorder_ipset_syndata": {
        "name": "Адреса discord с фуллингом syndata",
        "description": "Использует адреса дискорда, вместо доменов",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""--filter-tcp=443 --ipset=ipset-discord.txt --dpi-desync=syndata --dpi-desync-fake-syndata=tls_clienthello_3.bin --dpi-desync-autottl --new"""
    },
    "multidisorder_badseq_pos": {
        "name": "multidisorder badseq и сплит",
        "description": "Дисордер стратегия с фуллингом badseq нарезкой и повтором 6",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=80,443 --hostlist=discord.txt --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --new"""
    },
    "multisplit_286_pattern": {
        "name": "multisplit seqovl 286 с парттерном 11",
        "description": "Дисордер стратегия с фуллингом badseq нарезкой и повтором 11",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=80,443 --hostlist=discord.txt --dpi-desync=multisplit --dpi-desync-split-seqovl=286 --dpi-desync-split-seqovl-pattern=tls_clienthello_11.bin --dup=2 --dup-cutoff=n3 --new"""
    },
    "multidisorder_super_split_md5sig": {
        "name": "multidisorder super split md5sig",
        "description": "Обратная стратегия с нестандартной нарезкой и md5sig",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=80,443 --hostlist=discord.txt --dpi-desync=fake,multidisorder --dpi-desync-split-pos=method+2,midsld,5 --dpi-desync-ttl=0 --dpi-desync-fooling=md5sig,badsum,badseq --dpi-desync-repeats=15 --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --new"""
    },
    "multidisorder_super_split_badseq": {
        "name": "multidisorder super split ",
        "description": "Обратная стратегия с нестандартной нарезкой и badseq",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=80,443 --hostlist=discord.txt --dpi-desync=fake,multidisorder --dpi-desync-split-pos=method+2,midsld,5 --dpi-desync-ttl=0 --dpi-desync-fooling=badsum,badseq --dpi-desync-repeats=15 --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --new"""
    },
    "multidisorder_w3": {
        "name": "multidisorder с фейком w3 ",
        "description": "Обратная стратегия с фейком tls w3 и md5sig",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=80,443 --hostlist=discord.txt --dpi-desync=fake,multidisorder --dpi-desync-fake-tls=dtls_clienthello_w3_org.bin --dpi-desync-split-pos=1,midsld --dpi-desync-fooling=badseq,md5sig --new"""
    },
    "multidisorder_pos_100": {
        "name": "multidisorder с разрезом 100",
        "description": "Обратная стратегия с нестандартной нарезкой и фейком TLS",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=80,443 --hostlist=discord.txt --dpi-desync=fake,multidisorder --dpi-desync-fake-tls-mod=rnd,dupsid --dpi-desync-repeats=3 --dpi-desync-split-pos=100,midsld,sniext+1,endhost-2,-10 --dpi-desync-ttl=4 --new"""
    },
    "fake_badseq_rnd": {
        "name": "Фейк с фуулингом badseq и фейком tls rnd",
        "description": "Базовая стратегия десинхронизации с фейком tls rnd",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=80,443 --hostlist=discord.txt --dpi-desync=fake --dpi-desync-fooling=badseq --dpi-desync-fake-tls=tls_clienthello_7.bin --dpi-desync-fake-tls-mod=rnd --new"""
    },
    "fakedsplit_badseq_4": {
        "name": "Фейк с фуулингом badseq и фейком tls 4",
        "description": "Десинхронизация badseq с фейком tls 4",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=80,443 --hostlist=discord.txt --dpi-desync=fakedsplit --dpi-desync-split-pos=midsld-1,1 --dpi-desync-fooling=badseq --dpi-desync-fakedsplit-pattern=tls_clienthello_4.bin --dpi-desync-autottl --new"""
    },
    "fake_md5sig_fake_tls": {
        "name": "Фейк с фуулингом md5sig и фейком tls",
        "description": "Базовая десинхронизация md5sig с фейком tls",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=80,443 --hostlist=discord.txt --dpi-desync=fake --dpi-desync-fooling=md5sig --dpi-desync-fake-tls-mod=rnd,rndsni,padencap --new"""
    },
    "fake_autottl_faketls": {
        "name": "Фейк с авто ttl и фейком tls",
        "description": "Фейк с авто ttl и фейком tls (использовать с осторожностью)",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=80,443 --hostlist=discord.txt --dpi-desync=fake --dpi-desync-ttl=1 --dpi-desync-autottl=4 --dpi-desync-fake-tls-mod=rnd,rndsni,padencap --new"""
    },
    "fake_datanoack_fake_tls": {
        "name": "Фейк с datanoack и фейком tls",
        "description": "Фейк с datanoack и фейком tls",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=80,443 --hostlist=discord.txt --dpi-desync=fake --dpi-desync-fooling=datanoack --dpi-desync-fake-tls-mod=rnd,rndsni,padencap --new"""
    },
    "dis1": {
        "name": "Фейк с datanoack и padencap",
        "description": "Улучшенная стратегия с datanoack и padencap",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=80,443 --hostlist=discord.txt --dpi-desync=fake,fakeddisorder --dpi-desync-fooling=datanoack --dpi-desync-split-pos=midsld --dpi-desync-fake-tls-mod=rnd,rndsni,padencap --new"""
    },
    "dis2": {
        "name": "multisplit split pos padencap",
        "description": "Стандартный мультисплит с нарезкой и фейком padencap",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=80,443 --hostlist=discord.txt --dpi-desync=fake,multisplit --dpi-desync-ttl=1 --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls-mod=rnd,rndsni,padencap --new"""
    },
    "dis3": {
        "name": "split badseq 10",
        "description": "Стандартный сплит с фуллингом badseq и 10 повторами",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=80,443 --hostlist=discord.txt --dpi-desync=split --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq --dpi-desync-repeats=10 --dpi-desync-ttl=4 --new"""
    },
    "dis5": {
        "name": "fake split 6 google",
        "description": "Фейковый сплит с повторением 6 и фейком google",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=80,443 --hostlist=discord.txt --dpi-desync=fake,split --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --new"""
    },
    "dis5": {
        "name": "fake split2 6 sberbank",
        "description": "Фейковый сплит2 с повторением 6 и фейком от сбербанка много деняк",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=80,443 --hostlist=discord.txt --dpi-desync=fake,split2 --dpi-desync-ttl=1 --dpi-desync-autottl=5 --dpi-desync-repeats=6 --dpi-desync-fake-tls=tls_clienthello_sberbank_ru.bin --new"""
    },
    "dis6": {
        "name": "syndata (на все домены!)",
        "description": "Стратегия работает на все домены и может ломать сайты (на свой страх и риск)",
        "author": "hz",
        "label": LABEL_CAUTION,
        "args": f"""--filter-tcp=80,443 --hostlist=discord.txt --dpi-desync=syndata --dpi-desync-fake-syndata=tls_clienthello_3.bin --dpi-desync-ttl=5 --new"""
    },
    "dis7": {
        "name": "Ростелеком & Мегафон",
        "description": "Сплит с повторением 6 и фуллингом badseq и фейком tls от Google",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=80,443 --hostlist=discord.txt --dpi-desync=fake,split --dpi-desync-autottl=2 --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --new"""
    },
    "dis8": {
        "name": "Ростелеком & Мегафон v2",
        "description": "Cплит2 с фейком tls 4 и ttl 4 (короче одни четвёрки)",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=80,443 --hostlist=discord.txt --dpi-desync=fake,split2 --dpi-desync-split-seqovl=1 --dpi-desync-split-tls=sniext --dpi-desync-fake-tls=tls_clienthello_4.bin --dpi-desync-ttl=4 --new"""
    },
    "dis9": {
        "name": "split2 sniext google",
        "description": "Cплит2 с фейком tls от Google",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=80,443 --hostlist=discord.txt --dpi-desync=fake,split2 --dpi-desync-split-seqovl=1 --dpi-desync-split-tls=sniext --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --dpi-desync-ttl=2 --new"""
    },
    "dis10": {
        "name": "disorder2 badseq tls google",
        "description": "Cплит2 badseq с фейком tls от Google",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=80,443 --hostlist=discord.txt --dpi-desync=syndata,disorder2 --dpi-desync-split-pos=3 --dpi-desync-repeats=11 --dpi-desync-fooling=badseq --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --new"""
    },
    "dis11": {
        "name": "split badseq 10",
        "description": "Cплит2 с фуллингом badseq и 10 повторами",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=80,443 --hostlist=discord.txt --dpi-desync=split --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq --dpi-desync-repeats=10 --dpi-desync-autottl --new"""
    },
    "dis12": {
        "name": "split badseq 10 ttl",
        "description": "Cплит2 с фуллингом badseq и 10 повторами и ttl 3",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=80,443 --hostlist=discord.txt --dpi-desync=split --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq --dpi-desync-repeats=10 --dpi-desync-ttl=3 --new"""
    },
    "dis13": {
        "name": "fakedsplit badsrq 10",
        "description": "Фейки и сплиты с фуллингом badseq и 10 повторами",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=80,443 --hostlist=discord.txt --dpi-desync=fakedsplit --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq --dpi-desync-repeats=10 --dpi-desync-autottl --new"""
    },
    "dis14": {
        "name": "multisplit и seqovl",
        "description": "Мульти нарезка с seqovl и нестандартной позицией",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=80,443 --hostlist=discord.txt --dpi-desync=multisplit --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=midsld+1 --new"""
    },
    "other6": {
        "name": "general (alt) 1.8.1",
        "description": "Потом опишу подробнее",
        "author": "Flowseal",
        "label": None,
        "args": f"""--filter-tcp=80,443 --hostlist=discord.txt --dpi-desync=fake,split --dpi-desync-autottl=5 --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --new"""
    },
    "general_alt183": {
        "name": "general (alt) 1.8.3",
        "description": "Потом опишу подробнее",
        "author": "Flowseal",
        "label": None,
        "args": f"""--filter-tcp=80,443 --hostlist=discord.txt --dpi-desync=fake,fakedsplit --dpi-desync-autottl=5 --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --new"""
    },
    "general_alt2183": {
        "name": "general (alt2) 1.8.3",
        "description": "Потом опишу подробнее",
        "author": "Flowseal",
        "label": None,
        "args": f"""--filter-tcp=80,443 --hostlist=discord.txt --dpi-desync=multisplit --dpi-desync-split-seqovl=652 --dpi-desync-split-pos=2 --dpi-desync-split-seqovl-pattern=tls_clienthello_www_google_com.bin --new"""
    },
    "discord_tcp_none": {
        "name": "Не применять для Discord",
        "description": "Отключить обработку Discord",
        "author": "System",
        "label": None,
        "args": ""
    }
}

DISCORD_VOICE_STRATEGIES = {
    "ipv4_dup2_autottl_cutoff_n3": {
        "name": "IPv4 & IPv6 DUP, AutoTTL, Cutoff n3",
        "description": "Стратегия для IPv4 с дублированием пакетов, автоматическим TTL и обрезкой n3.",
        "author": "Community",
        "label": LABEL_RECOMMENDED,
        "args": f"""--filter-l3=ipv4 --filter-l7=discord,stun --dpi-desync=fake --dpi-desync-autottl --dup=2 --dup-autottl --dup-cutoff=n3 --new --filter-l3=ipv6 --filter-l7=discord,stun --dpi-desync=fake --dpi-desync-autottl6 --dup=2 --dup-autottl6 --dup-cutoff=n3 --new"""
    },
    "fake_l7": {
        "name": "Fake L7",
        "description": "Базовая стратегия с DPI Desync 'fake' и фильтрацией L7 для Discord и STUN.",
        "author": "Community",
        "label": LABEL_STABLE,
        "args": f"""--filter-l7=discord,stun --dpi-desync=fake --new"""
    },
    "fake_tamper_repeats_6": {
        "name": "Fake, Tamper, Repeats 6",
        "description": "Стратегия с подменой и изменением пакетов, 6 повторений.",
        "author": "Community",
        "label": None,
        "args": f"""--filter-l7=discord,stun --dpi-desync=fake,tamper --dpi-desync-repeats=6 --dpi-desync-fake-discord=0x00 --new"""
    },
    "fake_any_proto_repeats_6_cutoff_n4": {
        "name": "Fake, Any Proto, Repeats 6, Cutoff n4",
        "description": "Стратегия с Fake Desync для любого протокола, 6 повторениями и обрезкой n4.",
        "author": "Community",
        "label": None,
        "args": f"""--filter-l7=discord,stun --dpi-desync=fake --dpi-desync-repeats=6 --dpi-desync-any-protocol --dpi-desync-cutoff=n4 --new"""
    },
    "fake_tamper_any_proto_repeats_11_cutoff_d5": {
        "name": "Fake, Tamper, Repeats 11, Cutoff d5",
        "description": "Комбинированная стратегия с 11 повторениями и обрезкой d5 для любого протокола.",
        "author": "Community",
        "label": None,
        "args": f"""--filter-l7=discord,stun --dpi-desync=fake,tamper --dpi-desync-any-protocol --dpi-desync-cutoff=d5 --dpi-desync-repeats=11 --new"""
    },
    "fake_any_proto_quic1_cutoff_d2": {
        "name": "Fake, Any Proto, QUIC 1, Cutoff d2",
        "description": "Использование поддельного QUIC-пакета (quic_1.bin) с обрезкой d2.",
        "author": "Community",
        "label": None,
        "args": f"""--filter-l7=discord,stun --dpi-desync=fake --dpi-desync-any-protocol --dpi-desync-cutoff=d2 --dpi-desync-fake-quic=quic_1.bin --new"""
    },
    "fake_repeats_6": {
        "name": "Fake Repeats 6",
        "description": "Простая стратегия с 6 повторениями фейкового пакета.",
        "author": "Community",
        "label": None,
        "args": f"""--filter-l7=discord,stun --dpi-desync=fake --dpi-desync-repeats=6 --new"""
    },
    "ipset_fake_any_proto_cutoff_d3_repeats_6": {
        "name": "general (alt v2) 1.6.1",
        "description": "Стратегия, использующая IPSet, с 6 повторениями и обрезкой d3.",
        "author": "Community",
        "label": LABEL_RECOMMENDED,
        "args": f"""--ipset=ipset-discord.txt --dpi-desync=fake --dpi-desync-any-protocol --dpi-desync-cutoff=d3 --dpi-desync-repeats=6 --new"""
    },
    "ipset_fake_any_proto_cutoff_d3_repeats_8": {
        "name": "IPSet Fake, Any Proto, Cutoff d3, Repeats 8",
        "description": "Стратегия, использующая IPSet, с 8 повторениями и обрезкой d3.",
        "author": "Community",
        "label": LABEL_RECOMMENDED,
        "args": f"""--ipset=ipset-discord.txt --dpi-desync=fake --dpi-desync-any-protocol --dpi-desync-cutoff=d3 --dpi-desync-repeats=8 --new"""
    },
    "ipset_fake_any_proto_cutoff_d4_repeats_8": {
        "name": "IPSet Fake, Any Proto, Cutoff d4, Repeats 8",
        "description": "Стратегия, использующая IPSet, с 8 повторениями и обрезкой d4.",
        "author": "Community",
        "label": LABEL_RECOMMENDED,
        "args": f"""--ipset=ipset-discord.txt --dpi-desync=fake --dpi-desync-any-protocol --dpi-desync-cutoff=d4 --dpi-desync-repeats=8 --new"""
    },
    "fake_any_proto_cutoff_n3": {
        "name": "Fake, Any Proto, Cutoff n3",
        "description": "Минималистичная стратегия с обрезкой n3 для любого протокола.",
        "author": "Community",
        "label": None,
        "args": f"""--ipset=ipset-discord.txt --dpi-desync=fake --dpi-desync-any-protocol --dpi-desync-cutoff=n3 --new"""
    },
    "fake_split2_quic_test_cutoff_d2": {
        "name": "Fake, Split2, QUIC Test, Cutoff d2",
        "description": "Разделение пакета в сочетании с поддельным тестовым QUIC-пакетом.",
        "author": "Community",
        "label": None,
        "args": f"""--ipset=ipset-discord.txt --dpi-desync=fake,split2 --dpi-desync-any-protocol --dpi-desync-cutoff=d2 --dpi-desync-fake-quic=quic_test_00.bin --new"""
    },
    "fake_any_proto_google_quic_cutoff_n2": {
        "name": "Fake, Any Proto, Google QUIC, Cutoff n2",
        "description": "Поддельный QUIC-пакет от Google с обрезкой n2.",
        "author": "Community",
        "label": LABEL_RECOMMENDED,
        "args": f"""--ipset=ipset-discord.txt --dpi-desync=fake --dpi-desync-any-protocol --dpi-desync-cutoff=n2 --dpi-desync-fake-quic=quic_initial_www_google_com.bin --new"""
    },
    "fake_any_proto_google_quic_cutoff_d3_repeats_6": {
        "name": "Fake, Any Proto, Google QUIC, Cutoff d3, Repeats 6",
        "description": "Поддельный QUIC от Google с 6 повторениями и обрезкой d3.",
        "author": "Community",
        "label": None,
        "args": f"""--ipset=ipset-discord.txt --dpi-desync=fake --dpi-desync-any-protocol --dpi-desync-cutoff=d3 --dpi-desync-repeats=6 --dpi-desync-fake-quic=quic_initial_www_google_com.bin --new"""
    },
    "fake_tamper_any_proto_google_quic_cutoff_d3_repeats_6": {
        "name": "Fake, Tamper, Google QUIC, Cutoff d3, Repeats 6",
        "description": "Комбинация Fake и Tamper с QUIC от Google, 6 повторениями и обрезкой d3.",
        "author": "Community",
        "label": None,
        "args": f"""--ipset=ipset-discord.txt --dpi-desync=fake,tamper --dpi-desync-any-protocol --dpi-desync-cutoff=d3 --dpi-desync-repeats=6 --dpi-desync-fake-quic=quic_initial_www_google_com.bin --new"""
    },
    "fake_tamper_any_proto_google_quic_cutoff_n5_repeats_10": {
        "name": "Fake, Tamper, Google QUIC, Cutoff n5, Repeats 10",
        "description": "Агрессивная стратегия с 10 повторениями и обрезкой n5.",
        "author": "Community",
        "label": None,
        "args": f"""--ipset=ipset-discord.txt --dpi-desync=fake,tamper --dpi-desync-any-protocol --dpi-desync-cutoff=n5 --dpi-desync-repeats=10 --dpi-desync-fake-quic=quic_initial_www_google_com.bin --new"""
    },
    "fake_tamper_any_proto_google_quic_cutoff_n4": {
        "name": "Fake, Tamper, Google QUIC, Cutoff n4",
        "description": "Комбинация Fake и Tamper с QUIC от Google и обрезкой n4.",
        "author": "Community",
        "label": None,
        "args": f"""--ipset=ipset-discord.txt --dpi-desync=fake,tamper --dpi-desync-any-protocol --dpi-desync-cutoff=n4 --dpi-desync-fake-quic=quic_initial_www_google_com.bin"""
    },
    "discord_voice_udp_none": {
        "name": "Не применять для Discord Voice",
        "description": "Отключить обработку голосовых чатов Discord.",
        "author": "System",
        "label": None,
        "args": ""
    }
}

DISCORD_UPD_STRATEGIES = {
    "fake_6_google": {
        "name": "general (alt v2) 1.6.1",
        "description": "Стандартная стратегия для Discord Voice",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""--filter-udp=443 --hostlist=discord.txt --dpi-desync=fake --dpi-desync-repeats=6 --dpi-desync-fake-quic=quic_initial_www_google_com.bin --new"""
    },
    "fake_6_1": {
        "name": "fake 6 quic 1",
        "description": "Стандартная стратегия для Discord Voice с другим Fake QUIC",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""--filter-udp=443 --hostlist=discord.txt --dpi-desync=fake --dpi-desync-repeats=6 --dpi-desync-fake-quic=quic_1.bin --new"""
    },
    "fake_6_vk_com": {
        "name": "fake 6 quic vk.com",
        "description": "Стандартная стратегия для Discord Voice с другим QUIC от VK",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""--filter-udp=443 --hostlist=discord.txt --dpi-desync=fake --dpi-desync-repeats=6 --dpi-desync-fake-quic=quic_initial_vk_com.bin --new"""
    },
    "fake_8_google": {
        "name": "fake 8 google",
        "description": "Стандартная стратегия для Discord Voice",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""--filter-udp=443 --hostlist=discord.txt --dpi-desync=fake --dpi-desync-repeats=8 --dpi-desync-fake-quic=quic_initial_www_google_com.bin --new"""
    },
    "fake_10_pattern": {
        "name": "fake 10 pattern",
        "description": "Стандартная стратегия для Discord Voice с доп. улучшениями",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""--filter-udp=443 --hostlist=discord.txt --dpi-desync=fake --dpi-desync-udplen-increment=10 --dpi-desync-repeats=6 --dpi-desync-udplen-pattern=0xDEADBEEF --dpi-desync-fake-quic=quic_initial_www_google_com.bin --new"""
    },
    "fake_udplen": {
        "name": "fake udplen 7",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""--filter-udp=443 --hostlist=discord.txt --dpi-desync=fake,udplen --dpi-desync-udplen-increment=5 --dpi-desync-udplen-pattern=0xDEADBEEF --dpi-desync-fake-quic=quic_2.bin --dpi-desync-repeats=7 --dpi-desync-cutoff=n2 --new"""
    },
    "fake_updlen_7_quic_cutoff": {
        "name": "fake udplen 7 quic cutoff",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""--filter-udp=443 --hostlist=discord.txt --dpi-desync=fake --dpi-desync-udplen-increment=10 --dpi-desync-repeats=7 --dpi-desync-udplen-pattern=0xDEADBEEF --dpi-desync-fake-quic=quic_test_00.bin --dpi-desync-cutoff=n2 --new"""
    },
    "fake_updlen_7_quic_google": {
        "name": "fake udplen 7 quic google",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""--filter-udp=443 --hostlist=discord.txt --dpi-desync=fake --dpi-desync-udplen-increment=10 --dpi-desync-repeats=7 --dpi-desync-udplen-pattern=0xDEADBEEF --dpi-desync-fake-quic=quic_initial_www_google_com.bin --new"""
    },
    "fake_updlen_10_pattern": {
        "name": "fake udplen 10 pattern",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""--filter-udp=443 --hostlist=discord.txt --dpi-desync=fake --dpi-desync-udplen-increment=10 --dpi-desync-udplen-pattern=0xDEADBEEF --dpi-desync-fake-quic=quic_2.bin --dpi-desync-repeats=8 --dpi-desync-cutoff=n2 --new"""
    },
    "fake_split2_repeats_6": {
        "name": "fake split2 repeats 6",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""--filter-udp=443 --hostlist=discord.txt --dpi-desync=fake,split2 --dpi-desync-udplen-increment=10 --dpi-desync-repeats=6 --dpi-desync-udplen-pattern=0xDEADBEEF --dpi-desync-fake-quic=quic_initial_www_google_com.bin --new"""
    },
    "fake_split2_repeats_11": {
        "name": "fake split2 repeats 11",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""--filter-udp=443 --hostlist=discord.txt --dpi-desync=fake,split2 --dpi-desync-repeats=11 --dpi-desync-udplen-increment=15 --dpi-desync-fake-quic=quic_initial_www_google_com.bin --new"""
    },
    "discord_voice_udp_none": {
        "name": "Не применять для Discord",
        "description": "Отключить обработку Discord",
        "author": "System",
        "label": None,
        "args": ""
    }
}

def combine_strategies(youtube_id: str, youtube_udp_id: str, googlevideo_id: str, discord_id: str, discord_voice_id: str, rutracker_tcp_id: str, ntcparty_tcp_id: str, twitch_tcp_id: str, other_id: str, ipset_id: str = None, ipset_udp_id: str = None) -> dict:
    """
    Объединяет выбранные стратегии в одну общую
        
    Returns:
        Словарь с объединенной стратегией
    """
    from log import log
    
    # Получаем выбранные базовые аргументы
    from strategy_menu import get_base_args_selection
    base_args_type = get_base_args_selection()
    
    # Словарь базовых аргументов
    BASE_ARGS_OPTIONS = {
        "windivert_all": "--wf-raw=@windivert.all.txt",
        "wf-l3": "--wf-l3=ipv4,ipv6 --wf-tcp=80,443 --wf-udp=443,50000-50100",
        "wf-l3-all": "--wf-l3=ipv4,ipv6 --wf-tcp=80,443,444-65535 --wf-udp=443,444-65535",
        "none": ""
    }
    
    base_args = BASE_ARGS_OPTIONS.get(base_args_type, BASE_ARGS_OPTIONS["windivert_all"])
    
    # Собираем аргументы
    args_parts = []
    if base_args:  # Добавляем только если не пустая строка
        args_parts.append(base_args)
    # Безопасная функция для получения аргументов стратегии
    def safe_get_strategy_args(strategy_dict, strategy_id, category_name):
        if not strategy_id:
            return None
        
        if strategy_id not in strategy_dict:
            log(f"Стратегия '{strategy_id}' не найдена в категории '{category_name}'", "⚠ WARNING")
            log(f"Доступные стратегии в '{category_name}': {list(strategy_dict.keys())}", "DEBUG")
            return None
        
        try:
            args = strategy_dict[strategy_id].get("args", "")
            return args if args else None
        except Exception as e:
            log(f"Ошибка получения аргументов для '{strategy_id}': {e}", "❌ ERROR")
            return None

    # Добавляем GoogleVideo стратегию
    googlevideo_args = safe_get_strategy_args(GOOGLEVIDEO_STRATEGIES, googlevideo_id, "GoogleVideo")
    if googlevideo_args:
        args_parts.append(googlevideo_args)

    # Добавляем YouTube стратегию
    youtube_args = safe_get_strategy_args(YOUTUBE_TCP_STRATEGIES, youtube_id, "YouTube TCP")
    if youtube_args:
        args_parts.append(youtube_args)

    # Добавляем YouTube QUIC стратегию
    youtube_quic_args = safe_get_strategy_args(YOUTUBE_QUIC_STRATEGIES, youtube_udp_id, "YouTube QUIC")
    if youtube_quic_args:
        args_parts.append(youtube_quic_args)

    # Добавляем Discord стратегию
    discord_args = safe_get_strategy_args(DISCORD_STRATEGIES, discord_id, "Discord")
    if discord_args:
        args_parts.append(discord_args)
    
    # Добавляем Discord Voice стратегию
    discord_voice_args = safe_get_strategy_args(DISCORD_VOICE_STRATEGIES, discord_voice_id, "Discord Voice")
    if discord_voice_args:
        args_parts.append(discord_voice_args)

    # Добавляем Rutracker TCP стратегию
    rutracker_tcp_args = safe_get_strategy_args(RUTRACKER_TCP_STRATEGIES, rutracker_tcp_id, "Rutracker TCP")
    if rutracker_tcp_args:
        args_parts.append(rutracker_tcp_args)

    # Добавляем NtcParty TCP стратегию
    ntcparty_tcp_args = safe_get_strategy_args(NTCPARTY_TCP_STRATEGIES, ntcparty_tcp_id, "NtcParty TCP")
    if ntcparty_tcp_args:
        args_parts.append(ntcparty_tcp_args)

    # Добавляем Twitch TCP стратегию
    twitch_tcp_args = safe_get_strategy_args(TWITCH_TCP_STRATEGIES, twitch_tcp_id, "Twitch TCP")
    if twitch_tcp_args:
        args_parts.append(twitch_tcp_args)

    # Добавляем стратегию для остальных сайтов
    other_args = safe_get_strategy_args(OTHER_STRATEGIES, other_id, "Other")
    if other_args:
        args_parts.append(other_args)

    # IPset
    ipset_args = safe_get_strategy_args(IPSET_TCP_STRATEGIES, ipset_id, "IPset TCP")
    if ipset_args:
        args_parts.append(ipset_args)

    # UDP IPset
    ipset_udp_args = safe_get_strategy_args(IPSET_UDP_STRATEGIES, ipset_udp_id, "IPset UDP")
    if ipset_udp_args:
        args_parts.append(ipset_udp_args)

    # Объединяем все части через пробел
    combined_args = " ".join(args_parts)
    
    # Безопасная функция для получения имени стратегии
    def safe_get_strategy_name(strategy_dict, strategy_id):
        if not strategy_id or strategy_id not in strategy_dict:
            return None
        try:
            return strategy_dict[strategy_id].get('name', strategy_id)
        except:
            return strategy_id
    
    # Формируем описание
    descriptions = []
    if youtube_id and youtube_id != "youtube_tcp_none":
        name = safe_get_strategy_name(YOUTUBE_TCP_STRATEGIES, youtube_id)
        if name:
            descriptions.append(f"YouTube: {name}")
    
    if youtube_udp_id and youtube_udp_id != "youtube_quic_none":
        name = safe_get_strategy_name(YOUTUBE_QUIC_STRATEGIES, youtube_udp_id)
        if name:
            descriptions.append(f"YouTube QUIC: {name}")
    
    if discord_id and discord_id != "discord_tcp_none":
        name = safe_get_strategy_name(DISCORD_STRATEGIES, discord_id)
        if name:
            descriptions.append(f"Discord: {name}")
    
    if googlevideo_id and googlevideo_id != "googlevideo_tcp_none":
        name = safe_get_strategy_name(GOOGLEVIDEO_STRATEGIES, googlevideo_id)
        if name:
            descriptions.append(f"GoogleVideo: {name}")
    
    if discord_voice_id and discord_voice_id != "discord_voice_udp_none":
        name = safe_get_strategy_name(DISCORD_VOICE_STRATEGIES, discord_voice_id)
        if name:
            descriptions.append(f"Discord Voice: {name}")
    
    if rutracker_tcp_id and rutracker_tcp_id != "rutracker_tcp_none":
        name = safe_get_strategy_name(RUTRACKER_TCP_STRATEGIES, rutracker_tcp_id)
        if name:
            descriptions.append(f"Rutracker TCP: {name}")

    if ntcparty_tcp_id and ntcparty_tcp_id != "ntcparty_tcp_none":
        name = safe_get_strategy_name(NTCPARTY_TCP_STRATEGIES, ntcparty_tcp_id)
        if name:
            descriptions.append(f"NtcParty TCP: {name}")
    
    if twitch_tcp_id and twitch_tcp_id != "twitch_tcp_none":
        name = safe_get_strategy_name(TWITCH_TCP_STRATEGIES, twitch_tcp_id)
        if name:
            descriptions.append(f"Twitch TCP: {name}")
    
    if other_id and other_id != "other_tcp_none":
        name = safe_get_strategy_name(OTHER_STRATEGIES, other_id)
        if name:
            descriptions.append(f"Остальные: {name}")
    
    if ipset_id and ipset_id != "ipset_tcp_none":
        name = safe_get_strategy_name(IPSET_TCP_STRATEGIES, ipset_id)
        if name:
            descriptions.append(f"IPset: {name}")
    
    if ipset_udp_id and ipset_udp_id != "ipset_udp_none":
        name = safe_get_strategy_name(IPSET_UDP_STRATEGIES, ipset_udp_id)
        if name:
            descriptions.append(f"IPset UDP: {name}")

    combined_description = " | ".join(descriptions) if descriptions else "Пользовательская комбинация"
    
    log(f"Создана комбинированная стратегия с аргументами: {combined_args}", "DEBUG")
    
    return {
        "name": "Комбинированная стратегия",
        "description": combined_description,
        "version": "1.0",
        "provider": "universal",
        "author": "Combined",
        "updated": "2024",
        "label": LABEL_STABLE,
        "all_sites": True,
        "args": combined_args,
        "_is_builtin": True,
        "_youtube_id": youtube_id,
        "_youtube_udp_id": youtube_udp_id,
        "_googlevideo_id": googlevideo_id,
        "_discord_id": discord_id,
        "_discord_voice_id": discord_voice_id,
        "_rutracker_tcp_id": rutracker_tcp_id,
        "_ntcparty_tcp_id": ntcparty_tcp_id,
        "_twitch_tcp_id": twitch_tcp_id,
        "_other_id": other_id,
        "_ipset_id": ipset_id,
        "_ipset_udp_id": ipset_udp_id
    }


def get_default_selections():
    """Возвращает стратегии по умолчанию для каждой категории"""
    return {
        'youtube': 'multisplit_seqovl_midsld',
        'youtube_udp': 'fake_11',
        'googlevideo_tcp': 'googlevideo_tcp_none',
        'discord': 'dis4',
        'discord_voice_udp': 'ipv4_dup2_autottl_cutoff_n3',
        'rutracker_tcp': 'rutracker_tcp_none',
        'ntcparty_tcp': 'original_bolvan_v2_badsum',
        'twitch_tcp': 'twitch_tcp_none',
        'other': 'other_seqovl',
        'ipset': 'other_seqovl',
        'ipset_udp': 'fake_2_n2_google'
    }
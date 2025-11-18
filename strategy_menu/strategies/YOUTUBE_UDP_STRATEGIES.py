from ..constants import LABEL_RECOMMENDED, LABEL_CAUTION, LABEL_EXPERIMENTAL, LABEL_STABLE

# 80 порт не используется для QUIC, только 443 UDP
YOUTUBE_BASE_ARG_UDP = "--filter-udp=443 --hostlist=youtube.txt"

YOUTUBE_QUIC_STRATEGIES = {
    "fake_11": {
        "name": "fake 11 повторов",
        "description": "Базовая стратегия с 11 повторами fake пакетов",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""{YOUTUBE_BASE_ARG_UDP} --dpi-desync=fake --dpi-desync-repeats=11"""
    },
    "fake_2_quic_test_00": {
        "name": "fake 2 повторов quic_test_00",
        "description": "2 повтора с тестовым QUIC пакетом",
        "author": "hz",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG_UDP} --dpi-desync=fake --dpi-desync-repeats=2 --dpi-desync-cutoff=n2 --dpi-desync-fake-quic=quic_test_00.bin"""
    },
    "fake_11_quic_bin": {
        "name": "fake 11 повторов (Google QUIC)",
        "description": "11 повтора с Google QUIC и cutoff после 11 пакетов",
        "author": "hz",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG_UDP} --dpi-desync=fake --dpi-desync-repeats=11 --dpi-desync-fake-quic=quic_initial_www_google_com.bin"""
    },
    "fake_2_n2": {
        "name": "fake 2 повторов (Google QUIC) cutoff=n2",
        "description": "2 повтора с Google QUIC и cutoff после 2 пакетов",
        "author": "hz",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG_UDP} --dpi-desync=fake --dpi-desync-repeats=2 --dpi-desync-cutoff=n2 --dpi-desync-fake-quic=quic_initial_www_google_com.bin"""
    },
    "fake_repeat_2_quic": {
        "name": "fake 2 повторов (Google QUIC) cutoff=n2",
        "description": "2 повтора с Google QUIC и cutoff после 2 пакетов",
        "author": "hz",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG_UDP} --hostlist-domains=youtube.com,youtu.be,ytimg.com,googlevideo.com,googleapis.com,gvt1.com,video.google.com --dpi-desync=fake --dpi-desync-repeats=2 --dpi-desync-fake-quic=fake_quic.bin"""
    },
    
    "fake_4_google": {
        "name": "fake 4 повтора (Google QUIC)",
        "description": "4 повтора с fake QUIC пакетом Google",
        "author": "hz",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG_UDP} --dpi-desync=fake --dpi-desync-repeats=4 --dpi-desync-fake-quic=quic_initial_www_google_com.bin"""
    },
    
    "fake_4_quic1": {
        "name": "fake 4 повтора (QUIC 1)",
        "description": "4 повтора с альтернативным QUIC пакетом",
        "author": "hz",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG_UDP} --dpi-desync=fake --dpi-desync-repeats=4 --dpi-desync-fake-quic=quic_1.bin"""
    },
    
    "fake_15_ttl0_md5sig": {
        "name": "fake 15 повторов TTL=0 (md5sig+badsum)",
        "description": "Агрессивная стратегия с 15 повторами, TTL=0 и двумя методами fooling",
        "author": "hz",
        "label": LABEL_EXPERIMENTAL,
        "args": f"""{YOUTUBE_BASE_ARG_UDP} --dpi-desync=fake --dpi-desync-repeats=15 --dpi-desync-ttl=0 --dpi-desync-any-protocol --dpi-desync-cutoff=d4 --dpi-desync-fooling=md5sig,badsum --dpi-desync-fake-quic=quic_initial_www_google_com.bin"""
    },
    
    "fake_15_ttl0_badsum": {
        "name": "fake 15 повторов TTL=0 (badsum)",
        "description": "Агрессивная стратегия с 15 повторами, TTL=0 и badsum",
        "author": "hz",
        "label": LABEL_EXPERIMENTAL,
        "args": f"""{YOUTUBE_BASE_ARG_UDP} --dpi-desync=fake --dpi-desync-repeats=15 --dpi-desync-ttl=0 --dpi-desync-any-protocol --dpi-desync-cutoff=d4 --dpi-desync-fooling=badsum --dpi-desync-fake-quic=quic_initial_www_google_com.bin"""
    },
    
    "fake_6_google": {
        "name": "fake 6 повторов (Google QUIC)",
        "description": "6 повторов с fake QUIC пакетом Google",
        "author": "hz",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG_UDP} --dpi-desync=fake --dpi-desync-fake-quic=quic_initial_www_google_com.bin --dpi-desync-repeats=6"""
    },
    
    "fake_ipfrag2_quic5": {
        "name": "fake+ipfrag2 (QUIC 5)",
        "description": "Комбинация fake и ipfrag2 с QUIC 5",
        "author": "hz",
        "label": LABEL_STABLE,
        "args": f"""{YOUTUBE_BASE_ARG_UDP} --dpi-desync=fake,ipfrag2 --dpi-desync-fake-quic=quic_5.bin --dpi-desync-cutoff=n3 --dpi-desync-repeats=3"""
    },
    
    "fake_ipfrag2_quic3": {
        "name": "fake+ipfrag2 (QUIC 3)",
        "description": "Комбинация fake и ipfrag2 с QUIC 3",
        "author": "hz",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG_UDP} --dpi-desync=fake,ipfrag2 --dpi-desync-fake-quic=quic_3.bin --dpi-desync-cutoff=n3 --dpi-desync-repeats=2"""
    },
    
    "fake_ipfrag2_quic7": {
        "name": "fake+ipfrag2 (QUIC 7)",
        "description": "Комбинация fake и ipfrag2 с QUIC 7",
        "author": "hz",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG_UDP} --dpi-desync=fake,ipfrag2 --dpi-desync-fake-quic=quic_7.bin --dpi-desync-cutoff=n3 --dpi-desync-repeats=3"""
    },
    
    "fake_udplen_inc2": {
        "name": "fake+udplen increment=2",
        "description": "UDP длина +2 с QUIC 3",
        "author": "hz",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG_UDP} --dpi-desync=fake,udplen --dpi-desync-udplen-increment=2 --dpi-desync-fake-quic=quic_3.bin --dpi-desync-cutoff=n3 --dpi-desync-repeats=2"""
    },
    
    "fake_udplen_inc4_quic3": {
        "name": "fake+udplen increment=4 (QUIC 3)",
        "description": "UDP длина +4 с QUIC 3",
        "author": "hz",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG_UDP} --dpi-desync=fake,udplen --dpi-desync-udplen-increment=4 --dpi-desync-fake-quic=quic_3.bin --dpi-desync-cutoff=n3 --dpi-desync-repeats=2"""
    },
    
    "fake_udplen_inc4_quic4": {
        "name": "fake+udplen increment=4 (QUIC 4)",
        "description": "UDP длина +4 с QUIC 4",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""{YOUTUBE_BASE_ARG_UDP} --dpi-desync=fake,udplen --dpi-desync-udplen-increment=4 --dpi-desync-fake-quic=quic_4.bin --dpi-desync-cutoff=n3 --dpi-desync-repeats=2"""
    },
    
    "fake_udplen_pattern_0F0F": {
        "name": "fake+udplen pattern 0x0F0F0E0F",
        "description": "UDP с паттерном 0x0F0F0E0F и QUIC 6",
        "author": "hz",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG_UDP} --dpi-desync=fake,udplen --dpi-desync-udplen-increment=8 --dpi-desync-udplen-pattern=0x0F0F0E0F --dpi-desync-fake-quic=quic_6.bin --dpi-desync-cutoff=n3 --dpi-desync-repeats=2"""
    },
    
    "fake_udplen_pattern_0F0F_autottl": {
        "name": "fake+udplen pattern 0x0F0F0E0F (AutoTTL)",
        "description": "UDP с паттерном 0x0F0F0E0F, QUIC 6 и AutoTTL",
        "author": "hz",
        "label": LABEL_EXPERIMENTAL,
        "args": f"""{YOUTUBE_BASE_ARG_UDP} --dpi-desync=fake,udplen --dpi-desync-udplen-increment=8 --dpi-desync-udplen-pattern=0x0F0F0E0F --dpi-desync-fake-quic=quic_6.bin --dpi-desync-cutoff=n3 --dpi-desync-repeats=2 --dpi-desync-autottl"""
    },
    
    "fake_udplen_pattern_0E0F": {
        "name": "fake+udplen pattern 0x0E0F0E0F",
        "description": "UDP с паттерном 0x0E0F0E0F и QUIC 7",
        "author": "hz",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG_UDP} --dpi-desync=fake,udplen --dpi-desync-udplen-increment=8 --dpi-desync-udplen-pattern=0x0E0F0E0F --dpi-desync-fake-quic=quic_7.bin --dpi-desync-cutoff=n3 --dpi-desync-repeats=2"""
    },
    
    "fake_udplen_pattern_FEA8": {
        "name": "fake+udplen pattern 0xFEA82025",
        "description": "UDP с паттерном 0xFEA82025 и QUIC 4",
        "author": "hz",
        "label": LABEL_CAUTION,
        "args": f"""{YOUTUBE_BASE_ARG_UDP} --dpi-desync=fake,udplen --dpi-desync-udplen-increment=8 --dpi-desync-udplen-pattern=0xFEA82025 --dpi-desync-fake-quic=quic_4.bin --dpi-desync-cutoff=n4 --dpi-desync-repeats=2"""
    },
    
    "fake_udplen_inc25": {
        "name": "fake+udplen increment=25",
        "description": "UDP длина +25 с QUIC 5",
        "author": "hz",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG_UDP} --dpi-desync=fake,udplen --dpi-desync-udplen-increment=25 --dpi-desync-fake-quic=quic_5.bin --dpi-desync-repeats=2 --dpi-desync-cutoff=n3"""
    },
    
    "fake_split2_udplen25": {
        "name": "fake+split2 udplen=25",
        "description": "Комбинация fake и split2 с UDP длиной +25",
        "author": "hz",
        "label": LABEL_EXPERIMENTAL,
        "args": f"""{YOUTUBE_BASE_ARG_UDP} --dpi-desync=fake,split2 --dpi-desync-repeats=10 --dpi-desync-udplen-increment=25 --dpi-desync-fake-quic=quic_initial_www_google_com.bin"""
    },
    
    "fake_tamper_google": {
        "name": "fake+tamper (Google QUIC)",
        "description": "Комбинация fake и tamper с Google QUIC",
        "author": "hz",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG_UDP} --dpi-desync=fake,tamper --dpi-desync-repeats=11 --dpi-desync-fake-quic=quic_initial_www_google_com.bin"""
    },
    
    "fake_tamper_autottl": {
        "name": "fake+tamper (AutoTTL=2)",
        "description": "Комбинация fake и tamper с AutoTTL=2",
        "author": "hz",
        "label": LABEL_STABLE,
        "args": f"""{YOUTUBE_BASE_ARG_UDP} --dpi-desync=fake,tamper --dpi-desync-autottl=2 --dpi-desync-repeats=11"""
    },
    "youtube_udp_none": {
        "name": "Не применять для YouTube QUIC",
        "description": "Отключить обработку YouTube QUIC",
        "author": "System",
        "label": None,
        "args": ""  # Пустая строка = не добавлять аргументы
    }
}
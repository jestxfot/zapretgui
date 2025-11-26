"""
Базовые UDP техники обхода DPI.
Только DPI-аргументы! Фильтры берутся из CATEGORIES_REGISTRY.base_filter
"""

from ..constants import LABEL_RECOMMENDED, LABEL_STABLE, LABEL_GAME, LABEL_EXPERIMENTAL

UDP_STRATEGIES_BASE = {
    # ============== УНИВЕРСАЛЬНАЯ NONE СТРАТЕГИЯ ==============
    "none": {
        "name": "⛔ Отключено",
        "description": "Обход DPI отключен для этой категории",
        "author": "System",
        "label": None,
        "args": ""
    },

    # ============== ТЕХНИКИ DPI ==============
    "dronator_43": {
        "name": "Dronator 4.3",
        "description": "fake stun 0x0",
        "author": "Dronator",
        "label": LABEL_STABLE,
        "args": f"""--dpi-desync=fake --dpi-desync-fake-stun=0x00"""
    },
    "fake_2_n2_google": {
        "name": "fake_2_n2_google",
        "description": "Базовая стратегия для многих игр",
        "author": "community",
        "label": LABEL_GAME,
        "args": f"""--dpi-desync-any-protocol --dpi-desync=fake --dpi-desync-repeats=6 --dpi-desync-cutoff=n2 --dpi-desync-fake-unknown-udp=quic_initial_www_google_com.bin"""
    },
   "fake_2_n2_test": {
        "name": "fake_2_n2_test",
        "description": "2 повтора с quic_test_00.bin, cutoff n2",
        "author": "community",
        "label": LABEL_RECOMMENDED,
        "args": f"""--dpi-desync=fake --dpi-desync-repeats=2 --dpi-desync-cutoff=n2 --dpi-desync-fake-unknown-udp=quic_initial_www_google_com.bin"""
    },
    "fake_4_google": {
        "name": "Fake x4 Google",
        "description": "4 повтора с Google QUIC",
        "author": "community",
        "label": None,
        "args": f"""--dpi-desync=fake --dpi-desync-repeats=4 --dpi-desync-fake-unknown-udp=quic_initial_www_google_com.bin"""
    },
    "fake_4_quic1": {
        "name": "Fake x4 QUIC1",
        "description": "4 повтора с quic_1.bin",
        "author": "community",
        "label": None,
        "args": f"""--dpi-desync=fake --dpi-desync-repeats=4 --dpi-desync-fake-quic=quic_1.bin"""
    },
    "ipset_fake_12_n2": {
        "name": "ipset_fake_12_n2",
        "description": "UDP 443+ с ipset-all, 12 повторов, cutoff n2",
        "author": "community",
        "label": LABEL_GAME,
        "args": f"""--dpi-desync-any-protocol --dpi-desync=fake --dpi-desync-repeats=6 --dpi-desync-cutoff=d3 --dpi-desync-fake-unknown-udp=quic_initial_www_google_com.bin"""
    },
   "general_bf_32": {
        "name": "General-BF 3.2",
        "description": "Для Battlefield 6",
        "author": "community",
        "label": LABEL_RECOMMENDED,
        "args": f"""--dpi-desync=fake --dpi-desync-any-protocol=1 --dpi-desync-autottl=2 --dpi-desync-repeats=9 --dpi-desync-fake-unknown-udp=quic_initial_www_google_com.bin --dpi-desync-cutoff=n2"""
    },
    "ipset_fake_12_n2": {
        "name": "Apex legends & Rockstar v2",
        "description": "UDP 443+ с ipset-all, 12 повторов, cutoff n2",
        "author": "community",
        "label": LABEL_GAME,
        "args": f"""--dpi-desync=fake --dpi-desync-autottl=2 --dpi-desync-repeats=12 --dpi-desync-any-protocol=1 --dpi-desync-fake-unknown-udp=quic_initial_www_google_com.bin --dpi-desync-cutoff=n2"""
    },
    "ipset_fake_12_n3": {
        "name": "IPSET Fake x12 N3 (Apex legends & Battlefield 6)",
        "description": "UDP 443+ с ipset-all, 12 повторов, cutoff n3",
        "author": "community",
        "label": LABEL_GAME,
        "args": f"""--dpi-desync=fake --dpi-desync-autottl=2 --dpi-desync-repeats=12 --dpi-desync-any-protocol=1 --dpi-desync-fake-unknown-udp=quic_initial_www_google_com.bin --dpi-desync-cutoff=n3"""
    },
    "ipset_fake_10_n2": {
        "name": "IPSET Fake x10 N2 (Apex legends & Battlefield 6)",
        "description": "UDP 443+ с ipset-all, 10 повторов, cutoff n2",
        "author": "community",
        "label": LABEL_GAME,
        "args": f"""--dpi-desync=fake --dpi-desync-autottl=2 --dpi-desync-repeats=10 --dpi-desync-any-protocol=1 --dpi-desync-fake-unknown-udp=quic_initial_www_google_com.bin --dpi-desync-cutoff=n2"""
    },
    "ipset_fake_14_n3": {
        "name": "IPSET Fake x14 N3 (Apex legends)",
        "description": "UDP 443+ с ipset-all, 14 повторов, cutoff n3",
        "author": "community",
        "label": LABEL_GAME,
        "args": f"""--dpi-desync=fake --dpi-desync-autottl=2 --dpi-desync-repeats=14 --dpi-desync-any-protocol=1 --dpi-desync-fake-unknown-udp=quic_initial_www_google_com.bin --dpi-desync-cutoff=n3"""
    },
    "ipset_fake_tamper_11": {
        "name": "IPSET Fake+Tamper x11",
        "description": "UDP 443+ с ipset-all, fake+tamper, 11 повторов",
        "author": "community",
        "label": LABEL_GAME,
        "args": f"""--dpi-desync=fake,tamper --dpi-desync-any-protocol --dpi-desync-autottl=2 --dpi-desync-repeats=11"""
    },
    "ipset_fake_quic6_ttl7": {
        "name": "IPSET Fake QUIC6 TTL7",
        "description": "UDP 443+ с ipset-all, quic_6.bin, TTL 7",
        "author": "community",
        "label": LABEL_GAME,
        "args": f"""--dpi-desync=fake --dpi-desync-any-protocol --dpi-desync-fake-unknown-udp=quic_6.bin --dpi-desync-repeats=2 --dpi-desync-cutoff=n4 --dpi-desync-ttl=7"""
    },
   "fake_2_n2_test_2": {
        "name": "Rockstar v3",
        "description": "2 повтора с quic_test_00.bin, cutoff n2",
        "author": "community",
        "label": LABEL_RECOMMENDED,
        "args": f"""--dpi-desync=fake --dpi-desync-repeats=2 --dpi-desync-cutoff=n2 --dpi-desync-fake-quic=quic_test_00.bin"""
    },
    "fake_11_simple": {
        "name": "Fake x11 Simple",
        "description": "Простая стратегия с 11 повторами fake",
        "author": "community",
        "label": LABEL_STABLE,
        "args": f"""--dpi-desync=fake --dpi-desync-repeats=11"""
    },
    "fake_15_ttl0_md5sig": {
        "name": "Fake x15 TTL0 MD5sig",
        "description": "15 повторов, TTL 0, md5sig+badsum",
        "author": "community",
        "label": None,
        "args": f"""--dpi-desync=fake --dpi-desync-repeats=15 --dpi-desync-ttl=0 --dpi-desync-any-protocol --dpi-desync-cutoff=d4 --dpi-desync-fooling=md5sig,badsum --dpi-desync-fake-quic=quic_initial_www_google_com.bin"""
    },
    "fake_15_ttl0_badsum": {
        "name": "Fake x15 TTL0 Badsum",
        "description": "15 повторов, TTL 0, только badsum",
        "author": "community",
        "label": None,
        "args": f"""--dpi-desync=fake --dpi-desync-repeats=15 --dpi-desync-ttl=0 --dpi-desync-any-protocol --dpi-desync-cutoff=d4 --dpi-desync-fooling=badsum --dpi-desync-fake-quic=quic_initial_www_google_com.bin"""
    },
    "fake_6_google": {
        "name": "Fake x6 Google",
        "description": "6 повторов с Google QUIC",
        "author": "community",
        "label": None,
        "args": f"""--dpi-desync=fake --dpi-desync-fake-quic=quic_initial_www_google_com.bin --dpi-desync-repeats=6"""
    },
    "fake_ipfrag2_quic5": {
        "name": "Fake+IPFrag2 QUIC5",
        "description": "Fake с IP фрагментацией, quic_5.bin",
        "author": "community",
        "label": None,
        "args": f"""--dpi-desync=fake,ipfrag2 --dpi-desync-fake-quic=quic_5.bin --dpi-desync-cutoff=n3 --dpi-desync-repeats=3"""
    },
    "fake_ipfrag2_quic3": {
        "name": "Fake+IPFrag2 QUIC3",
        "description": "Fake с IP фрагментацией, quic_3.bin",
        "author": "community",
        "label": None,
        "args": f"""--dpi-desync=fake,ipfrag2 --dpi-desync-fake-quic=quic_3.bin --dpi-desync-cutoff=n3 --dpi-desync-repeats=2"""
    },
    "fake_ipfrag2_quic7": {
        "name": "Fake+IPFrag2 QUIC7",
        "description": "Fake с IP фрагментацией, quic_7.bin",
        "author": "community",
        "label": None,
        "args": f"""--dpi-desync=fake,ipfrag2 --dpi-desync-fake-quic=quic_7.bin --dpi-desync-cutoff=n3 --dpi-desync-repeats=3"""
    },
    "fake_udplen_2_quic3": {
        "name": "Fake+UDPLen+2 QUIC3",
        "description": "Fake с изменением длины UDP +2",
        "author": "community",
        "label": None,
        "args": f"""--dpi-desync=fake,udplen --dpi-desync-udplen-increment=2 --dpi-desync-fake-quic=quic_3.bin --dpi-desync-cutoff=n3 --dpi-desync-repeats=2"""
    },
    "fake_udplen_4_quic3": {
        "name": "Fake+UDPLen+4 QUIC3",
        "description": "Fake с изменением длины UDP +4, quic_3.bin",
        "author": "community",
        "label": None,
        "args": f"""--dpi-desync=fake,udplen --dpi-desync-udplen-increment=4 --dpi-desync-fake-quic=quic_3.bin --dpi-desync-cutoff=n3 --dpi-desync-repeats=2"""
    },
    "fake_udplen_4_quic4": {
        "name": "Fake+UDPLen+4 QUIC4",
        "description": "Fake с изменением длины UDP +4, quic_4.bin",
        "author": "community",
        "label": None,
        "args": f"""--dpi-desync=fake,udplen --dpi-desync-udplen-increment=4 --dpi-desync-fake-quic=quic_4.bin --dpi-desync-cutoff=n3 --dpi-desync-repeats=2"""
    },
    "fake_udplen_8_pattern1": {
        "name": "Fake+UDPLen+8 Pattern1",
        "description": "UDPLen +8 с паттерном 0x0F0F0E0F",
        "author": "community",
        "label": None,
        "args": f"""--dpi-desync=fake,udplen --dpi-desync-udplen-increment=8 --dpi-desync-udplen-pattern=0x0F0F0E0F --dpi-desync-fake-quic=quic_6.bin --dpi-desync-cutoff=n3 --dpi-desync-repeats=2"""
    },
    "fake_udplen_8_pattern1_autottl": {
        "name": "Fake+UDPLen+8 Pattern1 AutoTTL",
        "description": "UDPLen +8 с паттерном и AutoTTL",
        "author": "community",
        "label": None,
        "args": f"""--dpi-desync=fake,udplen --dpi-desync-udplen-increment=8 --dpi-desync-udplen-pattern=0x0F0F0E0F --dpi-desync-fake-quic=quic_6.bin --dpi-desync-cutoff=n3 --dpi-desync-repeats=2 --dpi-desync-autottl"""
    },
    "fake_udplen_8_pattern2": {
        "name": "Fake+UDPLen+8 Pattern2",
        "description": "UDPLen +8 с паттерном 0x0E0F0E0F",
        "author": "community",
        "label": None,
        "args": f"""--dpi-desync=fake,udplen --dpi-desync-udplen-increment=8 --dpi-desync-udplen-pattern=0x0E0F0E0F --dpi-desync-fake-quic=quic_7.bin --dpi-desync-cutoff=n3 --dpi-desync-repeats=2"""
    },
    "fake_udplen_8_pattern3": {
        "name": "Fake+UDPLen+8 Pattern3",
        "description": "UDPLen +8 с паттерном 0xFEA82025",
        "author": "community",
        "label": None,
        "args": f"""--dpi-desync=fake,udplen --dpi-desync-udplen-increment=8 --dpi-desync-udplen-pattern=0xFEA82025 --dpi-desync-fake-quic=quic_4.bin --dpi-desync-cutoff=n4 --dpi-desync-repeats=2"""
    },
    "fake_udplen_25": {
        "name": "Fake+UDPLen+25",
        "description": "Fake с большим изменением длины UDP +25",
        "author": "community",
        "label": None,
        "args": f"""--dpi-desync=fake,udplen --dpi-desync-udplen-increment=25 --dpi-desync-fake-quic=quic_5.bin --dpi-desync-repeats=2 --dpi-desync-cutoff=n3"""
    },
    "fake_split2_10": {
        "name": "Fake+Split2 x10",
        "description": "Fake со split2, 10 повторов",
        "author": "community",
        "label": None,
        "args": f"""--dpi-desync=fake,split2 --dpi-desync-repeats=10 --dpi-desync-udplen-increment=25 --dpi-desync-fake-quic=quic_initial_www_google_com.bin"""
    },
    "fake_tamper_11": {
        "name": "Fake+Tamper x11",
        "description": "Fake с tamper, 11 повторов",
        "author": "community",
        "label": LABEL_RECOMMENDED,
        "args": f"""--dpi-desync=fake,tamper --dpi-desync-repeats=11 --dpi-desync-fake-quic=quic_initial_www_google_com.bin"""
    },
    "fake_tamper_11_autottl": {
        "name": "Fake+Tamper x11 AutoTTL",
        "description": "Fake с tamper и AutoTTL=2",
        "author": "community",
        "label": LABEL_RECOMMENDED,
        "args": f"""--dpi-desync=fake,tamper --dpi-desync-autottl=2 --dpi-desync-repeats=11"""
    },
    "fake_tamper_11_autottl": {
        "name": "fake_tamper_11_autottl",
        "description": "",
        "author": "community",
        "label": LABEL_GAME,
        "args": f"""--dpi-desync-any-protocol --dpi-desync=fake --dpi-desync-repeats=6 --dpi-desync-cutoff=n15 --dpi-desync-fake-unknown-udp=quic_initial_www_google_com.bin"""
    },
    "fake_11_quic_bin": {
        "name": "fake 11 повторов (Google QUIC)",
        "description": "11 повтора с Google QUIC и cutoff после 11 пакетов",
        "author": "hz",
        "label": None,
        "args": f"""--dpi-desync=fake --dpi-desync-repeats=11 --dpi-desync-fake-quic=quic_initial_www_google_com.bin"""
    },
    "fake_2_n2": {
        "name": "fake 2 повторов (Google QUIC) cutoff=n2",
        "description": "2 повтора с Google QUIC и cutoff после 2 пакетов",
        "author": "hz",
        "label": None,
        "args": f"""--dpi-desync=fake --dpi-desync-repeats=2 --dpi-desync-cutoff=n2 --dpi-desync-fake-quic=quic_initial_www_google_com.bin"""
    },
    "fake_repeat_2_quic": {
        "name": "fake 2 повторов (Google QUIC) cutoff=n2",
        "description": "2 повтора с Google QUIC и cutoff после 2 пакетов",
        "author": "hz",
        "label": None,
        "args": f"""--dpi-desync=fake --dpi-desync-repeats=2 --dpi-desync-fake-quic=fake_quic.bin"""
    },
    
    "fake_4_google": {
        "name": "fake 4 повтора (Google QUIC)",
        "description": "4 повтора с fake QUIC пакетом Google",
        "author": "hz",
        "label": None,
        "args": f"""--dpi-desync=fake --dpi-desync-repeats=4 --dpi-desync-fake-quic=quic_initial_www_google_com.bin"""
    },
    "fake_6_google": {
        "name": "general (alt v2) 1.6.1",
        "description": "Стандартная стратегия для Discord Voice, Rockstar Launcher",
        "author": "Flowseal",
        "label": LABEL_RECOMMENDED,
        "args": f"""--dpi-desync=fake --dpi-desync-repeats=6 --dpi-desync-fake-quic=quic_initial_www_google_com.bin"""
    },
    "fake_6_1": {
        "name": "fake 6 quic 1",
        "description": "Стандартная стратегия с другим Fake QUIC",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""--dpi-desync=fake --dpi-desync-repeats=6 --dpi-desync-fake-quic=quic_1.bin"""
    },
    "fake_6_vk_com": {
        "name": "fake 6 quic vk.com",
        "description": "Стандартная стратегия для Discord Voice с другим QUIC от VK",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""--dpi-desync=fake --dpi-desync-repeats=6 --dpi-desync-fake-quic=quic_initial_vk_com.bin"""
    },
    "fake_8_google": {
        "name": "fake 8 google",
        "description": "Стандартная стратегия для Discord Voice",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""--dpi-desync=fake --dpi-desync-repeats=8 --dpi-desync-fake-quic=quic_initial_www_google_com.bin"""
    },
    "fake_10_pattern": {
        "name": "Ufanet 31.03.2025",
        "description": "Стандартная стратегия для Discord Voice с доп. улучшениями",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""--dpi-desync=fake --dpi-desync-udplen-increment=10 --dpi-desync-repeats=6 --dpi-desync-udplen-pattern=0xDEADBEEF --dpi-desync-fake-quic=quic_initial_www_google_com.bin"""
    },
    "fake_udplen": {
        "name": "YTDis Bystro 2.9.2 v1 / v2",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""--dpi-desync=fake,udplen --dpi-desync-udplen-increment=5 --dpi-desync-udplen-pattern=0xDEADBEEF --dpi-desync-fake-quic=quic_2.bin --dpi-desync-repeats=7 --dpi-desync-cutoff=n2"""
    },
    "fake_updlen_7_quic_cutoff": {
        "name": "fake udplen 7 quic cutoff",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""--dpi-desync=fake --dpi-desync-udplen-increment=10 --dpi-desync-repeats=7 --dpi-desync-udplen-pattern=0xDEADBEEF --dpi-desync-fake-quic=quic_test_00.bin --dpi-desync-cutoff=n2"""
    },
    "fake_updlen_7_quic_google": {
        "name": "fake udplen 7 quic google",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""--dpi-desync=fake --dpi-desync-udplen-increment=10 --dpi-desync-repeats=7 --dpi-desync-udplen-pattern=0xDEADBEEF --dpi-desync-fake-quic=quic_initial_www_google_com.bin"""
    },
    "fake_updlen_10_pattern": {
        "name": "fake udplen 10 pattern",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""--dpi-desync=fake --dpi-desync-udplen-increment=10 --dpi-desync-udplen-pattern=0xDEADBEEF --dpi-desync-fake-quic=quic_2.bin --dpi-desync-repeats=8 --dpi-desync-cutoff=n2"""
    },
    "fake_split2_repeats_6": {
        "name": "fake split2 repeats 6",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""--dpi-desync=fake,split2 --dpi-desync-udplen-increment=10 --dpi-desync-repeats=6 --dpi-desync-udplen-pattern=0xDEADBEEF --dpi-desync-fake-quic=quic_initial_www_google_com.bin"""
    },
    "fake_split2_repeats_11": {
        "name": "fake split2 repeats 11",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""--dpi-desync=fake,split2 --dpi-desync-repeats=11 --dpi-desync-udplen-increment=15 --dpi-desync-fake-quic=quic_initial_www_google_com.bin"""
    }
}
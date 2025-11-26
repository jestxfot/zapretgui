"""
Discord Voice стратегии.
Особый случай - сложные стратегии содержат полные команды с фильтрами,
простые - только технику (base_filter добавится автоматически).
"""

from ..constants import LABEL_RECOMMENDED, LABEL_STABLE, LABEL_GAME, LABEL_EXPERIMENTAL

DISCORD_VOICE_STRATEGIES = {
    # ============== УНИВЕРСАЛЬНАЯ NONE СТРАТЕГИЯ ==============
    "none": {
        "name": "⛔ Отключено",
        "description": "Discord Voice обход отключен",
        "author": "System",
        "label": None,
        "args": ""
    },

    # ============== ПРОСТЫЕ ТЕХНИКИ (base_filter добавится автоматически) ==============
    
    "fake_simple": {
        "name": "Fake (простой)",
        "description": "Базовый fake для Discord Voice",
        "author": "Community",
        "label": LABEL_STABLE,
        "args": "--dpi-desync=fake"
    },
    
    "fake_stun_0x00": {
        "name": "Fake STUN 0x00",
        "description": "Fake STUN с нулевым пакетом",
        "author": "Dronator",
        "label": LABEL_STABLE,
        "args": "--dpi-desync=fake --dpi-desync-fake-stun=0x00"
    },
    
    "fake_x4_stun": {
        "name": "Fake x4 STUN",
        "description": "4 повтора fake для STUN",
        "author": "Dronator",
        "label": LABEL_STABLE,
        "args": "--dpi-desync=fake --dpi-desync-fake-stun=0x00 --dpi-desync-repeats=4"
    },

    # ============== СЛОЖНЫЕ СТРАТЕГИИ (полные команды с --filter-l3 и --new) ==============
    
    "ipv4_ipv6_dup_autottl": {
        "name": "IPv4+IPv6 DUP AutoTTL",
        "description": "Раздельная обработка IPv4 и IPv6 с DUP",
        "author": "Community",
        "label": LABEL_RECOMMENDED,
        "args": "--filter-l3=ipv4 --filter-l7=discord,stun --dpi-desync=fake --dpi-desync-autottl --dup=2 --dup-autottl --dup-cutoff=n3 --new --filter-l3=ipv6 --filter-l7=discord,stun --dpi-desync=fake --dpi-desync-autottl6 --dup=2 --dup-autottl6 --dup-cutoff=n3"
    },
    "fake_l7": {
        "name": "Fake L7",
        "description": "Базовая стратегия с DPI Desync 'fake' и фильтрацией L7 для Discord и STUN.",
        "author": "Community",
        "label": LABEL_STABLE,
        "args": f"""--dpi-desync=fake"""
    },
    "dronatar_4_2": {
        "name": "Dronatar 4.2 / 4.3",
        "description": "fake discord=0x00, fake stun=0x00, repeats=6",
        "author": "Dronatar",
        "label": LABEL_RECOMMENDED,
        "args": f"""--dpi-desync=fake --dpi-desync-fake-discord=0x00 --dpi-desync-fake-stun=0x00 --dpi-desync-repeats=6"""
    },
    "fake_tamper_repeats_6": {
        "name": "Fake, Tamper, Repeats 6",
        "description": "Стратегия с подменой и изменением пакетов, 6 повторений.",
        "author": "Community",
        "label": None,
        "args": f"""--dpi-desync=fake,tamper --dpi-desync-repeats=6 --dpi-desync-fake-discord=0x00"""
    },
    "fake_any_proto_repeats_6_cutoff_n4": {
        "name": "Fake, Any Proto, Repeats 6, Cutoff n4",
        "description": "Стратегия с Fake Desync для любого протокола, 6 повторениями и обрезкой n4.",
        "author": "Community",
        "label": None,
        "args": f"""--dpi-desync=fake --dpi-desync-repeats=6 --dpi-desync-any-protocol --dpi-desync-cutoff=n4"""
    },
    "fake_tamper_any_proto_repeats_11_cutoff_d5": {
        "name": "Fake, Tamper, Repeats 11, Cutoff d5",
        "description": "Комбинированная стратегия с 11 повторениями и обрезкой d5 для любого протокола.",
        "author": "Community",
        "label": None,
        "args": f"""--dpi-desync=fake,tamper --dpi-desync-any-protocol --dpi-desync-cutoff=d5 --dpi-desync-repeats=11"""
    },
    "fake_any_proto_quic1_cutoff_d2": {
        "name": "Fake, Any Proto, QUIC 1, Cutoff d2",
        "description": "Использование поддельного QUIC-пакета (quic_1.bin) с обрезкой d2.",
        "author": "Community",
        "label": None,
        "args": f"""--dpi-desync=fake --dpi-desync-any-protocol --dpi-desync-cutoff=d2 --dpi-desync-fake-quic=quic_1.bin"""
    },
    "fake_repeats_6": {
        "name": "Fake Repeats 6",
        "description": "Простая стратегия с 6 повторениями фейкового пакета.",
        "author": "Community",
        "label": None,
        "args": f"""--dpi-desync=fake --dpi-desync-repeats=6"""
    },
    "ipset_fake_any_proto_cutoff_d3_repeats_6": {
        "name": "general (alt v2) 1.6.1",
        "description": "Стратегия, использующая IPSet, с 6 повторениями и обрезкой d3.",
        "author": "Community",
        "label": LABEL_RECOMMENDED,
        "args": f"""--dpi-desync=fake --dpi-desync-any-protocol --dpi-desync-cutoff=d3 --dpi-desync-repeats=6"""
    },
    "ipset_fake_any_proto_cutoff_d3_repeats_8": {
        "name": "IPSet Fake, Any Proto, Cutoff d3, Repeats 8",
        "description": "Стратегия, использующая IPSet, с 8 повторениями и обрезкой d3.",
        "author": "Community",
        "label": LABEL_RECOMMENDED,
        "args": f"""--dpi-desync=fake --dpi-desync-any-protocol --dpi-desync-cutoff=d3 --dpi-desync-repeats=8"""
    },
    "ipset_fake_any_proto_cutoff_d4_repeats_8": {
        "name": "IPSet Fake, Any Proto, Cutoff d4, Repeats 8",
        "description": "Стратегия, использующая IPSet, с 8 повторениями и обрезкой d4.",
        "author": "Community",
        "label": LABEL_RECOMMENDED,
        "args": f"""--dpi-desync=fake --dpi-desync-any-protocol --dpi-desync-cutoff=d4 --dpi-desync-repeats=8"""
    },
    "fake_any_proto_cutoff_n3": {
        "name": "Fake, Any Proto, Cutoff n3",
        "description": "Минималистичная стратегия с обрезкой n3 для любого протокола.",
        "author": "Community",
        "label": None,
        "args": f"""--dpi-desync=fake --dpi-desync-any-protocol --dpi-desync-cutoff=n3"""
    },
    "fake_split2_quic_test_cutoff_d2": {
        "name": "Fake, Split2, QUIC Test, Cutoff d2",
        "description": "Разделение пакета в сочетании с поддельным тестовым QUIC-пакетом.",
        "author": "Community",
        "label": None,
        "args": f"""--dpi-desync=fake,split2 --dpi-desync-any-protocol --dpi-desync-cutoff=d2 --dpi-desync-fake-quic=quic_test_00.bin"""
    },
    "fake_any_proto_google_quic_cutoff_n2": {
        "name": "Fake, Any Proto, Google QUIC, Cutoff n2",
        "description": "Поддельный QUIC-пакет от Google с обрезкой n2.",
        "author": "Community",
        "label": LABEL_RECOMMENDED,
        "args": f"""--dpi-desync=fake --dpi-desync-any-protocol --dpi-desync-cutoff=n2 --dpi-desync-fake-quic=quic_initial_www_google_com.bin"""
    },
    "fake_any_proto_google_quic_cutoff_d3_repeats_6": {
        "name": "Fake, Any Proto, Google QUIC, Cutoff d3, Repeats 6",
        "description": "Поддельный QUIC от Google с 6 повторениями и обрезкой d3.",
        "author": "Community",
        "label": None,
        "args": f"""--dpi-desync=fake --dpi-desync-any-protocol --dpi-desync-cutoff=d3 --dpi-desync-repeats=6 --dpi-desync-fake-quic=quic_initial_www_google_com.bin"""
    },
    "fake_tamper_any_proto_google_quic_cutoff_d3_repeats_6": {
        "name": "Fake, Tamper, Google QUIC, Cutoff d3, Repeats 6",
        "description": "Комбинация Fake и Tamper с QUIC от Google, 6 повторениями и обрезкой d3.",
        "author": "Community",
        "label": None,
        "args": f"""--dpi-desync=fake,tamper --dpi-desync-any-protocol --dpi-desync-cutoff=d3 --dpi-desync-repeats=6 --dpi-desync-fake-quic=quic_initial_www_google_com.bin"""
    },
    "fake_tamper_any_proto_google_quic_cutoff_n5_repeats_10": {
        "name": "Fake, Tamper, Google QUIC, Cutoff n5, Repeats 10",
        "description": "Агрессивная стратегия с 10 повторениями и обрезкой n5.",
        "author": "Community",
        "label": None,
        "args": f"""--dpi-desync=fake,tamper --dpi-desync-any-protocol --dpi-desync-cutoff=n5 --dpi-desync-repeats=10 --dpi-desync-fake-quic=quic_initial_www_google_com.bin"""
    },
    "fake_tamper_any_proto_google_quic_cutoff_n4": {
        "name": "Fake, Tamper, Google QUIC, Cutoff n4",
        "description": "Комбинация Fake и Tamper с QUIC от Google и обрезкой n4.",
        "author": "Community",
        "label": None,
        "args": f"""--dpi-desync=fake,tamper --dpi-desync-any-protocol --dpi-desync-cutoff=n4 --dpi-desync-fake-quic=quic_initial_www_google_com.bin"""
    },
    "discord_voice_udp_none": {
        "name": "Не применять для Discord Voice",
        "description": "Отключить обработку голосовых чатов Discord.",
        "author": "System",
        "label": None,
        "args": ""
    }
}
from ..constants import LABEL_RECOMMENDED, LABEL_STABLE, LABEL_GAME

UDP_DISCORD_BASE_ARG = "--filter-udp=443 --hostlist=discord.txt"

DISCORD_UPD_STRATEGIES = {
    "fake_6_google": {
        "name": "general (alt v2) 1.6.1",
        "description": "Стандартная стратегия для Discord Voice",
        "author": "Flowseal",
        "label": LABEL_RECOMMENDED,
        "args": f"""{UDP_DISCORD_BASE_ARG} --dpi-desync=fake --dpi-desync-repeats=6 --dpi-desync-fake-quic=quic_initial_www_google_com.bin"""
    },
    "fake_6_1": {
        "name": "fake 6 quic 1",
        "description": "Стандартная стратегия для Discord Voice с другим Fake QUIC",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""{UDP_DISCORD_BASE_ARG} --dpi-desync=fake --dpi-desync-repeats=6 --dpi-desync-fake-quic=quic_1.bin"""
    },
    "fake_6_vk_com": {
        "name": "fake 6 quic vk.com",
        "description": "Стандартная стратегия для Discord Voice с другим QUIC от VK",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""{UDP_DISCORD_BASE_ARG} --dpi-desync=fake --dpi-desync-repeats=6 --dpi-desync-fake-quic=quic_initial_vk_com.bin"""
    },
    "fake_8_google": {
        "name": "fake 8 google",
        "description": "Стандартная стратегия для Discord Voice",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""{UDP_DISCORD_BASE_ARG} --dpi-desync=fake --dpi-desync-repeats=8 --dpi-desync-fake-quic=quic_initial_www_google_com.bin"""
    },
    "fake_10_pattern": {
        "name": "Ufanet 31.03.2025",
        "description": "Стандартная стратегия для Discord Voice с доп. улучшениями",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""{UDP_DISCORD_BASE_ARG} --dpi-desync=fake --dpi-desync-udplen-increment=10 --dpi-desync-repeats=6 --dpi-desync-udplen-pattern=0xDEADBEEF --dpi-desync-fake-quic=quic_initial_www_google_com.bin"""
    },
    "fake_udplen": {
        "name": "YTDis Bystro 2.9.2 v1 / v2",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""{UDP_DISCORD_BASE_ARG} --dpi-desync=fake,udplen --dpi-desync-udplen-increment=5 --dpi-desync-udplen-pattern=0xDEADBEEF --dpi-desync-fake-quic=quic_2.bin --dpi-desync-repeats=7 --dpi-desync-cutoff=n2"""
    },
    "fake_updlen_7_quic_cutoff": {
        "name": "fake udplen 7 quic cutoff",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""{UDP_DISCORD_BASE_ARG} --dpi-desync=fake --dpi-desync-udplen-increment=10 --dpi-desync-repeats=7 --dpi-desync-udplen-pattern=0xDEADBEEF --dpi-desync-fake-quic=quic_test_00.bin --dpi-desync-cutoff=n2"""
    },
    "fake_updlen_7_quic_google": {
        "name": "fake udplen 7 quic google",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""{UDP_DISCORD_BASE_ARG} --dpi-desync=fake --dpi-desync-udplen-increment=10 --dpi-desync-repeats=7 --dpi-desync-udplen-pattern=0xDEADBEEF --dpi-desync-fake-quic=quic_initial_www_google_com.bin"""
    },
    "fake_updlen_10_pattern": {
        "name": "fake udplen 10 pattern",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""{UDP_DISCORD_BASE_ARG} --dpi-desync=fake --dpi-desync-udplen-increment=10 --dpi-desync-udplen-pattern=0xDEADBEEF --dpi-desync-fake-quic=quic_2.bin --dpi-desync-repeats=8 --dpi-desync-cutoff=n2"""
    },
    "fake_split2_repeats_6": {
        "name": "fake split2 repeats 6",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""{UDP_DISCORD_BASE_ARG} --dpi-desync=fake,split2 --dpi-desync-udplen-increment=10 --dpi-desync-repeats=6 --dpi-desync-udplen-pattern=0xDEADBEEF --dpi-desync-fake-quic=quic_initial_www_google_com.bin"""
    },
    "fake_split2_repeats_11": {
        "name": "fake split2 repeats 11",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""{UDP_DISCORD_BASE_ARG} --dpi-desync=fake,split2 --dpi-desync-repeats=11 --dpi-desync-udplen-increment=15 --dpi-desync-fake-quic=quic_initial_www_google_com.bin"""
    },
    "udp_discord_tcp_none": {
        "name": "Не применять для Discord",
        "description": "Отключить обработку Discord",
        "author": "System",
        "label": None,
        "args": ""
    }
}
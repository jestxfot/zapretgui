"""
Базовые HTTP (порт 80) техники обхода DPI.
Только DPI-аргументы! Фильтры берутся из CATEGORIES_REGISTRY.base_filter
"""

from ..constants import LABEL_RECOMMENDED, LABEL_GAME, LABEL_STABLE, LABEL_EXPERIMENTAL

"""
--dpi-desync=fakedsplit --dpi-desync-ttl=6 --dpi-desync-split-pos=method+2
--dpi-desync=fake,multisplit --dpi-desync-ttl=0 --dpi-desync-fooling=md5sig,badsum --new
--dpi-desync=fake,multisplit --dpi-desync-split-pos=method+2 --dpi-desync-fooling=md5sig --new
--dpi-desync=fake,multisplit --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=sld+1 --dpi-desync-fooling=badseq --new
--dpi-desync=fake,multisplit --dpi-desync-split-seqovl=2 --dpi-desync-split-pos=sld+1 --dpi-desync-fake-http=http_fake_MS.bin --dpi-desync-fooling=md5sig --dup=2 --dup-fooling=md5sig --dup-cutoff=n3 --new
--dpi-desync=fake,fakedsplit --dpi-desync-autottl=2 --dpi-desync-fooling=md5sig --new
--dpi-desync=fake,split2 --dpi-desync-autottl=3 --dpi-desync-fooling=md5sig --new
--dpi-desync=fake,disorder2 --dpi-desync-autottl=2 --dpi-desync-fooling=badseq --new
"""

# Стратегии для остальных сайтов
HTTP80_STRATEGIES_BASE = {
    # ============== УНИВЕРСАЛЬНАЯ NONE СТРАТЕГИЯ ==============
    "none": {
        "name": "⛔ Отключено",
        "description": "Обход DPI отключен для этой категории",
        "author": "System",
        "label": None,
        "args": ""
    },
    "fake_multisplit_2_fake_http": {
        "name": "TankiX Revive",
        "description": "fake multisplit seqovl md5sig",
        "author": "hz",
        "label": LABEL_GAME,
        "args": f"""--dpi-desync=fake,multisplit --dpi-desync-split-seqovl=2 --dpi-desync-split-pos=sld+1 --dpi-desync-fake-http=0x0F0F0F0F --dpi-desync-fooling=md5sig --dup=2 --dup-fooling=md5sig --dup-cutoff=n3"""
    },
    "fake_multisplit_seqovl_pos_fake_http": {
        "name": "TankiX Revive v2",
        "description": "fake multisplit seqovl pos fake http",
        "author": "hz",
        "label": LABEL_GAME,
        "args": f"""--dpi-desync=fake,multisplit --dpi-desync-split-seqovl=2 --dpi-desync-split-pos=host+1 --dpi-desync-fake-http=0x0E0E0F0E --dpi-desync-fooling=md5sig"""
    },
    "fake_multisplit_seqovl_pos_fake_http_2": {
        "name": "TankiX Revive v3",
        "description": "fake multisplit seqovl pos fake http",
        "author": "hz",
        "label": LABEL_GAME,
        "args": f"""--dpi-desync=fake,multisplit --dpi-desync-split-seqovl=2 --dpi-desync-split-pos=host+1 --dpi-desync-fake-http=0x0F0F0F0F --dpi-desync-fooling=md5sig"""
    },

    "fake_multisplit_md5sig_autottl": {
        "name": "fake multisplit md5sig",
        "description": "",
        "author": "hz",
        "label": LABEL_GAME,
        "args": f"""--dpi-desync=fake,multisplit --dpi-desync-split-pos=sld+1 --dpi-desync-fooling=md5sig --dpi-desync-autottl"""
    },
    "dronator_4_3": {
        "name": "Dronator 4.3",
        "description": "fake split2 md5sig",
        "author": "hz",
        "label": None,
        "args": f"""--dpi-desync=fake,split2 --dpi-desync-fooling=md5sig"""
    },
    "multisplit_17": {
        "name": "YTDisBystro 3.4 v1 (2)",
        "description": "Мульти нарезка с md5sig и фейком TLS",
        "author": "hz",
        "label": None,
        "args": f"""--dpi-desync=fake,multisplit --dpi-desync-split-pos=2,midsld --dpi-desync-fake-tls=tls_clienthello_17.bin --dpi-desync-fake-tls-mod=rnd,dupsid --dpi-desync-fooling=md5sig --dpi-desync-autottl --dup=2 --dup-fooling=md5sig --dup-autottl --dup-cutoff=n3"""
    },

    "general_altv2_161_original": {
        "name": "general (alt v2) 1.6.1",
        "description": "Оригинальный alt2",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""--dpi-desync=fake,split2 --dpi-desync-autottl=2 --dpi-desync-fooling=md5sig --new"""
    },
    "general_alt8_185": {
        "name": "general (alt8) 1.8.5",
        "description": "Потом опишу подробнее",
        "author": "V3nilla",
        "label": None,
        "args": f"""--dpi-desync=fake,split2 --dpi-desync-autottl=2 --dpi-desync-fooling=badseq --dpi-desync-badseq-increment=2"""
    }
}
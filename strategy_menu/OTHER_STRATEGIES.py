from .constants import LABEL_RECOMMENDED, LABEL_GAME, LABEL_CAUTION, LABEL_EXPERIMENTAL, LABEL_STABLE

OTHER_BASE_ARG = "--filter-tcp=80,443 --hostlist=other.txt --hostlist=other2.txt --hostlist=russia-blacklist.txt"

"""
--filter-tcp=80 --dpi-desync=fake,multisplit --dpi-desync-ttl=0 --dpi-desync-fooling=md5sig,badsum --new
--filter-tcp=80 --dpi-desync=fake,multisplit --dpi-desync-split-pos=method+2 --dpi-desync-fooling=md5sig --new
--filter-tcp=80 --dpi-desync=fake,multisplit --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=sld+1 --dpi-desync-fooling=badseq --new
--filter-tcp=80 --dpi-desync=fake,multisplit --dpi-desync-split-seqovl=2 --dpi-desync-split-pos=host+1 --dpi-desync-fake-http=0x0E0E0F0E --dpi-desync-fooling=md5sig --new
--filter-tcp=80 --dpi-desync=fake,multisplit --dpi-desync-split-seqovl=2 --dpi-desync-split-pos=host+1 --dpi-desync-fake-http=0x0F0F0F0F --dpi-desync-fooling=md5sig --new
--filter-tcp=80 --dpi-desync=fake,multisplit --dpi-desync-split-seqovl=2 --dpi-desync-split-pos=sld+1 --dpi-desync-fake-http=0x0F0F0F0F --dpi-desync-fooling=md5sig --dup=2 --dup-fooling=md5sig --dup-cutoff=n3 --new
--filter-tcp=80 --dpi-desync=fake,multisplit --dpi-desync-split-seqovl=2 --dpi-desync-split-pos=sld+1 --dpi-desync-fake-http=http_fake_MS.bin --dpi-desync-fooling=md5sig --dup=2 --dup-fooling=md5sig --dup-cutoff=n3 --new
--filter-tcp=80 --dpi-desync=fake,multisplit --dpi-desync-split-pos=sld+1 --dpi-desync-fooling=md5sig --dpi-desync-autottl --new # LABEL_GAME
--filter-tcp=80 --dpi-desync=fake,fakedsplit --dpi-desync-autottl=2 --dpi-desync-fooling=md5sig --new
--filter-tcp=80 --dpi-desync=fake,split2 --dpi-desync-autottl=2 --dpi-desync-fooling=md5sig --new
--filter-tcp=80 --dpi-desync=fake,split2 --dpi-desync-autottl=3 --dpi-desync-fooling=md5sig --new
--filter-tcp=80 --dpi-desync=fake,disorder2 --dpi-desync-autottl=2 --dpi-desync-fooling=badseq --new
"""

# Стратегии для остальных сайтов
OTHER_STRATEGIES = {
    "other_seqovl": {
        "name": "multisplit seqovl 211 & pattern 5",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""{OTHER_BASE_ARG} --dpi-desync=multisplit --dpi-desync-split-seqovl=211 --dpi-desync-split-seqovl-pattern=tls_clienthello_5.bin --new"""
    },
    "multisplit_286_pattern": {
        "name": "multisplit seqovl 286 с парттерном 11",
        "description": "Дисордер стратегия с фуллингом badseq нарезкой и повтором 11",
        "author": "hz",
        "label": None,
        "args": f"""{OTHER_BASE_ARG} --dpi-desync=multisplit --dpi-desync-split-seqovl=286 --dpi-desync-split-seqovl-pattern=tls_clienthello_11.bin --dup=2 --dup-cutoff=n3 --new"""
    },
    "multisplit_308_pattern": {
        "name": "multisplit seqovl 308 с парттерном 9",
        "description": "Дисордер стратегия с фуллингом badseq нарезкой и повтором 9",
        "author": "hz",
        "label": None,
        "args": f"""{OTHER_BASE_ARG} --dpi-desync=multisplit --dpi-desync-split-seqovl=308 --dpi-desync-split-seqovl-pattern=tls_clienthello_9.bin --dup=2 --dup-cutoff=n3 --new"""
    },
    "fake_autottl_repeats_6_badseq": {
        "name": "alt mgts (v1) 1.6.1",
        "description": "fake autottl repeats 6 badseq",
        "author": "hz",
        "label": None,
        "args": f"""{OTHER_BASE_ARG} --dpi-desync=fake --dpi-desync-autottl=2 --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --new"""
    },
    "altmgts2_161_2": {
        "name": "alt mgts (v2) 1.6.1",
        "description": "fake autottl repeats 6 md5sig",
        "author": "hz",
        "label": None,
        "args": f"""{OTHER_BASE_ARG} --dpi-desync=fake --dpi-desync-repeats=6 --dpi-desync-fooling=md5sig --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --new"""
    },
    "altmgts2_161_3": {
        "name": "alt mgts (v3) 1.6.1",
        "description": "fake autottl repeats 6 md5sig",
        "author": "hz",
        "label": None,
        "args": f"""{OTHER_BASE_ARG} --dpi-desync=fake --dpi-desync-autottl=2 --dpi-desync-repeats=6 --dpi-desync-fooling=md5sig --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --new"""
    },
    "original_bolvan_v2_badsum": {
        "name": "Если стратегия не работает смени её!",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""{OTHER_BASE_ARG} --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-fake-tls-mod=rnd,dupsid,sni=www.google.com --new"""
    },
    "other_multidisorder": {
        "name": "multidisorder 6 md5sig",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": LABEL_STABLE,
        "args": f"""{OTHER_BASE_ARG} --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=6 --dpi-desync-fooling=md5sig --new"""
    },
    "other_multidisorder_2": {
        "name": "multidisorder 6 badseq & md5sig",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": LABEL_STABLE,
        "args": f"""{OTHER_BASE_ARG} --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=6 --dpi-desync-fooling=badseq,md5sig --new"""
    },
    "other2": {
        "name": "multidisorder 6 badseq",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": None,
        "args": f"""{OTHER_BASE_ARG} --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --new"""
    },
    "fake_fakedsplit_autottl_2": {
        "name": "fake fakedsplit badseq",
        "description": "Рекомендуется для 80 порта (HTTP)",
        "author": "hz",
        "label": None,
        "args": f"""{OTHER_BASE_ARG} --dpi-desync=fake,fakedsplit --dpi-desync-autottl=2 --dpi-desync-fooling=badseq"""
    },
    "multisplit_seqovl_2_midsld": {
        "name": "fake multisplit seqovl 2 midsld",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": None,
        "args": f"""{OTHER_BASE_ARG} --dpi-desync=fake,multisplit --dpi-desync-split-seqovl=2 --dpi-desync-split-pos=1,midsld --dpi-desync-fake-http=0x0F0F0F0F --dpi-desync-fooling=md5sig --new"""
    },
    "multisplit_fake_tls_badseq": {
        "name": "multisplit 14 badseq",
        "description": "Хорошая базовая комлектация для старта",
        "author": "hz",
        "label": None,
        "args": f"""{OTHER_BASE_ARG} --dpi-desync=fake,multisplit --dpi-desync-split-pos=sld+1 --dpi-desync-fake-tls=0x0F0F0E0F --dpi-desync-fake-tls=tls_clienthello_14.bin --dpi-desync-fake-tls-mod=rnd,dupsid --dpi-desync-fooling=badseq --dpi-desync-autottl --dup=2 --dup-fooling=badseq --dup-autottl --dup-cutoff=n3 --new"""
    },
    "multisplit_fake_tls_md5sig": {
        "name": "multisplit 14 md5sig",
        "description": "Хорошая базовая комлектация для старта",
        "author": "hz",
        "label": None,
        "args": f"""{OTHER_BASE_ARG} --dpi-desync=fake,multisplit --dpi-desync-split-pos=sld+1 --dpi-desync-fake-tls=0x0F0F0E0F --dpi-desync-fake-tls=tls_clienthello_14.bin --dpi-desync-fake-tls-mod=rnd,dupsid --dpi-desync-fooling=md5sig --dpi-desync-autottl --dup=2 --dup-fooling=md5sig --dup-autottl --dup-cutoff=n3 --new"""
    },
    "multisplit_17": {
        "name": "multisplit 17",
        "description": "Мульти нарезка с md5sig и фейком TLS",
        "author": "hz",
        "label": None,
        "args": f"""{OTHER_BASE_ARG} --dpi-desync=fake,multisplit --dpi-desync-split-pos=2,midsld --dpi-desync-fake-tls=tls_clienthello_17.bin --dpi-desync-fake-tls-mod=rnd,dupsid --dpi-desync-fooling=md5sig --dpi-desync-autottl --dup=2 --dup-fooling=md5sig --dup-autottl --dup-cutoff=n3 --new"""
    },
    "other4": {
        "name": "fakedsplit badseq 10",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": None,
        "args": f"""{OTHER_BASE_ARG} --dpi-desync=fakedsplit --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq --dpi-desync-repeats=10 --dpi-desync-autottl --new"""
    },
    "other5": {
        "name": "multidisorder datanoack deepseek",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": None,
        "args": f"""{OTHER_BASE_ARG} --dpi-desync=fake,multidisorder --dpi-desync-fooling=datanoack --dpi-desync-split-pos=midsld --dpi-desync-fake-tls=tls_clienthello_chat_deepseek_com.bin --new"""
    },
    "general_altv2_161": {
        "name": "general (alt v2) 1.6.1",
        "description": "Устаревший split2 с seqovl 652 и паттерном 4",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""{OTHER_BASE_ARG} --dpi-desync=split2 --dpi-desync-split-seqovl=652 --dpi-desync-split-pos=2 --dpi-desync-split-seqovl-pattern=tls_clienthello_www_google_com.bin --new"""
    },
    "other6": {
        "name": "general (alt1) 1.8.1",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": None,
        "args": f"""{OTHER_BASE_ARG} --dpi-desync=fake,split --dpi-desync-autottl=5 --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --new"""
    },
    "general_alt183": {
        "name": "general (alt) 1.8.3",
        "description": "Потом опишу подробнее",
        "author": "Flowseal",
        "label": None,
        "args": f"""{OTHER_BASE_ARG} --dpi-desync=fake,fakedsplit --dpi-desync-autottl=5 --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --new"""
    },
    "general_alt2183": {
        "name": "general (alt2) 1.8.3",
        "description": "Потом опишу подробнее",
        "author": "Flowseal",
        "label": None,
        "args": f"""{OTHER_BASE_ARG} --dpi-desync=multisplit --dpi-desync-split-seqovl=652 --dpi-desync-split-pos=2 --dpi-desync-split-seqovl-pattern=tls_clienthello_www_google_com.bin --new"""
    },
    "other_tcp_none": {
        "name": "Не применять для остальных",
        "description": "Отключить обработку остальных сайтов",
        "author": "System",
        "label": None,
        "args": ""
    }
}
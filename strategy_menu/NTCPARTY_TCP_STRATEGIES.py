from .constants import LABEL_RECOMMENDED, LABEL_GAME, LABEL_CAUTION, LABEL_EXPERIMENTAL, LABEL_STABLE, LABEL_WARP

NTCPARTY_BASE_ARG = "--filter-tcp=443 --hostlist-domains=ntc.party"

# Стратегии для остальных сайтов
NTCPARTY_TCP_STRATEGIES = {
    "other_seqovl": {
        "name": "multisplit seqovl 211 & pattern 5",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""{NTCPARTY_BASE_ARG} --dpi-desync=multisplit --dpi-desync-split-seqovl=211 --dpi-desync-split-seqovl-pattern=tls_clienthello_5.bin --new"""
    },
    "multisplit_286_pattern": {
        "name": "multisplit seqovl 286 и cutoff n3",
        "description": "Дисордер стратегия с фуллингом pattern и cutoff n3",
        "author": "hz",
        "label": None,
        "args": f"""{NTCPARTY_BASE_ARG} --dpi-desync=multisplit --dpi-desync-split-seqovl=286 --dpi-desync-split-seqovl-pattern=tls_clienthello_11.bin --dup=2 --dup-cutoff=n3 --new"""
    },
    "multisplit_226_pattern_18": {
        "name": "multisplit seqovl 226",
        "description": "Дисордер стратегия с фуллингом pattern и повтором 9",
        "author": "hz",
        "label": None,
        "args": f"""{NTCPARTY_BASE_ARG} --dpi-desync=multisplit --dpi-desync-split-seqovl=226 --dpi-desync-split-seqovl-pattern=tls_clienthello_18.bin --dup=2 --dup-cutoff=n3 --new"""
    },
    "multisplit_308_pattern": {
        "name": "multisplit seqovl 308 с парттерном 9",
        "description": "Дисордер стратегия с фуллингом badseq нарезкой и повтором 9",
        "author": "hz",
        "label": None,
        "args": f"""{NTCPARTY_BASE_ARG} --dpi-desync=multisplit --dpi-desync-split-seqovl=308 --dpi-desync-split-seqovl-pattern=tls_clienthello_9.bin --dup=2 --dup-cutoff=n3 --new"""
    },
    "fakeddisorder_datanoack_1": {
        "name": "FakedDisorder datanoack",
        "description": "Базовая стратегия FakedDisorder с datanoack",
        "author": None,
        "label": LABEL_RECOMMENDED,
        "args": f"""{NTCPARTY_BASE_ARG} --dpi-desync=fake,fakeddisorder --dpi-desync-fooling=datanoack --dpi-desync-split-pos=midsld --dpi-desync-fake-tls=0x00000000"""
    },
    "fake_autottl_repeats_6_badseq": {
        "name": "alt mgts (v1) 1.6.1",
        "description": "fake autottl repeats 6 badseq",
        "author": "hz",
        "label": None,
        "args": f"""{NTCPARTY_BASE_ARG} --dpi-desync=fake --dpi-desync-autottl=2 --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --new"""
    },
    "altmgts2_161_2": {
        "name": "alt mgts (v2) 1.6.1",
        "description": "fake autottl repeats 6 md5sig",
        "author": "hz",
        "label": None,
        "args": f"""{NTCPARTY_BASE_ARG} --dpi-desync=fake --dpi-desync-repeats=6 --dpi-desync-fooling=md5sig --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --new"""
    },
    "altmgts2_161_3": {
        "name": "alt mgts (v3) 1.6.1",
        "description": "fake autottl repeats 6 md5sig",
        "author": "hz",
        "label": None,
        "args": f"""{NTCPARTY_BASE_ARG} --dpi-desync=fake --dpi-desync-autottl=2 --dpi-desync-repeats=6 --dpi-desync-fooling=md5sig --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --new"""
    },
    "original_bolvan_v2_badsum": {
        "name": "Если стратегия не работает смени её!",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""{NTCPARTY_BASE_ARG} --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-fake-tls-mod=rnd,dupsid,sni=www.google.com --new"""
    },
    "other_multidisorder": {
        "name": "multidisorder 6 md5sig",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": LABEL_STABLE,
        "args": f"""{NTCPARTY_BASE_ARG} --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=6 --dpi-desync-fooling=md5sig --new"""
    },
    "other_multidisorder_2": {
        "name": "multidisorder 6 badseq & md5sig",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": LABEL_STABLE,
        "args": f"""{NTCPARTY_BASE_ARG} --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=6 --dpi-desync-fooling=badseq,md5sig --new"""
    },
    "other2": {
        "name": "multidisorder 6 badseq",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": None,
        "args": f"""{NTCPARTY_BASE_ARG} --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --new"""
    },
    "fake_fakedsplit_autottl_2": {
        "name": "fake fakedsplit badseq",
        "description": "Рекомендуется для 80 порта (HTTP)",
        "author": "hz",
        "label": None,
        "args": f"""{NTCPARTY_BASE_ARG} --dpi-desync=fake,fakedsplit --dpi-desync-autottl=2 --dpi-desync-fooling=badseq --new"""
    },
    "multisplit_seqovl_2_midsld": {
        "name": "fake multisplit seqovl 2 midsld",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": None,
        "args": f"""{NTCPARTY_BASE_ARG} --dpi-desync=fake,multisplit --dpi-desync-split-seqovl=2 --dpi-desync-split-pos=1,midsld --dpi-desync-fake-http=0x0F0F0F0F --dpi-desync-fooling=md5sig --new"""
    },
    "multisplit_fake_tls_badseq": {
        "name": "multisplit 14 badseq",
        "description": "Хорошая базовая комлектация для старта",
        "author": "hz",
        "label": None,
        "args": f"""{NTCPARTY_BASE_ARG} --dpi-desync=fake,multisplit --dpi-desync-split-pos=sld+1 --dpi-desync-fake-tls=0x0F0F0E0F --dpi-desync-fake-tls=tls_clienthello_14.bin --dpi-desync-fake-tls-mod=rnd,dupsid --dpi-desync-fooling=badseq --dpi-desync-autottl --dup=2 --dup-fooling=badseq --dup-autottl --dup-cutoff=n3 --new"""
    },
    "multisplit_fake_tls_md5sig": {
        "name": "multisplit 14 md5sig",
        "description": "Хорошая базовая комлектация для старта",
        "author": "hz",
        "label": None,
        "args": f"""{NTCPARTY_BASE_ARG} --dpi-desync=fake,multisplit --dpi-desync-split-pos=sld+1 --dpi-desync-fake-tls=0x0F0F0E0F --dpi-desync-fake-tls=tls_clienthello_14.bin --dpi-desync-fake-tls-mod=rnd,dupsid --dpi-desync-fooling=md5sig --dpi-desync-autottl --dup=2 --dup-fooling=md5sig --dup-autottl --dup-cutoff=n3 --new"""
    },
    "multisplit_17": {
        "name": "multisplit 17",
        "description": "Мульти нарезка с md5sig и фейком TLS",
        "author": "hz",
        "label": None,
        "args": f"""{NTCPARTY_BASE_ARG} --dpi-desync=fake,multisplit --dpi-desync-split-pos=2,midsld --dpi-desync-fake-tls=tls_clienthello_17.bin --dpi-desync-fake-tls-mod=rnd,dupsid --dpi-desync-fooling=md5sig --dpi-desync-autottl --dup=2 --dup-fooling=md5sig --dup-autottl --dup-cutoff=n3 --new"""
    },
    "other4": {
        "name": "fakedsplit badseq 10",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": None,
        "args": f"""{NTCPARTY_BASE_ARG} --dpi-desync=fakedsplit --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq --dpi-desync-repeats=10 --dpi-desync-autottl --new"""
    },
    "other5": {
        "name": "multidisorder datanoack deepseek",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": None,
        "args": f"""{NTCPARTY_BASE_ARG} --dpi-desync=fake,multidisorder --dpi-desync-fooling=datanoack --dpi-desync-split-pos=midsld --dpi-desync-fake-tls=tls_clienthello_chat_deepseek_com.bin --new"""
    },
    "general_altv2_161": {
        "name": "general (alt v2) 1.6.1",
        "description": "Устаревший split2 с seqovl 652 и паттерном 4",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""{NTCPARTY_BASE_ARG} --dpi-desync=split2 --dpi-desync-split-seqovl=652 --dpi-desync-split-pos=2 --dpi-desync-split-seqovl-pattern=tls_clienthello_www_google_com.bin --new"""
    },
    "general_altv2_161": {
        "name": "general (alt v2) 1.6.1",
        "description": "split2 с seqovl 652 и паттерном 4 для варпа (МОЖЕТ СЛОМАТЬ САЙТЫ!)",
        "author": "hz",
        "label": LABEL_WARP,
        "args": f"""--filter-tcp=80,443 --dpi-desync=split2 --dpi-desync-split-seqovl=652 --dpi-desync-split-pos=2 --dpi-desync-split-seqovl-pattern=tls_clienthello_www_google_com.bin --new"""
    },
    "other6": {
        "name": "general (alt1) 1.8.1",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": None,
        "args": f"""{NTCPARTY_BASE_ARG} --dpi-desync=fake,split --dpi-desync-autottl=5 --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --new"""
    },
    "general_alt183": {
        "name": "general (alt) 1.8.3",
        "description": "Потом опишу подробнее",
        "author": "Flowseal",
        "label": None,
        "args": f"""{NTCPARTY_BASE_ARG} --dpi-desync=fake,fakedsplit --dpi-desync-autottl=5 --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --new"""
    },
    "general_alt2183": {
        "name": "general (alt2) 1.8.3",
        "description": "Потом опишу подробнее",
        "author": "Flowseal",
        "label": None,
        "args": f"""{NTCPARTY_BASE_ARG} --dpi-desync=multisplit --dpi-desync-split-seqovl=652 --dpi-desync-split-pos=2 --dpi-desync-split-seqovl-pattern=tls_clienthello_www_google_com.bin --new"""
    },
    "ntcparty_tcp_none": {
        "name": "Не применять для остальных",
        "description": "Отключить обработку остальных сайтов",
        "author": "System",
        "label": None,
        "args": ""
    }
}
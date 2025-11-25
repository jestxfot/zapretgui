from ..constants import LABEL_CAUTION, LABEL_GAME, LABEL_RECOMMENDED, LABEL_STABLE 

IPSET_BASE_ARG = "--filter-tcp=80,443,444-65535 --ipset=russia-youtube-rtmps.txt --ipset=ipset-all.txt --ipset=ipset-base.txt --ipset=ipset-all2.txt --ipset=ipset-discord.txt --ipset-exclude=ipset-dns.txt"

"""
--filter-tcp=443 --ipset=russia-youtube-rtmps.txt --dpi-desync=syndata --dpi-desync-fake-syndata=tls_clienthello_4.bin --dpi-desync-autottl --new
--filter-tcp=443 --ipset=russia-youtube-rtmps.txt --dpi-desync=syndata --dpi-desync-fake-syndata=tls_clienthello_4.bin --dpi-desync-fooling=badseq --new
--filter-tcp=443 --ipset=russia-youtube-rtmps.txt --dpi-desync=syndata --dpi-desync-fake-syndata=tls_clienthello_7.bin --dup=2 --dup-cutoff=n3 --new
--filter-tcp=443 --ipset=russia-youtube-rtmps.txt --dpi-desync=syndata --dpi-desync-fake-syndata=syn_packet.bin --dup=2 --dup-cutoff=n3 --new
"""

WARMFRAME_CHAT = "--filter-tcp=6695-6705 --dpi-desync=fake,split2 --dpi-desync-repeats=8 --dpi-desync-fooling=md5sig --dpi-desync-autottl=2 --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --new"

IPSET_TCP_STRATEGIES = {
    "general_alt4_182": {
        "name": "general (alt v4) 1.8.2",
        "description": "Для Rockstar Launcher & Epic Games",
        "author": "https://github.com/Flowseal/zapret-discord-youtube/issues/2361",
        "label": LABEL_GAME,
        "args": f"""{WARMFRAME_CHAT} {IPSET_BASE_ARG} --dpi-desync=fake,multisplit --dpi-desync-repeats=6 --dpi-desync-fooling=md5sig --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin"""
    },
    "general_alt185": {
        "name": "general (alt) 1.8.5",
        "description": "Для Battlefield 6",
        "author": "Flowseal",
        "label": LABEL_GAME,
        "args": f"""{WARMFRAME_CHAT} {IPSET_BASE_ARG} --dpi-desync=fake,fakedsplit --dpi-desync-repeats=6 --dpi-desync-fooling=ts --dpi-desync-fakedsplit-pattern=0x00 --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin"""
    },
    "general_bf_2": {
        "name": "general (BF) 2.0",
        "description": "Для Battlefield 6",
        "author": "Flowseal",
        "label": LABEL_GAME,
        "args": f"""{WARMFRAME_CHAT} {IPSET_BASE_ARG}  --dpi-desync=fake --dpi-desync-repeats=6 --dpi-desync-fake-tls-mod=none --dpi-desync-fooling=badseq"""
    },
    "other_seqovl": {
        "name": "YTDisBystro 3.4 v1 (all ports)",
        "description": "Стратегия била по всем портам и отлично подходила для игр",
        "author": "hz",
        "label": LABEL_GAME,
        "args": f"""{WARMFRAME_CHAT} {IPSET_BASE_ARG} --dpi-desync=multisplit --dpi-desync-split-seqovl=211 --dpi-desync-split-seqovl-pattern=tls_clienthello_5.bin"""
    },
    "multisplit_286_pattern": {
        "name": "YTDisBystro 3.4 v2 (1)",
        "description": "Дисордер стратегия с фуллингом badseq нарезкой и повтором 11",
        "author": "hz",
        "label": LABEL_GAME,
        "args": f"""{WARMFRAME_CHAT} {IPSET_BASE_ARG} --dpi-desync=multisplit --dpi-desync-split-seqovl=286 --dpi-desync-split-seqovl-pattern=tls_clienthello_11.bin --dup=2 --dup-cutoff=n3"""
    },
    "multisplit_308_pattern": {
        "name": "multisplit seqovl 308 с парттерном 9",
        "description": "Дисордер стратегия с фуллингом badseq нарезкой и повтором 9",
        "author": "hz",
        "label": LABEL_GAME,
        "args": f"""{WARMFRAME_CHAT} {IPSET_BASE_ARG} --dpi-desync=multisplit --dpi-desync-split-seqovl=308 --dpi-desync-split-seqovl-pattern=tls_clienthello_9.bin --dup=2 --dup-cutoff=n3"""
    },
    "original_bolvan_v2_badsum": {
        "name": "Если стратегия не работает смени её!",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""{WARMFRAME_CHAT} {IPSET_BASE_ARG} --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-fake-tls-mod=rnd,dupsid,sni=www.google.com"""
    },
    "other_multidisorder": {
        "name": "multidisorder 6 md5sig",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": LABEL_STABLE,
        "args": f"""{WARMFRAME_CHAT} {IPSET_BASE_ARG} --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=6 --dpi-desync-fooling=md5sig"""
    },
    "other_multidisorder_2": {
        "name": "original bol-van v2",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": LABEL_STABLE,
        "args": f"""{WARMFRAME_CHAT} {IPSET_BASE_ARG} --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=6 --dpi-desync-fooling=badseq,md5sig"""
    },
    "other2": {
        "name": "original bol-van v2 (badsum)",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": None,
        "args": f"""{WARMFRAME_CHAT} {IPSET_BASE_ARG} --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=6 --dpi-desync-fooling=badseq"""
    },
    "multisplit_fake_tls_badseq": {
        "name": "YTDisBystro 3.4 v1",
        "description": "Хорошая базовая комлектация для старта",
        "author": "hz",
        "label": None,
        "args": f"""{WARMFRAME_CHAT} {IPSET_BASE_ARG} --dpi-desync=fake,multisplit --dpi-desync-split-pos=sld+1 --dpi-desync-fake-tls=0x0F0F0E0F --dpi-desync-fake-tls=tls_clienthello_14.bin --dpi-desync-fake-tls-mod=rnd,dupsid --dpi-desync-fooling=badseq --dpi-desync-autottl --dup=2 --dup-fooling=badseq --dup-autottl --dup-cutoff=n3"""
    },
    "multisplit_fake_tls_md5sig": {
        "name": "YTDisBystro 3.4 v3",
        "description": "Хорошая базовая комлектация для старта",
        "author": "hz",
        "label": None,
        "args": f"""{WARMFRAME_CHAT} {IPSET_BASE_ARG} --dpi-desync=fake,multisplit --dpi-desync-split-pos=sld+1 --dpi-desync-fake-tls=0x0F0F0E0F --dpi-desync-fake-tls=tls_clienthello_14.bin --dpi-desync-fake-tls-mod=rnd,dupsid --dpi-desync-fooling=md5sig --dpi-desync-autottl --dup=2 --dup-fooling=md5sig --dup-autottl --dup-cutoff=n3"""
    },
    "multisplit_17": {
        "name": "YTDisBystro 3.4",
        "description": "Мульти нарезка с md5sig и фейком TLS",
        "author": "hz",
        "label": None,
        "args": f"""{WARMFRAME_CHAT} {IPSET_BASE_ARG} --dpi-desync=fake,multisplit --dpi-desync-split-pos=2,midsld --dpi-desync-fake-tls=tls_clienthello_17.bin --dpi-desync-fake-tls-mod=rnd,dupsid --dpi-desync-fooling=md5sig --dpi-desync-autottl --dup=2 --dup-fooling=md5sig --dup-autottl --dup-cutoff=n3"""
    },
    "other4": {
        "name": "fakedsplit badseq 10",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": None,
        "args": f"""{WARMFRAME_CHAT} {IPSET_BASE_ARG} --dpi-desync=fakedsplit --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq --dpi-desync-repeats=10 --dpi-desync-autottl"""
    },
    "other5": {
        "name": "multidisorder datanoack deepseek",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": None,
        "args": f"""{WARMFRAME_CHAT} {IPSET_BASE_ARG} --dpi-desync=fake,multidisorder --dpi-desync-fooling=datanoack --dpi-desync-split-pos=midsld --dpi-desync-fake-tls=tls_clienthello_chat_deepseek_com.bin"""
    },
    "other6": {
        "name": "general (alt) 1.8.1",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": LABEL_GAME,
        "args": f"""{WARMFRAME_CHAT} {IPSET_BASE_ARG} --dpi-desync=fake,split --dpi-desync-autottl=5 --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin"""
    },
    "general_alt183": {
        "name": "general (alt) 1.8.3",
        "description": "Потом опишу подробнее",
        "author": "Flowseal",
        "label": LABEL_GAME,
        "args": f"""{WARMFRAME_CHAT} {IPSET_BASE_ARG} --dpi-desync=fake,fakedsplit --dpi-desync-autottl=5 --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin"""
    },
    "general_alt2183": {
        "name": "general (alt2) 1.8.3 / 1.8.4",
        "description": "Потом опишу подробнее",
        "author": "Flowseal",
        "label": LABEL_GAME,
        "args": f"""{WARMFRAME_CHAT} {IPSET_BASE_ARG} --dpi-desync=multisplit --dpi-desync-split-seqovl=652 --dpi-desync-split-pos=2 --dpi-desync-split-seqovl-pattern=tls_clienthello_www_google_com.bin"""
    },
    "general_alt7_184": {
        "name": "general (alt v7) 1.8.4",
        "description": "multisplit seqovl 681 pos 1 seqovl pattern",
        "author": "Flowseal",
        "label": None,
        "args": f"""{WARMFRAME_CHAT} {IPSET_BASE_ARG} --dpi-desync=multisplit --dpi-desync-split-pos=2,sniext+1 --dpi-desync-split-seqovl=679 --dpi-desync-split-seqovl-pattern=tls_clienthello_www_google_com.bin"""
    },
    "general_alt8_185": {
        "name": "general (alt v8) 1.8.5",
        "description": "fake autottl repeats 6 badseq increment 2",
        "author": "V3nilla",
        "label": None,
        "args": f"""{WARMFRAME_CHAT} {IPSET_BASE_ARG} --dpi-desync=fake --dpi-desync-fake-tls-mod=none --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-badseq-increment=2"""
    },
    "general_alt8_185_2": {
        "name": "general (alt v8) 1.8.5 (2)",
        "description": "fake autottl repeats 6 badseq increment 0",
        "author": "V3nilla",
        "label": None,
        "args": f"""{WARMFRAME_CHAT} {IPSET_BASE_ARG} --dpi-desync=fake --dpi-desync-fake-tls-mod=none --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-badseq-increment=0"""
    },
    "general_alt8_185_3": {
        "name": "general (alt v8) 1.8.5 (3)",
        "description": "fake autottl repeats 6 badseq increment 100000",
        "author": "V3nilla",
        "label": None,
        "args": f"""{WARMFRAME_CHAT} {IPSET_BASE_ARG} --dpi-desync=fake --dpi-desync-fake-tls-mod=none --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-badseq-increment=100000"""
    },
    "other_seqovl_fakedsplit_ttl2": {
        "name": "fakedsplit ttl2",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""{WARMFRAME_CHAT} {IPSET_BASE_ARG} --dpi-desync=fake,fakedsplit --dpi-desync-ttl=2 --dpi-desync-split-pos=1 --dpi-desync-fake-tls=0x00000000 --dpi-desync-fake-tls=! --dpi-desync-fake-tls-mod=rnd,rndsni,dupsid"""
    },
    "fakeddisorder_datanoack_1": {
        "name": "FakedDisorder datanoack",
        "description": "Базовая стратегия FakedDisorder с datanoack",
        "author": None,
        "label": LABEL_RECOMMENDED,
        "args": f"""{WARMFRAME_CHAT} {IPSET_BASE_ARG} --dpi-desync=fake,fakeddisorder --dpi-desync-fooling=datanoack --dpi-desync-split-pos=midsld --dpi-desync-fake-tls=0x00000000"""
    },
    "fake_autottl_repeats_6_badseq": {
        "name": "alt mgts (v1) 1.6.1 / 1.8.4",
        "description": "fake autottl repeats 6 badseq",
        "author": "hz",
        "label": None,
        "args": f"""{WARMFRAME_CHAT} {IPSET_BASE_ARG} --dpi-desync=fake --dpi-desync-autottl=2 --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin"""
    },
    "general_simplefake_185": {
        "name": "general simple fake alt 1.8.5",
        "description": "fake autottl repeats 6 badseq",
        "author": "hz",
        "label": None,
        "args": f"""{WARMFRAME_CHAT} {IPSET_BASE_ARG} --dpi-desync=fake --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-badseq-increment=10000000 --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin"""
    },
    "altmgts2_161_2": {
        "name": "alt mgts (v2) 1.6.1 / 1.8.4",
        "description": "fake autottl repeats 6 md5sig",
        "author": "hz",
        "label": None,
        "args": f"""{WARMFRAME_CHAT} {IPSET_BASE_ARG} --dpi-desync=fake --dpi-desync-repeats=6 --dpi-desync-fooling=md5sig --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin"""
    },
    "general_simple_fake_165_2": {
        "name": "general simple fake 1.8.5 v2",
        "description": "fake autottl repeats 6 ts",
        "author": "hz",
        "label": None,
        "args": f"""{WARMFRAME_CHAT} {IPSET_BASE_ARG} --dpi-desync=fake --dpi-desync-repeats=6 --dpi-desync-fooling=ts --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin"""
    },
    "altmgts2_161_3": {
        "name": "alt mgts (v3) 1.6.1",
        "description": "fake autottl repeats 6 md5sig",
        "author": "hz",
        "label": None,
        "args": f"""{WARMFRAME_CHAT} {IPSET_BASE_ARG} --dpi-desync=fake --dpi-desync-autottl=2 --dpi-desync-repeats=6 --dpi-desync-fooling=md5sig --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin"""
    },
    "general_fake_tls_auto_alt_184": {
        "name": "general (fake TLS auto alt) 1.8.4",
        "description": "multisplit seqovl 681 pos 1 seqovl pattern",
        "author": "Flowseal",
        "label": None,
        "args": f"""{WARMFRAME_CHAT} {IPSET_BASE_ARG} --dpi-desync=fake,fakedsplit --dpi-desync-split-pos=1 --dpi-desync-autottl --dpi-desync-fooling=badseq --dpi-desync-badseq-increment=10000000 --dpi-desync-repeats=8 --dpi-desync-fake-tls-mod=rnd,dupsid,sni=www.google.com"""
    },
    "general_fake_tls_auto_alt_185": {
        "name": "general (fake TLS auto alt) 1.8.5",
        "description": "multisplit seqovl 681 pos 1 seqovl pattern",
        "author": "Flowseal",
        "label": None,
        "args": f"""{WARMFRAME_CHAT} {IPSET_BASE_ARG} --dpi-desync=fake,fakedsplit --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq --dpi-desync-badseq-increment=10000000 --dpi-desync-repeats=8 --dpi-desync-fake-tls-mod=rnd,dupsid,sni=www.google.com"""
    },
    "general_fake_tls_auto_alt3_184": {
        "name": "general (fake TLS auto alt3) 1.8.4",
        "description": "multisplit seqovl 681 pos 1 seqovl pattern",
        "author": "Flowseal",
        "label": None,
        "args": f"""{WARMFRAME_CHAT} {IPSET_BASE_ARG} --dpi-desync=fake,multisplit --dpi-desync-split-seqovl=681 --dpi-desync-split-pos=1 --dpi-desync-fooling=ts --dpi-desync-repeats=8 --dpi-desync-split-seqovl-pattern=tls_clienthello_www_google_com.bin --dpi-desync-fake-tls-mod=rnd,dupsid,sni=www.google.com"""
    },
    "general_fake_tls_auto_184": {
        "name": "general (fake TLS auto) 1.8.4",
        "description": "multisplit seqovl 681 pos 1 seqovl pattern",
        "author": "Flowseal",
        "label": None,
        "args": f"""{WARMFRAME_CHAT} {IPSET_BASE_ARG} --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=11 --dpi-desync-fooling=badseq --dpi-desync-fake-tls-mod=rnd,dupsid,sni=sun6-21.userapi.com"""
    },
    "syndata": {
        "name": "syndata",
        "description": "Экспериментальная стратегия с ЧИСТОЙ syndata",
        "author": "Flowseal",
        "label": LABEL_CAUTION,
        "args": f"""{WARMFRAME_CHAT} {IPSET_BASE_ARG} --dpi-desync=syndata"""
    },
    "syndata_1": {
        "name": "syndata 4",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""{WARMFRAME_CHAT} {IPSET_BASE_ARG} --dpi-desync=syndata --dpi-desync-fake-syndata=tls_clienthello_4.bin --dpi-desync-autottl"""
    },
    "syndata_4_badseq": {
        "name": "syndata 4 badseq",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": None,
        "args": f"""{WARMFRAME_CHAT} {IPSET_BASE_ARG} --dpi-desync=syndata --dpi-desync-fake-syndata=tls_clienthello_4.bin --dpi-desync-fooling=badseq"""
    },
    "syndata_7_n3": {
        "name": "syndata 7 n3",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": None,
        "args": f"""{WARMFRAME_CHAT} {IPSET_BASE_ARG} --dpi-desync=syndata --dpi-desync-fake-syndata=tls_clienthello_7.bin --dup=2 --dup-cutoff=n3"""
    },
    "syndata_syn_packet_n3": {
        "name": "syndata syn_packet.bin n3",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": None,
        "args": f"""{WARMFRAME_CHAT} {IPSET_BASE_ARG} --dpi-desync=syndata --dpi-desync-fake-syndata=syn_packet.bin --dup=2 --dup-cutoff=n3"""
    },
    "launcher_zapret_2_9_1_v1": {
        "name": "Launcher zapret 2.9.1 v1",
        "description": "fake multidisorder pos 7 fake-tls=0F0F0F0F fake-tls=3.bin badseq,autottl 2:2-12",
        "author": "Dronatar",
        "label": LABEL_RECOMMENDED,
        "args": f"""{WARMFRAME_CHAT} {IPSET_BASE_ARG} --dpi-desync=fake,multidisorder --dpi-desync-split-pos=7,sld+1 --dpi-desync-fake-tls=0x0F0F0F0F --dpi-desync-fake-tls=3.bin --dpi-desync-fake-tls-mod=rnd,dupsid,sni=fonts.google.com --dpi-desync-fooling=badseq --dpi-desync-autottl 2:2-12"""
    },
    "fake_md5sig_fake_tls": {
        "name": "Launcher zapret 2.9.1 v2",
        "description": "Базовая десинхронизация md5sig с фейком tls",
        "author": "hz",
        "label": None,
        "args": f"""{WARMFRAME_CHAT} {IPSET_BASE_ARG} --dpi-desync=fake --dpi-desync-fooling=md5sig --dpi-desync-fake-tls-mod=rnd,rndsni,padencap"""
    },
    "launcher_zapret_2_9_1_v3": {
        "name": "Launcher zapret 2.9.1 v3",
        "description": "multidisorder pos 1 midsld fake-tls=3.bin autottl",
        "author": "Dronatar",
        "label": LABEL_RECOMMENDED,
        "args": f"""{WARMFRAME_CHAT} {IPSET_BASE_ARG} --dpi-desync=multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls=3.bin --dpi-desync-autottl"""
    },
    "launcher_zapret_2_9_1_v4": {
        "name": "Launcher zapret 2.9.1 v4",
        "description": "multisplit pos 1 seqovl 681 pattern 4.bin dpi-desync-repeats=2",
        "author": "Dronatar",
        "label": LABEL_RECOMMENDED,
        "args": f"""{WARMFRAME_CHAT} {IPSET_BASE_ARG} --dpi-desync=multisplit --dpi-desync-repeats=2 --dpi-desync-split-seqovl=681 --dpi-desync-split-pos=1 --dpi-desync-split-seqovl-pattern=4.bin"""
    },
    "launcher_zapret_3_0_0_extreme": {
        "name": "Launcher zapret 3.0.0 Extreme Mode",
        "description": "multisplit pos 1 seqovl 681 pattern 4.bin dpi-desync-repeats=2",
        "author": "Dronatar",
        "label": LABEL_RECOMMENDED,
        "args": f"""{WARMFRAME_CHAT} {IPSET_BASE_ARG} --dpi-desync=multidisorder --dpi-desync-split-pos=1,midsld"""
    },
    "ipset_tcp_none": {
        "name": "Не применять для остальных",
        "description": "Отключить обработку остальных сайтов",
        "author": "System",
        "label": None,
        "args": ""
    }
}
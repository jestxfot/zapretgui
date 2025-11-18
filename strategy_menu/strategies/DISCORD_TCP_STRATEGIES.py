from ..constants import LABEL_RECOMMENDED, LABEL_CAUTION, LABEL_EXPERIMENTAL, LABEL_STABLE

DISCORD_TCP_STRATEGIES_BASE_ARG = "--filter-tcp=443,2053,2083,2087,2096,8443 --hostlist=discord.txt"

DISCORD_TCP_STRATEGIES = {
    "other_seqovl": {
        "name": "YTDisBystro 3.4 v1 (all ports)",
        "description": "Раньше эта стратегия била по всем портам и отлично подходила для игр",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""{DISCORD_TCP_STRATEGIES_BASE_ARG} --dpi-desync=multisplit --dpi-desync-split-seqovl=211 --dpi-desync-split-seqovl-pattern=tls_clienthello_5.bin"""
    },
    "dis4": {
        "name": "general (alt v2) 1.6.1",
        "description": "Устаревший split2 с seqovl 652 и паттерном 4",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""{DISCORD_TCP_STRATEGIES_BASE_ARG} --dpi-desync=split2 --dpi-desync-split-seqovl=652 --dpi-desync-split-pos=2 --dpi-desync-split-seqovl-pattern=tls_clienthello_www_google_com.bin"""
    },
    "multisplit_fake_tls_badseq": {
        "name": "YTDisBystro 3.4 v1",
        "description": "Хорошая базовая комлектация для старта",
        "author": "hz",
        "label": None,
        "args": f"""{DISCORD_TCP_STRATEGIES_BASE_ARG} --dpi-desync=fake,multisplit --dpi-desync-split-pos=sld+1 --dpi-desync-fake-tls=0x0F0F0E0F --dpi-desync-fake-tls=tls_clienthello_14.bin --dpi-desync-fake-tls-mod=rnd,dupsid --dpi-desync-fooling=badseq --dpi-desync-autottl --dup=2 --dup-fooling=badseq --dup-autottl --dup-cutoff=n3"""
    },
    "multisplit_fake_tls_md5sig": {
        "name": "YTDisBystro 3.4 v3",
        "description": "Хорошая базовая комлектация для старта",
        "author": "hz",
        "label": None,
        "args": f"""{DISCORD_TCP_STRATEGIES_BASE_ARG} --dpi-desync=fake,multisplit --dpi-desync-split-pos=sld+1 --dpi-desync-fake-tls=0x0F0F0E0F --dpi-desync-fake-tls=tls_clienthello_14.bin --dpi-desync-fake-tls-mod=rnd,dupsid --dpi-desync-fooling=md5sig --dpi-desync-autottl --dup=2 --dup-fooling=md5sig --dup-autottl --dup-cutoff=n3"""
    },
    "dronatar_4_2": {
        "name": "Dronatar 4.2",
        "description": "fake fake-tls=0x00, repeats=6 badseq increment=0",
        "author": "Dronatar",
        "label": LABEL_RECOMMENDED,
        "args": f"""{DISCORD_TCP_STRATEGIES_BASE_ARG} --dpi-desync=fake --dpi-desync-fake-tls-mod=rnd,dupsid --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-badseq-increment=0"""
    },
    "multidisorder_md5sig_pos": {
        "name": "original bol-van v2",
        "description": "Дисордер стратегия с фуллингом md5sig нарезкой и повтором 6",
        "author": "hz",
        "label": None,
        "args": f"""{DISCORD_TCP_STRATEGIES_BASE_ARG} --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=6 --dpi-desync-fooling=badseq,md5sig"""
    },
    "multidisorder_ipset_syndata": {
        "name": "Ulta v2 / 06.01.2025",
        "description": "Использует адреса дискорда, вместо доменов",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""--filter-tcp=443 --ipset=ipset-discord.txt --dpi-desync=syndata --dpi-desync-fake-syndata=tls_clienthello_3.bin --dpi-desync-autottl"""
    },
    "multidisorder_badseq_pos": {
        "name": "original bol-van v2 (badsum)",
        "description": "Дисордер стратегия с фуллингом badseq нарезкой и повтором 6",
        "author": "hz",
        "label": None,
        "args": f"""{DISCORD_TCP_STRATEGIES_BASE_ARG} --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=6 --dpi-desync-fooling=badseq"""
    },
    "multisplit_286_pattern": {
        "name": "YTDisBystro 3.4 v2 (1)",
        "description": "Дисордер стратегия с фуллингом badseq нарезкой и повтором 11",
        "author": "hz",
        "label": None,
        "args": f"""{DISCORD_TCP_STRATEGIES_BASE_ARG} --dpi-desync=multisplit --dpi-desync-split-seqovl=286 --dpi-desync-split-seqovl-pattern=tls_clienthello_11.bin --dup=2 --dup-cutoff=n3"""
    },
    "multidisorder_super_split_md5sig": {
        "name": "Discord Voice & YT (badseq)",
        "description": "Обратная стратегия с нестандартной нарезкой и md5sig",
        "author": "hz",
        "label": None,
        "args": f"""{DISCORD_TCP_STRATEGIES_BASE_ARG} --dpi-desync=fake,multidisorder --dpi-desync-split-pos=method+2,midsld,5 --dpi-desync-ttl=0 --dpi-desync-fooling=md5sig,badsum,badseq --dpi-desync-repeats=15 --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin"""
    },
    "multidisorder_super_split_badseq": {
        "name": "Discord Voice & YT (md5sig и badseq)",
        "description": "Обратная стратегия с нестандартной нарезкой и badseq",
        "author": "hz",
        "label": None,
        "args": f"""{DISCORD_TCP_STRATEGIES_BASE_ARG} --dpi-desync=fake,multidisorder --dpi-desync-split-pos=method+2,midsld,5 --dpi-desync-ttl=0 --dpi-desync-fooling=badsum,badseq --dpi-desync-repeats=15 --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin"""
    },
    "multidisorder_w3": {
        "name": "Discord Voice & YT (DTLS)",
        "description": "Обратная стратегия с фейком tls w3 и md5sig",
        "author": "hz",
        "label": None,
        "args": f"""{DISCORD_TCP_STRATEGIES_BASE_ARG} --dpi-desync=fake,multidisorder --dpi-desync-fake-tls=dtls_clienthello_w3_org.bin --dpi-desync-split-pos=1,midsld --dpi-desync-fooling=badseq,md5sig"""
    },
    "multidisorder_pos_100": {
        "name": "Split Position",
        "description": "Обратная стратегия с нестандартной нарезкой и фейком TLS",
        "author": "hz",
        "label": None,
        "args": f"""{DISCORD_TCP_STRATEGIES_BASE_ARG} --dpi-desync=fake,multidisorder --dpi-desync-fake-tls-mod=rnd,dupsid --dpi-desync-repeats=3 --dpi-desync-split-pos=100,midsld,sniext+1,endhost-2,-10 --dpi-desync-ttl=4"""
    },
    "multisplit_3": {
        "name": "YTDisBystro 2.9.2 v1 / v2",
        "description": "Отлично подходит для YouTube",
        "author": "hz",
        "label": None,
        "args": f"""{DISCORD_TCP_STRATEGIES_BASE_ARG} --dpi-desync=multisplit --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=midsld+1 --dpi-desync-split-seqovl-pattern=tls_clienthello_7.bin"""
    },
    "fake_badseq_rnd": {
        "name": "YTDisBystro 2.9.2 v1 (1)",
        "description": "Базовая стратегия десинхронизации с фейком tls rnd",
        "author": "hz",
        "label": None,
        "args": f"""{DISCORD_TCP_STRATEGIES_BASE_ARG} --dpi-desync=fake --dpi-desync-fooling=badseq --dpi-desync-fake-tls=tls_clienthello_7.bin --dpi-desync-fake-tls-mod=rnd"""
    },
    "fakedsplit_badseq_4": {
        "name": "Фейк с фуулингом badseq и фейком tls 4",
        "description": "Десинхронизация badseq с фейком tls 4",
        "author": "hz",
        "label": None,
        "args": f"""{DISCORD_TCP_STRATEGIES_BASE_ARG} --dpi-desync=fakedsplit --dpi-desync-split-pos=midsld-1,1 --dpi-desync-fooling=badseq --dpi-desync-fakedsplit-pattern=tls_clienthello_4.bin --dpi-desync-autottl"""
    },
    "fake_autottl_faketls": {
        "name": "Фейк с авто ttl и фейком tls",
        "description": "Фейк с авто ttl и фейком tls (использовать с осторожностью)",
        "author": "hz",
        "label": None,
        "args": f"""{DISCORD_TCP_STRATEGIES_BASE_ARG} --dpi-desync=fake --dpi-desync-ttl=1 --dpi-desync-autottl=4 --dpi-desync-fake-tls-mod=rnd,rndsni,padencap"""
    },
    "fake_datanoack_fake_tls": {
        "name": "Фейк с datanoack и фейком tls",
        "description": "Фейк с datanoack и фейком tls",
        "author": "hz",
        "label": None,
        "args": f"""{DISCORD_TCP_STRATEGIES_BASE_ARG} --dpi-desync=fake --dpi-desync-fooling=datanoack --dpi-desync-fake-tls-mod=rnd,rndsni,padencap"""
    },
    "dis1": {
        "name": "Фейк с datanoack и padencap",
        "description": "Улучшенная стратегия с datanoack и padencap",
        "author": "hz",
        "label": None,
        "args": f"""{DISCORD_TCP_STRATEGIES_BASE_ARG} --dpi-desync=fake,fakeddisorder --dpi-desync-fooling=datanoack --dpi-desync-split-pos=midsld --dpi-desync-fake-tls-mod=rnd,rndsni,padencap"""
    },
    "dis2": {
        "name": "multisplit split pos padencap",
        "description": "Стандартный мультисплит с нарезкой и фейком padencap",
        "author": "hz",
        "label": None,
        "args": f"""{DISCORD_TCP_STRATEGIES_BASE_ARG} --dpi-desync=fake,multisplit --dpi-desync-ttl=1 --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls-mod=rnd,rndsni,padencap"""
    },
    "dis3": {
        "name": "split badseq 10",
        "description": "Стандартный сплит с фуллингом badseq и 10 повторами",
        "author": "hz",
        "label": None,
        "args": f"""{DISCORD_TCP_STRATEGIES_BASE_ARG} --dpi-desync=split --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq --dpi-desync-repeats=10 --dpi-desync-ttl=4"""
    },
    "dis5": {
        "name": "fake split 6 google",
        "description": "Фейковый сплит с повторением 6 и фейком google",
        "author": "hz",
        "label": None,
        "args": f"""{DISCORD_TCP_STRATEGIES_BASE_ARG} --dpi-desync=fake,split --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin"""
    },
    "dis5": {
        "name": "fake split2 6 sberbank",
        "description": "Фейковый сплит2 с повторением 6 и фейком от сбербанка много деняк",
        "author": "hz",
        "label": None,
        "args": f"""{DISCORD_TCP_STRATEGIES_BASE_ARG} --dpi-desync=fake,split2 --dpi-desync-ttl=1 --dpi-desync-autottl=5 --dpi-desync-repeats=6 --dpi-desync-fake-tls=tls_clienthello_sberbank_ru.bin"""
    },
    "dis6": {
        "name": "syndata (на все домены!)",
        "description": "Стратегия работает на все домены и может ломать сайты (на свой страх и риск)",
        "author": "hz",
        "label": LABEL_CAUTION,
        "args": f"""{DISCORD_TCP_STRATEGIES_BASE_ARG} --dpi-desync=syndata --dpi-desync-fake-syndata=tls_clienthello_3.bin --dpi-desync-ttl=5"""
    },
    "dis7": {
        "name": "Ростелеком & Мегафон",
        "description": "Сплит с повторением 6 и фуллингом badseq и фейком tls от Google",
        "author": "hz",
        "label": None,
        "args": f"""{DISCORD_TCP_STRATEGIES_BASE_ARG} --dpi-desync=fake,split --dpi-desync-autottl=2 --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin"""
    },
    "dis8": {
        "name": "Ростелеком & Мегафон v2",
        "description": "Cплит2 с фейком tls 4 и ttl 4 (короче одни четвёрки)",
        "author": "hz",
        "label": None,
        "args": f"""{DISCORD_TCP_STRATEGIES_BASE_ARG} --dpi-desync=fake,split2 --dpi-desync-split-seqovl=1 --dpi-desync-split-tls=sniext --dpi-desync-fake-tls=tls_clienthello_4.bin --dpi-desync-ttl=4"""
    },
    "dis9": {
        "name": "split2 sniext google",
        "description": "Cплит2 с фейком tls от Google",
        "author": "hz",
        "label": None,
        "args": f"""{DISCORD_TCP_STRATEGIES_BASE_ARG} --dpi-desync=fake,split2 --dpi-desync-split-seqovl=1 --dpi-desync-split-tls=sniext --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --dpi-desync-ttl=2"""
    },
    "dis10": {
        "name": "disorder2 badseq tls google",
        "description": "Cплит2 badseq с фейком tls от Google",
        "author": "hz",
        "label": None,
        "args": f"""{DISCORD_TCP_STRATEGIES_BASE_ARG} --dpi-desync=syndata,disorder2 --dpi-desync-split-pos=3 --dpi-desync-repeats=11 --dpi-desync-fooling=badseq --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin"""
    },
    "dis11": {
        "name": "split badseq 10",
        "description": "Cплит2 с фуллингом badseq и 10 повторами",
        "author": "hz",
        "label": None,
        "args": f"""{DISCORD_TCP_STRATEGIES_BASE_ARG} --dpi-desync=split --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq --dpi-desync-repeats=10 --dpi-desync-autottl"""
    },
    "dis12": {
        "name": "split badseq 10 ttl",
        "description": "Cплит2 с фуллингом badseq и 10 повторами и ttl 3",
        "author": "hz",
        "label": None,
        "args": f"""{DISCORD_TCP_STRATEGIES_BASE_ARG} --dpi-desync=split --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq --dpi-desync-repeats=10 --dpi-desync-ttl=3"""
    },
    "dis13": {
        "name": "fakedsplit badsrq 10",
        "description": "Фейки и сплиты с фуллингом badseq и 10 повторами",
        "author": "hz",
        "label": None,
        "args": f"""{DISCORD_TCP_STRATEGIES_BASE_ARG} --dpi-desync=fakedsplit --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq --dpi-desync-repeats=10 --dpi-desync-autottl"""
    },
    "dis14": {
        "name": "multisplit и seqovl",
        "description": "Мульти нарезка с seqovl и нестандартной позицией",
        "author": "hz",
        "label": None,
        "args": f"""{DISCORD_TCP_STRATEGIES_BASE_ARG} --dpi-desync=multisplit --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=midsld+1"""
    },
    "other6": {
        "name": "general (alt) 1.8.1",
        "description": "Потом опишу подробнее",
        "author": "Flowseal",
        "label": None,
        "args": f"""{DISCORD_TCP_STRATEGIES_BASE_ARG} --dpi-desync=fake,split --dpi-desync-autottl=5 --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin"""
    },
    "general_alt183": {
        "name": "general (alt) 1.8.3 / 1.8.4",
        "description": "Потом опишу подробнее",
        "author": "Flowseal",
        "label": None,
        "args": f"""{DISCORD_TCP_STRATEGIES_BASE_ARG} --dpi-desync=fake,fakedsplit --dpi-desync-autottl=5 --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin"""
    },
    "general_alt185": {
        "name": "general (alt) 1.8.5",
        "description": "Потом опишу подробнее",
        "author": "Flowseal",
        "label": None,
        "args": f"""{DISCORD_TCP_STRATEGIES_BASE_ARG} --dpi-desync=fake,fakedsplit --dpi-desync-repeats=6 --dpi-desync-fooling=ts --dpi-desync-fakedsplit-pattern=0x00 --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin"""
    },
    "general_alt2183": {
        "name": "general (alt2) 1.8.3 / 1.8.4",
        "description": "Потом опишу подробнее",
        "author": "Flowseal",
        "label": None,
        "args": f"""{DISCORD_TCP_STRATEGIES_BASE_ARG} --dpi-desync=multisplit --dpi-desync-split-seqovl=652 --dpi-desync-split-pos=2 --dpi-desync-split-seqovl-pattern=tls_clienthello_www_google_com.bin"""
    },
    "general_alt3183_2": {
        "name": "general (alt v3) 1.8.2 / 1.8.4",
        "description": "fakedsplit pos 1 autottl badseq repeats 8",
        "author": "Flowseal",
        "label": None,
        "args": f"""{DISCORD_TCP_STRATEGIES_BASE_ARG} --dpi-desync=fakedsplit --dpi-desync-split-pos=1 --dpi-desync-autottl --dpi-desync-fooling=badseq --dpi-desync-repeats=8"""
    },
    "general_alt4_182": {
        "name": "general (alt v4) 1.8.2 / 1.8.4",
        "description": "fake multisplit repeats 6 md5sig tls google",
        "author": "Flowseal",
        "label": None,
        "args": f"""{DISCORD_TCP_STRATEGIES_BASE_ARG} --dpi-desync=fake,multisplit --dpi-desync-repeats=6 --dpi-desync-fooling=md5sig --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin"""
    },
    "general_alt5_182": {
        "name": "general (alt v5) 1.8.2 / 1.8.4",
        "description": "syndata",
        "author": "Flowseal",
        "label": LABEL_CAUTION,
        "args": f"""{DISCORD_TCP_STRATEGIES_BASE_ARG} --ipcache-hostname --dpi-desync=syndata"""
    },
     "general_alt6_182": {
        "name": "general (alt v6) 1.8.2",
        "description": "multisplit repeats 2 seqovl 681 pos 1 badseq hopbyhop2",
        "author": "Flowseal",
        "label": None,
        "args": f"""{DISCORD_TCP_STRATEGIES_BASE_ARG} --dpi-desync=multisplit --dpi-desync-repeats=2 --dpi-desync-split-seqovl=681 --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq,hopbyhop2 --dpi-desync-split-seqovl-pattern=tls_clienthello_www_google_com.bin"""
    },
    "general_alt6_184": {
        "name": "general (alt v6) 1.8.4",
        "description": "multisplit seqovl 681 pos 1 seqovl pattern",
        "author": "Flowseal",
        "label": None,
        "args": f"""{DISCORD_TCP_STRATEGIES_BASE_ARG} --dpi-desync=multisplit --dpi-desync-split-seqovl=681 --dpi-desync-split-pos=1 --dpi-desync-split-seqovl-pattern=tls_clienthello_www_google_com.bin"""
    },
    "general_alt7_184": {
        "name": "general (alt v7) 1.8.4",
        "description": "multisplit seqovl 681 pos 1 seqovl pattern",
        "author": "Flowseal",
        "label": None,
        "args": f"""{DISCORD_TCP_STRATEGIES_BASE_ARG} --dpi-desync=multisplit --dpi-desync-split-pos=2,sniext+1 --dpi-desync-split-seqovl=679 --dpi-desync-split-seqovl-pattern=tls_clienthello_www_google_com.bin"""
    },
    "general_alt8_185": {
        "name": "general (alt v8) 1.8.5",
        "description": "fake autottl repeats 6 badseq increment 2",
        "author": "V3nilla",
        "label": None,
        "args": f"""{DISCORD_TCP_STRATEGIES_BASE_ARG} --dpi-desync=fake --dpi-desync-fake-tls-mod=none --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-badseq-increment=2"""
    },
    "general_alt8_185_2": {
        "name": "general (alt v8) 1.8.5 (2)",
        "description": "fake autottl repeats 6 badseq increment 0",
        "author": "V3nilla",
        "label": None,
        "args": f"""{DISCORD_TCP_STRATEGIES_BASE_ARG} --dpi-desync=fake --dpi-desync-fake-tls-mod=none --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-badseq-increment=0"""
    },
    "general_alt8_185_3": {
        "name": "general (alt v8) 1.8.5 (3)",
        "description": "fake autottl repeats 6 badseq increment 100000",
        "author": "V3nilla",
        "label": None,
        "args": f"""{DISCORD_TCP_STRATEGIES_BASE_ARG} --dpi-desync=fake --dpi-desync-fake-tls-mod=none --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-badseq-increment=100000"""
    },
    "fake_autottl_repeats_6_badseq": {
        "name": "alt mgts (v1) 1.6.1 / 1.8.4",
        "description": "fake autottl repeats 6 badseq",
        "author": "hz",
        "label": None,
        "args": f"""{DISCORD_TCP_STRATEGIES_BASE_ARG} --dpi-desync=fake --dpi-desync-autottl=2 --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin"""
    },
    "general_simplefake_185": {
        "name": "general simple fake alt 1.8.5",
        "description": "fake autottl repeats 6 badseq",
        "author": "hz",
        "label": None,
        "args": f"""{DISCORD_TCP_STRATEGIES_BASE_ARG} --dpi-desync=fake --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-badseq-increment=10000000 --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin"""
    },
    "altmgts2_161_2": {
        "name": "alt mgts (v2) 1.6.1 / 1.8.4",
        "description": "fake autottl repeats 6 md5sig",
        "author": "hz",
        "label": None,
        "args": f"""{DISCORD_TCP_STRATEGIES_BASE_ARG} --dpi-desync=fake --dpi-desync-repeats=6 --dpi-desync-fooling=md5sig --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin"""
    },
    "general_simple_fake_165_2": {
        "name": "general simple fake 1.8.5 v2",
        "description": "fake autottl repeats 6 ts",
        "author": "hz",
        "label": None,
        "args": f"""{DISCORD_TCP_STRATEGIES_BASE_ARG} --dpi-desync=fake --dpi-desync-repeats=6 --dpi-desync-fooling=ts --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin"""
    },
    "altmgts2_161_3": {
        "name": "alt mgts (v3) 1.6.1",
        "description": "fake autottl repeats 6 md5sig",
        "author": "hz",
        "label": None,
        "args": f"""{DISCORD_TCP_STRATEGIES_BASE_ARG} --dpi-desync=fake --dpi-desync-autottl=2 --dpi-desync-repeats=6 --dpi-desync-fooling=md5sig --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin"""
    },
    "general_fake_tls_auto_alt_184": {
        "name": "general (fake TLS auto alt) 1.8.4",
        "description": "multisplit seqovl 681 pos 1 seqovl pattern",
        "author": "Flowseal",
        "label": None,
        "args": f"""{DISCORD_TCP_STRATEGIES_BASE_ARG} --dpi-desync=fake,fakedsplit --dpi-desync-split-pos=1 --dpi-desync-autottl --dpi-desync-fooling=badseq --dpi-desync-badseq-increment=10000000 --dpi-desync-repeats=8 --dpi-desync-fake-tls-mod=rnd,dupsid,sni=www.google.com"""
    },
    "general_fake_tls_auto_alt_185": {
        "name": "general (fake TLS auto alt) 1.8.5",
        "description": "multisplit seqovl 681 pos 1 seqovl pattern",
        "author": "Flowseal",
        "label": None,
        "args": f"""{DISCORD_TCP_STRATEGIES_BASE_ARG} --dpi-desync=fake,fakedsplit --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq --dpi-desync-badseq-increment=10000000 --dpi-desync-repeats=8 --dpi-desync-fake-tls-mod=rnd,dupsid,sni=www.google.com"""
    },
    "general_fake_tls_auto_alt3_184": {
        "name": "general (fake TLS auto alt3) 1.8.4",
        "description": "multisplit seqovl 681 pos 1 seqovl pattern",
        "author": "Flowseal",
        "label": None,
        "args": f"""{DISCORD_TCP_STRATEGIES_BASE_ARG} --dpi-desync=fake,multisplit --dpi-desync-split-seqovl=681 --dpi-desync-split-pos=1 --dpi-desync-fooling=ts --dpi-desync-repeats=8 --dpi-desync-split-seqovl-pattern=tls_clienthello_www_google_com.bin --dpi-desync-fake-tls-mod=rnd,dupsid,sni=www.google.com"""
    },
    "general_fake_tls_auto_alt2_184": {
        "name": "general (fake TLS auto alt2) 1.8.4",
        "description": "multisplit seqovl 681 pos 1 seqovl pattern",
        "author": "Flowseal",
        "label": None,
        "args": f"""{DISCORD_TCP_STRATEGIES_BASE_ARG} --dpi-desync=fake,multisplit --dpi-desync-split-seqovl=681 --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq --dpi-desync-badseq-increment=10000000 --dpi-desync-repeats=8 --dpi-desync-split-seqovl-pattern=tls_clienthello_www_google_com.bin --dpi-desync-fake-tls-mod=rnd,dupsid,sni=www.google.com"""
    },
    "general_fake_tls_auto_184": {
        "name": "general (fake TLS auto) 1.8.4",
        "description": "multisplit seqovl 681 pos 1 seqovl pattern",
        "author": "Flowseal",
        "label": None,
        "args": f"""{DISCORD_TCP_STRATEGIES_BASE_ARG} --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=11 --dpi-desync-fooling=badseq --dpi-desync-fake-tls-mod=rnd,dupsid,sni=sun6-21.userapi.com"""
    },
    "dronatar_4_3": {
        "name": "Dronatar 4.3",
        "description": "fake fake-tls=0x00, repeats=6 badseq,hopbyhop2",
        "author": "Dronatar",
        "label": LABEL_RECOMMENDED,
        "args": f"""{DISCORD_TCP_STRATEGIES_BASE_ARG} --dpi-desync=fake --dpi-desync-fake-tls-mod=none --dpi-desync-repeats=6 --dpi-desync-fooling=badseq,hopbyhop2"""
    },
    "launcher_zapret_2_9_1_v1": {
        "name": "Launcher zapret 2.9.1 v1",
        "description": "fake multidisorder pos 7 fake-tls=0F0F0F0F fake-tls=3.bin badseq,autottl 2:2-12",
        "author": "Dronatar",
        "label": LABEL_RECOMMENDED,
        "args": f"""{DISCORD_TCP_STRATEGIES_BASE_ARG} --dpi-desync=fake,multidisorder --dpi-desync-split-pos=7,sld+1 --dpi-desync-fake-tls=0x0F0F0F0F --dpi-desync-fake-tls=3.bin --dpi-desync-fake-tls-mod=rnd,dupsid,sni=fonts.google.com --dpi-desync-fooling=badseq --dpi-desync-autottl 2:2-12"""
    },
    "fake_md5sig_fake_tls": {
        "name": "Launcher zapret 2.9.1 v2",
        "description": "Базовая десинхронизация md5sig с фейком tls",
        "author": "hz",
        "label": None,
        "args": f"""{DISCORD_TCP_STRATEGIES_BASE_ARG} --dpi-desync=fake --dpi-desync-fooling=md5sig --dpi-desync-fake-tls-mod=rnd,rndsni,padencap"""
    },
    "launcher_zapret_2_9_1_v3": {
        "name": "Launcher zapret 2.9.1 v3",
        "description": "multidisorder pos 1 midsld fake-tls=3.bin autottl",
        "author": "Dronatar",
        "label": LABEL_RECOMMENDED,
        "args": f"""{DISCORD_TCP_STRATEGIES_BASE_ARG} --dpi-desync=multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls=3.bin --dpi-desync-autottl"""
    },
    "launcher_zapret_2_9_1_v4": {
        "name": "Launcher zapret 2.9.1 v4",
        "description": "multisplit pos 1 seqovl 681 pattern 4.bin dpi-desync-repeats=2",
        "author": "Dronatar",
        "label": LABEL_RECOMMENDED,
        "args": f"""{DISCORD_TCP_STRATEGIES_BASE_ARG} --dpi-desync=multisplit --dpi-desync-repeats=2 --dpi-desync-split-seqovl=681 --dpi-desync-split-pos=1 --dpi-desync-split-seqovl-pattern=4.bin"""
    },
    "launcher_zapret_3_0_0_extreme": {
        "name": "Launcher zapret 3.0.0 Extreme Mode",
        "description": "multisplit pos 1 seqovl 681 pattern 4.bin dpi-desync-repeats=2",
        "author": "Dronatar",
        "label": LABEL_RECOMMENDED,
        "args": f"""{DISCORD_TCP_STRATEGIES_BASE_ARG} --dpi-desync=multidisorder --dpi-desync-split-pos=1,midsld"""
    },
    "discord_tcp_none": {
        "name": "Не применять для Discord",
        "description": "Отключить обработку Discord",
        "author": "System",
        "label": None,
        "args": ""
    }
}
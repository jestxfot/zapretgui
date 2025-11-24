from ..constants import LABEL_RECOMMENDED, LABEL_GAME, LABEL_CAUTION, LABEL_EXPERIMENTAL, LABEL_STABLE, LABEL_WARP

SPEEDTEST_BASE_ARG = "--filter-tcp=443,8080 --hostlist=speedtest.txt"

# Стратегии для остальных сайтов
SPEEDTEST_TCP_STRATEGIES = {
    "other_seqovl": {
        "name": "YTDisBystro 3.4 v1 (all ports)",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""{SPEEDTEST_BASE_ARG} --blob=bin_tls5:@{BIN_FOLDER}\\tls_clienthello_5.bin {RUTRACKER_BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=multisplit:seqovl=211:seqovl_pattern=bin_tls5"""
    },
    "other_seqovl_2": {
        "name": "multidisorder seqovl 211 & pattern 5",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""{SPEEDTEST_BASE_ARG} --dpi-desync=multidisorder --dpi-desync-split-seqovl=211 --dpi-desync-split-seqovl-pattern=tls_clienthello_5.bin"""
    },
    "multisplit_286_pattern": {
        "name": "YTDisBystro 3.4 v2 (1)",
        "description": "Мультисплит стратегия с фуллингом pattern и cutoff n3",
        "author": "hz",
        "label": None,
        "args": f"""{SPEEDTEST_BASE_ARG} --blob=bin_tls11:@{BIN_FOLDER}\\tls_clienthello_11.bin {RUTRACKER_BASE_ARG} --payload=tls_client_hello --out-range=-n3 --lua-desync=send:repeats=2 --out-range=-d10 --lua-desync=multisplit:seqovl=286:seqovl_pattern=bin_tls11"""
    },
    "multisplit_226_pattern_18": {
        "name": "multisplit seqovl 226",
        "description": "Мультисплит стратегия с фуллингом pattern и повтором 9",
        "author": "hz",
        "label": None,
        "args": f"""{SPEEDTEST_BASE_ARG} --payload=tls_client_hello --out-range=-n3 --lua-desync=send:repeats=2 --out-range=-d10 --lua-desync=multisplit:seqovl=226:seqovl_pattern=bin_tls18"""
    },
    "multisplit_226_pattern_google_Com": {
        "name": "multisplit seqovl 226 v2",
        "description": "Мультисплит стратегия с фуллингом pattern и повтором 9",
        "author": "hz",
        "label": None,
        "args": f"""{SPEEDTEST_BASE_ARG} --payload=tls_client_hello --out-range=-d1 --lua-desync=send:repeats=2 --out-range=-d10 --lua-desync=multisplit:seqovl=226:seqovl_pattern=tls_google"""
    },
    "multisplit_308_pattern": {
        "name": "multisplit seqovl 308 с парттерном 9",
        "description": "Мультисплит стратегия с фуллингом badseq нарезкой и повтором 9",
        "author": "hz",
        "label": None,
        "args": f"""{SPEEDTEST_BASE_ARG} """
    },
    "multisplit_split_pos_1": {
        "name": "multisplit split pos 1",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""{SPEEDTEST_BASE_ARG} --lua-desync=multisplit:pos=1"""
    },
    "datanoack": {
        "name": "datanoack",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""{SPEEDTEST_BASE_ARG} --dpi-desync-fooling=datanoack"""
    },
    "multisplit_datanoack": {
        "name": "multisplit datanoack",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""{SPEEDTEST_BASE_ARG} --lua-desync=multisplit:pos=2:tcp_flags_unset=ack"""
    },
    "multisplit_datanoack_split_pos_1": {
        "name": "multisplit datanoack split pos 1",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""{SPEEDTEST_BASE_ARG} --lua-desync=multisplit:pos=1:tcp_flags_unset=ack"""
    },
    "other_seqovl_fakedsplit_ttl2": {
        "name": "fakedsplit ttl2",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""{SPEEDTEST_BASE_ARG} --lua-desync=fake:blob=fake_default_tls:ip_ttl=2:ip6_ttl=2:tls_mod=rnd,rndsni,dupsid --lua-desync=fakedsplit:pos=1:pattern=fake_default_tls:ip_ttl=2:ip6_ttl=2"""
    },
    "fakeddisorder_datanoack_1": {
        "name": "FakedDisorder datanoack",
        "description": "Базовая стратегия FakedDisorder с datanoack",
        "author": None,
        "label": LABEL_RECOMMENDED,
        "args": f"""{SPEEDTEST_BASE_ARG} """
    },
    "fake_autottl_repeats_6_badseq": {
        "name": "alt mgts (v1) 1.6.1 / 1.8.4",
        "description": "fake autottl repeats 6 badseq",
        "author": "hz",
        "label": None,
        "args": f"""{SPEEDTEST_BASE_ARG} """
    },
    "altmgts2_161_2": {
        "name": "alt mgts (v2) 1.6.1 / 1.8.4",
        "description": "fake autottl repeats 6 md5sig",
        "author": "hz",
        "label": None,
        "args": f"""{SPEEDTEST_BASE_ARG} """
    },
    "altmgts2_161_3": {
        "name": "alt mgts (v3) 1.6.1",
        "description": "fake autottl repeats 6 md5sig",
        "author": "hz",
        "label": None,
        "args": f"""{SPEEDTEST_BASE_ARG} """
    },
    "original_bolvan_v2_badsum": {
        "name": "Если стратегия не работает смени её!",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""{SPEEDTEST_BASE_ARG} """
    },
    "original_bolvan_v2_badsum_max": {
        "name": "Мессенджер Max",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""{SPEEDTEST_BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=fake:blob=fake_default_tls:tcp_ack=-66000:repeats=6:tls_mod=rnd,dupsid,sni=web.max.ru --lua-desync=multidisorder:pos=1,midsld"""
    },
    "other_multidisorder": {
        "name": "multidisorder 6 md5sig",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": LABEL_STABLE,
        "args": f"""{SPEEDTEST_BASE_ARG} """
    },
    "other_multidisorder_2": {
        "name": "original bol-van v2",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": LABEL_STABLE,
        "args": f"""{SPEEDTEST_BASE_ARG} """
    },
    "other2": {
        "name": "original bol-van v2 (badsum)",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": None,
        "args": f"""{SPEEDTEST_BASE_ARG} """
    },
    "fake_fakedsplit_autottl_2": {
        "name": "fake fakedsplit badseq",
        "description": "",
        "author": "hz",
        "label": None,
        "args": f"""{SPEEDTEST_BASE_ARG} --dpi-desync=fake,fakedsplit --dpi-desync-autottl=2 --dpi-desync-fooling=badseq"""
    },
    "multisplit_seqovl_2_midsld": {
        "name": "fake multisplit seqovl 2 midsld",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": None,
        "args": f"""{SPEEDTEST_BASE_ARG} --dpi-desync=fake,multisplit --dpi-desync-split-seqovl=2 --dpi-desync-split-pos=1,midsld --dpi-desync-fake-http=0x0F0F0F0F --dpi-desync-fooling=md5sig"""
    },
    "multisplit_fake_tls_badseq": {
        "name": "YTDisBystro 3.4 v1",
        "description": "Хорошая базовая комлектация для старта",
        "author": "hz",
        "label": None,
        "args": f"""{SPEEDTEST_BASE_ARG} --dpi-desync=fake,multisplit --dpi-desync-split-pos=sld+1 --dpi-desync-fake-tls=0x0F0F0E0F --dpi-desync-fake-tls=tls_clienthello_14.bin --dpi-desync-fake-tls-mod=rnd,dupsid --dpi-desync-fooling=badseq --dpi-desync-autottl --dup=2 --dup-fooling=badseq --dup-autottl --dup-cutoff=n3"""
    },
    "multisplit_fake_tls_md5sig": {
        "name": "YTDisBystro 3.4 v3",
        "description": "Хорошая базовая комлектация для старта",
        "author": "hz",
        "label": None,
        "args": f"""{SPEEDTEST_BASE_ARG} --dpi-desync=fake,multisplit --dpi-desync-split-pos=sld+1 --dpi-desync-fake-tls=0x0F0F0E0F --dpi-desync-fake-tls=tls_clienthello_14.bin --dpi-desync-fake-tls-mod=rnd,dupsid --dpi-desync-fooling=md5sig --dpi-desync-autottl --dup=2 --dup-fooling=md5sig --dup-autottl --dup-cutoff=n3"""
    },
    "multisplit_17": {
        "name": "YTDisBystro 3.4",
        "description": "Мульти нарезка с md5sig и фейком TLS",
        "author": "hz",
        "label": None,
        "args": f"""{SPEEDTEST_BASE_ARG} --dpi-desync=fake,multisplit --dpi-desync-split-pos=2,midsld --dpi-desync-fake-tls=tls_clienthello_17.bin --dpi-desync-fake-tls-mod=rnd,dupsid --dpi-desync-fooling=md5sig --dpi-desync-autottl --dup=2 --dup-fooling=md5sig --dup-autottl --dup-cutoff=n3"""
    },
    "other4": {
        "name": "fakedsplit badseq 10",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": None,
        "args": f"""{SPEEDTEST_BASE_ARG} --dpi-desync=fakedsplit --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq --dpi-desync-repeats=10 --dpi-desync-autottl"""
    },
    "other5": {
        "name": "multidisorder datanoack deepseek",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": None,
        "args": f"""{SPEEDTEST_BASE_ARG} --dpi-desync=fake,multidisorder --dpi-desync-fooling=datanoack --dpi-desync-split-pos=midsld --dpi-desync-fake-tls=tls_clienthello_chat_deepseek_com.bin"""
    },
    "general_altv2_161": {
        "name": "general (alt v2) 1.6.1",
        "description": "Устаревший split2 с seqovl 652 и паттерном 4",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""{SPEEDTEST_BASE_ARG} --dpi-desync=split2 --dpi-desync-split-seqovl=652 --dpi-desync-split-pos=2 --dpi-desync-split-seqovl-pattern=tls_clienthello_www_google_com.bin"""
    },
    "general_altv2_161": {
        "name": "general (alt v2) 1.6.1",
        "description": "split2 с seqovl 652 и паттерном 4 для варпа (МОЖЕТ СЛОМАТЬ САЙТЫ!)",
        "author": "hz",
        "label": LABEL_WARP,
        "args": f"""--filter-tcp=80,443,8080 --dpi-desync=split2 --dpi-desync-split-seqovl=652 --dpi-desync-split-pos=2 --dpi-desync-split-seqovl-pattern=tls_clienthello_www_google_com.bin"""
    },
    "other6": {
        "name": "general (alt1) 1.8.1",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": None,
        "args": f"""{SPEEDTEST_BASE_ARG} --dpi-desync=fake,split --dpi-desync-autottl=5 --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin"""
    },
    "general_alt183": {
        "name": "general (alt) 1.8.3",
        "description": "Потом опишу подробнее",
        "author": "Flowseal",
        "label": None,
        "args": f"""{SPEEDTEST_BASE_ARG} --dpi-desync=fake,fakedsplit --dpi-desync-autottl=5 --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin"""
    },
    "general_alt2183": {
        "name": "general (alt2) 1.8.3 / 1.8.4",
        "description": "Потом опишу подробнее",
        "author": "Flowseal",
        "label": None,
        "args": f"""{SPEEDTEST_BASE_ARG} --dpi-desync=multisplit --dpi-desync-split-seqovl=652 --dpi-desync-split-pos=2 --dpi-desync-split-seqovl-pattern=tls_clienthello_www_google_com.bin"""
    },
    "general_alt3183_2": {
        "name": "general (alt v3) 1.8.2 / 1.8.4",
        "description": "fakedsplit pos 1 autottl badseq repeats 8",
        "author": "Flowseal",
        "label": None,
        "args": f"""{SPEEDTEST_BASE_ARG} --dpi-desync=fakedsplit --dpi-desync-split-pos=1 --dpi-desync-autottl --dpi-desync-fooling=badseq --dpi-desync-repeats=8"""
    },
    "general_alt4_182": {
        "name": "general (alt v4) 1.8.2 / 1.8.4",
        "description": "fake multisplit repeats 6 md5sig tls google",
        "author": "Flowseal",
        "label": None,
        "args": f"""{SPEEDTEST_BASE_ARG} --dpi-desync=fake,multisplit --dpi-desync-repeats=6 --dpi-desync-fooling=md5sig --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin"""
    },
    "general_alt6_184": {
        "name": "general (alt v6) 1.8.4",
        "description": "multisplit seqovl 681 pos 1 seqovl pattern",
        "author": "Flowseal",
        "label": None,
        "args": f"""{SPEEDTEST_BASE_ARG} --dpi-desync=multisplit --dpi-desync-split-seqovl=681 --dpi-desync-split-pos=1 --dpi-desync-split-seqovl-pattern=tls_clienthello_www_google_com.bin"""
    },
    "general_alt7_184": {
        "name": "general (alt v7) 1.8.4",
        "description": "multisplit seqovl 681 pos 1 seqovl pattern",
        "author": "Flowseal",
        "label": None,
        "args": f"""{SPEEDTEST_BASE_ARG} --dpi-desync=multisplit --dpi-desync-split-pos=2,sniext+1 --dpi-desync-split-seqovl=679 --dpi-desync-split-seqovl-pattern=tls_clienthello_www_google_com.bin"""
    },
    "general_fake_tls_auto_alt_184": {
        "name": "general (fake TLS auto alt) 1.8.4",
        "description": "multisplit seqovl 681 pos 1 seqovl pattern",
        "author": "Flowseal",
        "label": None,
        "args": f"""{SPEEDTEST_BASE_ARG} --dpi-desync=fake,fakedsplit --dpi-desync-split-pos=1 --dpi-desync-autottl --dpi-desync-fooling=badseq --dpi-desync-badseq-increment=10000000 --dpi-desync-repeats=8 --dpi-desync-fake-tls-mod=rnd,dupsid,sni=www.google.com"""
    },
    "general_fake_tls_auto_alt2_184": {
        "name": "general (fake TLS auto alt2) 1.8.4",
        "description": "multisplit seqovl 681 pos 1 seqovl pattern",
        "author": "Flowseal",
        "label": None,
        "args": f"""{SPEEDTEST_BASE_ARG} --dpi-desync=fake,multisplit --dpi-desync-split-seqovl=681 --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq --dpi-desync-badseq-increment=10000000 --dpi-desync-repeats=8 --dpi-desync-split-seqovl-pattern=tls_clienthello_www_google_com.bin --dpi-desync-fake-tls-mod=rnd,dupsid,sni=www.google.com"""
    },
    "general_fake_tls_auto_alt3_184": {
        "name": "general (fake TLS auto alt3) 1.8.4",
        "description": "multisplit seqovl 681 pos 1 seqovl pattern",
        "author": "Flowseal",
        "label": None,
        "args": f"""{SPEEDTEST_BASE_ARG} --dpi-desync=fake,multisplit --dpi-desync-split-seqovl=681 --dpi-desync-split-pos=1 --dpi-desync-fooling=ts --dpi-desync-repeats=8 --dpi-desync-split-seqovl-pattern=tls_clienthello_www_google_com.bin --dpi-desync-fake-tls-mod=rnd,dupsid,sni=www.google.com"""
    },
    "general_fake_tls_auto_184": {
        "name": "general (fake TLS auto) 1.8.4",
        "description": "multisplit seqovl 681 pos 1 seqovl pattern",
        "author": "Flowseal",
        "label": None,
        "args": f"""{SPEEDTEST_BASE_ARG} --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=11 --dpi-desync-fooling=badseq --dpi-desync-fake-tls-mod=rnd,dupsid,sni=sun6-21.userapi.com"""
    },
    "multisplit_1_midsld": {
        "name": "multisplit seqovl 1 и midsld",
        "description": "Базовая мультисплит с midsld",
        "author": "hz",
        "label": None,
        "args": f"""{SPEEDTEST_BASE_ARG} --lua-desync=multisplit:pos=1,midsld"""
    },
    "fake_multidisorder_1_split_pos_1": {
        "name": "fake multidisorder badsum split pos 1",
        "description": "Базовая мультисплит с midsld",
        "author": "hz",
        "label": None,
        "args": f"""{SPEEDTEST_BASE_ARG} --dpi-desync=fake,multidisorder --dpi-desync-fooling=badsum --dpi-desync-split-pos=1"""
    },
    "speedtest_tcp_none": {
        "name": "Не применять для остальных",
        "description": "Отключить обработку остальных сайтов",
        "author": "System",
        "label": None,
        "args": ""
    }
}
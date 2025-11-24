from ..constants import LABEL_RECOMMENDED, LABEL_CAUTION, LABEL_EXPERIMENTAL, LABEL_STABLE

BASE_ARG = "--filter-tcp=80,443 --hostlist=google.txt"

GOOGLE_TCP_STRATEGIES = {
    "multisplit_seqovl_midsld": {
        "name": "multisplit seqovl midsld",
        "description": "Самая простая стратегия multisplit для Google",
        "author": None,
        "label": LABEL_RECOMMENDED,
        "args": f"""{BASE_ARG} --dpi-desync=multisplit --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=midsld-1"""
    },
    "original_bolvan_v2_badsum": {
        "name": "Если стратегия не работает смени её!",
        "description": "Базовая стратегия multidisorder для Google",
        "author": "OrigBolvan",
        "label": LABEL_RECOMMENDED,
        "args": f"""{BASE_ARG} """
    },
    "bolvan_md5sig": {
        "name": "BolVan md5sig 11",
        "description": "Другой метод фуллинга + большее число повторений",
        "author": "OrigBolvan",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=11 --dpi-desync-fooling=md5sig"""
    },
    "bolvan_md5sig_2": {
        "name": "BolVan v3",
        "description": "Другой метод фуллинга + большее число повторений + tls от гугла",
        "author": "Уфанет",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=11 --dpi-desync-fooling=md5sig  --dpi-desync-fake-tls-mod=rnd,dupsid,sni=www.google.com"""
    },
    "bolvan_fake_tls": {
        "name": "BolVan fake TLS 4",
        "description": "Используется фейковый Clienthello",
        "author": "OrigBolvan",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=4 --dpi-desync-fake-tls=tls_clienthello_18.bin --dpi-desync-fooling=badseq"""
    },
    "multisplit_seqovl": {
        "name": "multisplit и seqovl 1",
        "description": "Используется multisplit и seqovl 1",
        "author": "hz",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=multisplit --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=midsld+1"""
    },
    "fake_multisplit_seqovl_md5sig": {
        "name": "fake multisplit и seqovl 1 md5sig",
        "description": "Используется multisplit и seqovl 1",
        "author": "hz",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=fake,multisplit --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=midsld-1 --dpi-desync-fooling=md5sig,badseq --dpi-desync-fake-tls=tls_clienthello_4.bin --dpi-desync-ttl=2"""
    },
    "split_pos_md5sig": {
        "name": "Discord Voice & YT (badseq)",
        "description": "method+2,midsld,5 и ttl 0",
        "author": "hz",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=fake,multidisorder --dpi-desync-split-pos=method+2,midsld,5 --dpi-desync-ttl=0 --dpi-desync-fooling=md5sig,badsum,badseq --dpi-desync-repeats=15 --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin"""
    },
    "multisplit_1": {
        "name": "Мультисплит и смещение +1",
        "description": "Базовая стратегия десинхронизации multisplit",
        "author": "hz",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=multisplit --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=sld+1"""
    },
    "multisplit_2": {
        "name": "Мультисплит и смещение -1",
        "description": "Базовая стратегия десинхронизации multisplit",
        "author": "hz",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=multisplit --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=sld-1"""
    },
    "multisplit_3": {
        "name": "YTDisBystro 2.9.2 v1 / v2",
        "description": "Отлично подходит для Google",
        "author": "hz",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=multisplit --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=midsld+1 --dpi-desync-split-seqovl-pattern=tls_clienthello_7.bin"""
    },
    "fake_badseq_rnd": {
        "name": "YTDisBystro 2.9.2 v1 (1)",
        "description": "Базовая стратегия десинхронизации с фейком tls rnd",
        "author": "hz",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=fake --dpi-desync-fooling=badseq --dpi-desync-fake-tls=tls_clienthello_7.bin --dpi-desync-fake-tls-mod=rnd"""
    },
    "multidisorder_fake_tls_1": {
        "name": "YtDisBystro 3.4 (v4)",
        "description": "multidisorder 7 Fake TLS fonts и badseq",
        "author": "hz",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=fake,multidisorder --dpi-desync-split-pos=7,sld+1 --dpi-desync-fake-tls=0x0F0F0F0F --dpi-desync-fake-tls=tls_clienthello_4.bin --dpi-desync-fake-tls-mod=rnd,dupsid,sni=fonts.google.com --dpi-desync-fooling=badseq --dpi-desync-autottl"""
    },
    "multidisorder_fake_tls_2": {
        "name": "multidisorder 7 Fake TLS calendar и badseq",
        "description": "Кастомная и сложная стратегия с фейком calendar",
        "author": "hz",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=fake,multidisorder --dpi-desync-split-pos=7,sld+1 --dpi-desync-fake-tls=0x0F0F0F0F --dpi-desync-fake-tls=tls_clienthello_4.bin --dpi-desync-fake-tls-mod=rnd,dupsid,sni=calendar.google.com --dpi-desync-fooling=badseq --dpi-desync-autottl"""
    },
    "multidisorder_badseq_w3": {
        "name": "Discord Voice & YT (DTLS)",
        "description": "Обратная стратегия с фуллингом badseq и фейком w3",
        "author": "hz",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=fake,multidisorder --dpi-desync-fake-tls=dtls_clienthello_w3_org.bin --dpi-desync-split-pos=1,midsld --dpi-desync-fooling=badseq,md5sig"""
    },
    "multidisorder_rnd_split": {
        "name": "Split Position",
        "description": "Обратная стратегия с нестандартной стратегией и фейком TLS",
        "author": "hz",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=fake,multidisorder --dpi-desync-fake-tls-mod=rnd,dupsid --dpi-desync-repeats=3 --dpi-desync-split-pos=100,midsld,sniext+1,endhost-2,-10 --dpi-desync-ttl=4"""
    },
    "multisplit_17": {
        "name": "YTDisBystro 3.4",
        "description": "Мульти нарезка с md5sig и фейком TLS",
        "author": "hz",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=fake,multisplit --dpi-desync-split-pos=2,midsld --dpi-desync-fake-tls=tls_clienthello_17.bin --dpi-desync-fake-tls-mod=rnd,dupsid --dpi-desync-fooling=md5sig --dpi-desync-autottl --dup=2 --dup-fooling=md5sig --dup-autottl --dup-cutoff=n3"""
    },
    "syndata": {
        "name": "syndata",
        "description": "Экспериментальная стратегия с ЧИСТОЙ syndata",
        "author": "Flowseal",
        "label": LABEL_CAUTION,
        "args": f"""{BASE_ARG} --dpi-desync=syndata"""
    },
    "multisplit_md5sig": {
        "name": "multisplit и md5sig",
        "description": "Экспериментальная стратегия multisplit и md5sig",
        "author": "hz",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=fake,multisplit --dpi-desync-split-pos=sld+1 --dpi-desync-fake-tls=0x0F0F0E0F --dpi-desync-fake-tls=tls_clienthello_9.bin --dpi-desync-fake-tls-mod=rnd,dupsid --dpi-desync-fooling=md5sig --dpi-desync-autottl --dup=2 --dup-fooling=md5sig --dup-autottl --dup-cutoff=n3""" # раньше тут было syndata --dpi-desync-fake-syndata=tls_clienthello_7.bin
    },
    "fake_multidisorder_seqovl_fake_tls": {
        "name": "fake multidisorder seqovl fake tls",
        "description": "ОЧЕНЬ сложная стратегия с фейком TLS и seqovl",
        "author": "hz",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=fake,multidisorder --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=sld+1 --dpi-desync-fake-tls=0x0F0F0E0F --dpi-desync-fake-tls=tls_clienthello_9.bin --dpi-desync-fake-tls-mod=rnd,dupsid --dpi-desync-fooling=md5sig --dpi-desync-autottl --dup=2 --dup-fooling=md5sig --dup-autottl --dup-cutoff=n3"""
    },
    "syndata_md5sig_2": {
        "name": "multisplit и md5sig 9",
        "description": "Стандартный multisplit и md5sig и фейк TLS 9",
        "author": "hz",
        "label": LABEL_CAUTION,
        "args": f"""{BASE_ARG} --ipcache-hostname --dpi-desync=syndata,fake,multisplit --dpi-desync-split-pos=sld+1 --dpi-desync-fake-syndata=tls_clienthello_7.bin --dpi-desync-fake-tls=0x0F0F0E0F --dpi-desync-fake-tls=tls_clienthello_9.bin --dpi-desync-fake-tls-mod=rnd,dupsid --dpi-desync-fooling=md5sig --dpi-desync-autottl --dup=2 --dup-fooling=md5sig --dup-autottl --dup-cutoff=n3"""
    },
    "multisplit_fake_tls_md5sig": {
        "name": "multisplit и md5sig 1",
        "description": "Стандартный multisplit и md5sig и фейк TLS 1",
        "author": "hz",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=fake,multisplit --dpi-desync-split-pos=sld+1 --dpi-desync-fake-tls=0x0F0F0E0F --dpi-desync-fake-tls=tls_clienthello_1.bin --dpi-desync-fake-tls-mod=rnd,dupsid --dpi-desync-fooling=md5sig --dpi-desync-autottl --dup=2 --dup-fooling=md5sig --dup-autottl --dup-cutoff=n3"""
    },
    "multisplit_fake_tls_md5sig_2": {
        "name": "YTDisBystro 3.4 v3",
        "description": "Стандартный multisplit и md5sig и фейк TLS 14",
        "author": "hz",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=fake,multisplit --dpi-desync-split-pos=sld+1 --dpi-desync-fake-tls=0x0F0F0E0F --dpi-desync-fake-tls=tls_clienthello_14.bin --dpi-desync-fake-tls-mod=rnd,dupsid --dpi-desync-fooling=md5sig --dpi-desync-autottl --dup=2 --dup-fooling=md5sig --dup-autottl --dup-cutoff=n3"""
    },
    "multisplit_seqovl_pos": {
        "name": "multisplit seqovl с split pos",
        "description": "Базовый multisplit и seqovl с фейками и нарезкой",
        "author": "hz",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=fake,multisplit --dpi-desync-split-seqovl=2 --dpi-desync-split-pos=3 --dpi-desync-fake-tls=tls_clienthello_2.bin --dpi-desync-ttl=3"""
    },
    "multisplit_seqovl_pos_2": {
        "name": "multisplit seqovl с split pos и badseq",
        "description": "Базовый multisplit и seqovl с фейками, нарезкой и  badseq",
        "author": "hz",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=fake,multisplit --dpi-desync-fooling=badseq --dpi-desync-split-seqovl=2 --dpi-desync-split-pos=2 --dpi-desync-fake-tls=tls_clienthello_2n.bin --dpi-desync-fake-tls-mod=rnd --dpi-desync-autottl"""
    },
    "multidisorder_repeats_md5sig": {
        "name": "original bol-van v2",
        "description": "multidisorder с fake tls mod",
        "author": "bol-van",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=11 --dpi-desync-fooling=md5sig --dpi-desync-fake-tls-mod=rnd,dupsid,sni=www.google.com"""
    },
    "multidisorder_repeats_md5sig_2": {
        "name": "multidisorder с повторами и md5ig",
        "description": "multidisorder с fake tls clienthello",
        "author": "hz",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=11 --dpi-desync-fooling=md5sig --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin"""
    },
    "alt1_161": {
        "name": "general (alt v1) 1.8.2",
        "description": "fake,split autottl 5 repeats 6 badseq и fake tls google",
        "author": "hz",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=fake,split --dpi-desync-autottl=5 --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin"""
    },
    "alt2_182": {
        "name": "general (alt v2) 1.8.2",
        "description": "fake,split seqovl 652 pos 2 seqovl pattern",
        "author": "hz",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=split2 --dpi-desync-split-seqovl=652 --dpi-desync-split-pos=2 --dpi-desync-split-seqovl-pattern=tls_clienthello_www_google_com.bin"""
    },
    "general_alt2183": {
        "name": "general (alt v2) 1.8.3 / 1.8.4",
        "description": "multisplit seqovl 652 pos 2 seqovl pattern",
        "author": "Flowseal",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=multisplit --dpi-desync-split-seqovl=652 --dpi-desync-split-pos=2 --dpi-desync-split-seqovl-pattern=tls_clienthello_www_google_com.bin"""
    },
    "general_alt3183": {
        "name": "general (alt v3) 1.6.1",
        "description": "split pos 1 autottl badseq repeats 8",
        "author": "Flowseal",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=split --dpi-desync-split-pos=1 --dpi-desync-autottl --dpi-desync-fooling=badseq --dpi-desync-repeats=8"""
    },
    "general_alt3183_2": {
        "name": "general (alt v3) 1.8.2 / 1.8.4",
        "description": "fakedsplit pos 1 autottl badseq repeats 8",
        "author": "Flowseal",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=fakedsplit --dpi-desync-split-pos=1 --dpi-desync-autottl --dpi-desync-fooling=badseq --dpi-desync-repeats=8"""
    },
    "general_alt4_161": {
        "name": "general (alt v4) 1.6.1",
        "description": "fake split2 repeats 6 md5sig tls google",
        "author": "Flowseal",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=fake,split2 --dpi-desync-repeats=6 --dpi-desync-fooling=md5sig --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin"""
    },
    "general_alt4_182": {
        "name": "general (alt v4) 1.8.2 / 1.8.4",
        "description": "fake multisplit repeats 6 md5sig tls google",
        "author": "Flowseal",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=fake,multisplit --dpi-desync-repeats=6 --dpi-desync-fooling=md5sig --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin"""
    },
    "general_alt5_182": {
        "name": "general (alt v5) 1.8.2 / 1.8.4",
        "description": "syndata",
        "author": "Flowseal",
        "label": LABEL_CAUTION,
        "args": f"""{BASE_ARG} --ipcache-hostname --dpi-desync=syndata"""
    },
     "general_alt6_182": {
        "name": "general (alt v6) 1.8.2",
        "description": "multisplit repeats 2 seqovl 681 pos 1 badseq hopbyhop2",
        "author": "Flowseal",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=multisplit --dpi-desync-repeats=2 --dpi-desync-split-seqovl=681 --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq,hopbyhop2 --dpi-desync-split-seqovl-pattern=tls_clienthello_www_google_com.bin"""
    },
    "general_alt6_181": {
        "name": "general (alt v6) 1.8.1",
        "description": "split2 repeats 2 seqovl 681 pos 1 badseq hopbyhop2",
        "author": "Flowseal",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=split2 --dpi-desync-repeats=2 --dpi-desync-split-seqovl=681 --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq,hopbyhop2 --dpi-desync-split-seqovl-pattern=tls_clienthello_www_google_com.bin"""
    },
    "general_alt6_184": {
        "name": "general (alt v6) 1.8.4",
        "description": "multisplit seqovl 681 pos 1 seqovl pattern",
        "author": "Flowseal",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=multisplit --dpi-desync-split-seqovl=681 --dpi-desync-split-pos=1 --dpi-desync-split-seqovl-pattern=tls_clienthello_www_google_com.bin"""
    },
    "general_alt7_184": {
        "name": "general (alt v7) 1.8.4",
        "description": "multisplit seqovl 681 pos 1 seqovl pattern",
        "author": "Flowseal",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=multisplit --dpi-desync-split-pos=2,sniext+1 --dpi-desync-split-seqovl=679 --dpi-desync-split-seqovl-pattern=tls_clienthello_www_google_com.bin"""
    },
    "general_alt8_185": {
        "name": "general (alt v8) 1.8.5",
        "description": "fake autottl repeats 6 badseq increment 2",
        "author": "V3nilla",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=fake --dpi-desync-fake-tls-mod=none --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-badseq-increment=2"""
    },
    "general_alt8_185_2": {
        "name": "general (alt v8) 1.8.5 (2)",
        "description": "fake autottl repeats 6 badseq increment 0",
        "author": "V3nilla",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=fake --dpi-desync-fake-tls-mod=none --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-badseq-increment=0"""
    },
    "general_alt8_185_3": {
        "name": "general (alt v8) 1.8.5 (3)",
        "description": "fake autottl repeats 6 badseq increment 100000",
        "author": "V3nilla",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=fake --dpi-desync-fake-tls-mod=none --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-badseq-increment=100000"""
    },
    "general_fake_tls_auto_alt_184": {
        "name": "general (fake TLS auto alt) 1.8.4",
        "description": "multisplit seqovl 681 pos 1 seqovl pattern",
        "author": "Flowseal",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=fake,fakedsplit --dpi-desync-split-pos=1 --dpi-desync-autottl --dpi-desync-fooling=badseq --dpi-desync-badseq-increment=10000000 --dpi-desync-repeats=8 --dpi-desync-fake-tls-mod=rnd,dupsid,sni=www.google.com"""
    },
    "general_fake_tls_auto_alt_185": {
        "name": "general (fake TLS auto alt) 1.8.5",
        "description": "multisplit seqovl 681 pos 1 seqovl pattern",
        "author": "Flowseal",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=fake,fakedsplit --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq --dpi-desync-badseq-increment=10000000 --dpi-desync-repeats=8 --dpi-desync-fake-tls-mod=rnd,dupsid,sni=www.google.com"""
    },
    "general_fake_tls_auto_alt2_184": {
        "name": "general (fake TLS auto alt2) 1.8.4",
        "description": "multisplit seqovl 681 pos 1 seqovl pattern",
        "author": "Flowseal",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=fake,multisplit --dpi-desync-split-seqovl=681 --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq --dpi-desync-badseq-increment=10000000 --dpi-desync-repeats=8 --dpi-desync-split-seqovl-pattern=tls_clienthello_www_google_com.bin --dpi-desync-fake-tls-mod=rnd,dupsid,sni=www.google.com"""
    },
    "general_fake_tls_auto_alt3_184": {
        "name": "general (fake TLS auto alt3) 1.8.4",
        "description": "multisplit seqovl 681 pos 1 seqovl pattern",
        "author": "Flowseal",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=fake,multisplit --dpi-desync-split-seqovl=681 --dpi-desync-split-pos=1 --dpi-desync-fooling=ts --dpi-desync-repeats=8 --dpi-desync-split-seqovl-pattern=tls_clienthello_www_google_com.bin --dpi-desync-fake-tls-mod=rnd,dupsid,sni=www.google.com"""
    },
    "general_fake_tls_auto_184": {
        "name": "general (fake TLS auto) 1.8.4",
        "description": "multisplit seqovl 681 pos 1 seqovl pattern",
        "author": "Flowseal",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=11 --dpi-desync-fooling=badseq --dpi-desync-fake-tls-mod=rnd,dupsid,sni=sun6-21.userapi.com"""
    },
    "multisplit_1_midsld": {
        "name": "multisplit seqovl 1 и midsld",
        "description": "Базовая мультисплит с midsld",
        "author": "hz",
        "label": None,
        "args": f"""{BASE_ARG} --lua-desync=multisplit:pos=1,midsld"""
    },
    "fake_multidisorder_1_split_pos_1": {
        "name": "fake multidisorder badsum split pos 1",
        "description": "Базовая мультисплит с midsld",
        "author": "hz",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=fake,multidisorder --dpi-desync-fooling=badsum --dpi-desync-split-pos=1"""
    },
    "disorder2_badseq_tls_google": {
        "name": "disorder2 badseq tls google",
        "description": "Cплит2 badseq с фейком tls от Google",
        "author": "hz",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=syndata,disorder2 --dpi-desync-split-pos=3 --dpi-desync-repeats=11 --dpi-desync-fooling=badseq --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin"""
    },
    "dis11": {
        "name": "split badseq 10",
        "description": "Cплит2 с фуллингом badseq и 10 повторами",
        "author": "hz",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=split --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq --dpi-desync-repeats=10 --dpi-desync-autottl"""
    },
    "dis12": {
        "name": "split badseq 10 ttl",
        "description": "Cплит2 с фуллингом badseq и 10 повторами и ttl 3",
        "author": "hz",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=split --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq --dpi-desync-repeats=10 --dpi-desync-ttl=3"""
    },
    "dis13": {
        "name": "fakedsplit badsrq 10",
        "description": "Фейки и сплиты с фуллингом badseq и 10 повторами",
        "author": "hz",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=fakedsplit --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq --dpi-desync-repeats=10 --dpi-desync-autottl"""
    },
    "fake_autottl_repeats_6_badseq": {
        "name": "alt mgts (v1) 1.6.1 / 1.8.4",
        "description": "fake autottl repeats 6 badseq",
        "author": "hz",
        "label": None,
        "args": f"""{BASE_ARG} """
    },
    "general_simplefake_185": {
        "name": "general simple fake alt 1.8.5",
        "description": "fake autottl repeats 6 badseq",
        "author": "hz",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=fake --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-badseq-increment=10000000 --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin"""
    },
    "altmgts2_161_2": {
        "name": "alt mgts (v2) 1.6.1 / 1.8.4",
        "description": "fake autottl repeats 6 md5sig",
        "author": "hz",
        "label": None,
        "args": f"""{BASE_ARG} """
    },
    "general_simple_fake_165_2": {
        "name": "general simple fake 1.8.5 v2",
        "description": "fake autottl repeats 6 ts",
        "author": "hz",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=fake --dpi-desync-repeats=6 --dpi-desync-fooling=ts --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin"""
    },
    "altmgts2_161_3": {
        "name": "alt mgts (v3) 1.6.1",
        "description": "fake autottl repeats 6 md5sig",
        "author": "hz",
        "label": None,
        "args": f"""{BASE_ARG} """
    },
    "ankddev10": {
        "name": "aankddev (v10)",
        "description": "syndata multidisorder split pos 4 repeats 10 md5sig fake tls vk kyber",
        "author": "hz",
        "label": LABEL_CAUTION,
        "args": f"""{BASE_ARG} --ipcache-hostname --dpi-desync=syndata,multidisorder --dpi-desync-split-pos=4 --dpi-desync-repeats=10 --dpi-desync-fooling=md5sig --dpi-desync-fake-tls=tls_clienthello_vk_com_kyber.bin"""
    },
    "split2_seqovl_vk": {
        "name": "Устаревший split2 с clienthello от VK",
        "description": "split2 и 625 seqovl с sniext и vk ttl 2 от конторы пидорасов",
        "author": "hz",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=fake,split2 --dpi-desync-split-seqovl=625 --dpi-desync-split-tls=sniext --dpi-desync-fake-tls=tls_clienthello_vk_com.bin --dpi-desync-ttl=2"""
    },
    "split2_seqovl_google": {
        "name": "Устаревший split2 с clienthello от google",
        "description": "split2 и 1 seqovl с sniext и google ttl 4",
        "author": "hz",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=fake,split2 --dpi-desync-split-seqovl=1 --dpi-desync-split-tls=sniext --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --dpi-desync-ttl=4"""
    },
    "split2_split": {
        "name": "Устаревший split2 split",
        "description": "Базовый split2 и нарезка",
        "author": "hz",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=fake,split2 --dpi-desync-split-seqovl=2 --dpi-desync-split-pos=3"""
    },
    "split2_seqovl_652": {
        "name": "split2 seqovl 652",
        "description": "Устаревший split2 с seqovl 652 и паттерном 4",
        "author": "hz",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=fake,split2 --dpi-desync-split-seqovl=652 --dpi-desync-split-pos=3,midsld-1 --dpi-desync-split-seqovl-pattern=tls_clienthello_4.bin"""
    },
    "split2_split_google": {
        "name": "Устаревший split2 split seqovl google",
        "description": "Базовый split2 и нарезка с fake tls google",
        "author": "hz",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=fake,split2 --dpi-desync-split-seqovl=2 --dpi-desync-split-pos=3 --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --dpi-desync-ttl=3"""
    },
    "split2_split_2": {
        "name": "Устаревший split2 split seqovl 2",
        "description": "Базовый split2 и нарезка с fake tls 2",
        "author": "hz",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=fake,split2 --dpi-desync-split-seqovl=2 --dpi-desync-split-pos=3 --dpi-desync-fake-tls=tls_clienthello_2.bin --dpi-desync-autottl=2"""
    },
    "fake_split2": {
        "name": "Устаревший fake split2 seqovl 1",
        "description": "fake и split2, нарезка с fake tls 2",
        "author": "hz",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=fake,split2 --dpi-desync-split-seqovl=1 --dpi-desync-split-tls=sniext --dpi-desync-fake-tls=tls_clienthello_3.bin --dpi-desync-ttl=2"""
    },
    "split_seqovl": {
        "name": "Устаревший split и seqovl",
        "description": "Базовый split и seqovl",
        "author": "hz",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=split --dpi-desync-split-seqovl=1 --dpi-desync-split-tls=sniext --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --dpi-desync-ttl=1"""
    },
    "split_pos_badseq": {
        "name": "Ростелеком & Мегафон",
        "description": "Базовый split и badseq",
        "author": "hz",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=split --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq --dpi-desync-repeats=10 --dpi-desync-autottl=2"""
    },
    "split_pos_badseq_10": {
        "name": "split badseq 10 и cutoff",
        "description": "split и badseq разрез и 10 повторов",
        "author": "hz",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=split --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq --dpi-desync-repeats=10 --dpi-desync-cutoff=d2 --dpi-desync-ttl=3"""
    },
    "split_pos_3": {
        "name": "split pos 3 и повторы",
        "description": "split разрез в 3 и 4 повтора",
        "author": "hz",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=split --dpi-desync-split-pos=3 --dpi-desync-repeats=4 --dpi-desync-autottl=1"""
    },
    "general_alt183": {
        "name": "general (alt) 1.8.3 / 1.8.4",
        "description": "Потом опишу подробнее",
        "author": "Flowseal",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=fake,fakedsplit --dpi-desync-autottl=5 --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin"""
    },
    "general_alt185": {
        "name": "general (alt) 1.8.5",
        "description": "Потом опишу подробнее",
        "author": "Flowseal",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=fake,fakedsplit --dpi-desync-repeats=6 --dpi-desync-fooling=ts --dpi-desync-fakedsplit-pattern=0x00 --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin"""
    },
    "launcher_zapret_2_9_1_v1": {
        "name": "Launcher zapret 2.9.1 v1",
        "description": "fake multidisorder pos 7 fake-tls=0F0F0F0F fake-tls=3.bin badseq,autottl 2:2-12",
        "author": "Dronatar",
        "label": LABEL_RECOMMENDED,
        "args": f"""{BASE_ARG} --dpi-desync=fake,multidisorder --dpi-desync-split-pos=7,sld+1 --dpi-desync-fake-tls=0x0F0F0F0F --dpi-desync-fake-tls=3.bin --dpi-desync-fake-tls-mod=rnd,dupsid,sni=fonts.google.com --dpi-desync-fooling=badseq --dpi-desync-autottl 2:2-12"""
    },
    "fake_md5sig_fake_tls": {
        "name": "Launcher zapret 2.9.1 v2",
        "description": "Базовая десинхронизация md5sig с фейком tls",
        "author": "hz",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=fake --dpi-desync-fooling=md5sig --dpi-desync-fake-tls-mod=rnd,rndsni,padencap"""
    },
    "launcher_zapret_2_9_1_v3": {
        "name": "Launcher zapret 2.9.1 v3",
        "description": "multidisorder pos 1 midsld fake-tls=3.bin autottl",
        "author": "Dronatar",
        "label": LABEL_RECOMMENDED,
        "args": f"""{BASE_ARG} --dpi-desync=multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls=3.bin --dpi-desync-autottl"""
    },
    "launcher_zapret_2_9_1_v4": {
        "name": "Launcher zapret 2.9.1 v4",
        "description": "multisplit pos 1 seqovl 681 pattern 4.bin dpi-desync-repeats=2",
        "author": "Dronatar",
        "label": LABEL_RECOMMENDED,
        "args": f"""{BASE_ARG} --dpi-desync=multisplit --dpi-desync-repeats=2 --dpi-desync-split-seqovl=681 --dpi-desync-split-pos=1 --dpi-desync-split-seqovl-pattern=4.bin"""
    },
    "launcher_zapret_3_0_0_extreme": {
        "name": "Launcher zapret 3.0.0 Extreme Mode",
        "description": "multisplit pos 1 seqovl 681 pattern 4.bin dpi-desync-repeats=2",
        "author": "Dronatar",
        "label": LABEL_RECOMMENDED,
        "args": f"""{BASE_ARG} --dpi-desync=multidisorder --dpi-desync-split-pos=1,midsld"""
    },
    "google_tcp_none": {
        "name": "Не применять для Google",
        "description": "Отключить обработку Google",
        "author": "System",
        "label": None,
        "args": ""  # Пустая строка = не добавлять аргументы
    }
}
from .constants import LABEL_RECOMMENDED, LABEL_CAUTION, LABEL_EXPERIMENTAL, LABEL_STABLE

YOUTUBE_BASE_ARG = "--filter-tcp=80,443 --hostlist=youtube.txt"

# YouTube стратегии
YOUTUBE_STRATEGIES = {
    "multisplit_seqovl_midsld": {
        "name": "multisplit seqovl midsld",
        "description": "Самая простая стратегия multisplit для YouTube",
        "author": None,
        "label": LABEL_RECOMMENDED,
        "args": f"""{YOUTUBE_BASE_ARG} --dpi-desync=multisplit --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=midsld-1 --new"""
    },
    "original_bolvan_v2_badsum": {
        "name": "Если стратегия не работает смени её!",
        "description": "Базовая стратегия multidisorder для YouTube",
        "author": "OrigBolvan",
        "label": LABEL_RECOMMENDED,
        "args": f"""{YOUTUBE_BASE_ARG} --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-fake-tls-mod=rnd,dupsid,sni=www.google.com --new"""
    },
    "bolvan_md5sig": {
        "name": "BolVan md5sig 11",
        "description": "Другой метод фуллинга + большее число повторений",
        "author": "OrigBolvan",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG} --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=11 --dpi-desync-fooling=md5sig --new"""
    },
    "bolvan_md5sig_2": {
        "name": "BolVan v3",
        "description": "Другой метод фуллинга + большее число повторений + tls от гугла",
        "author": "Уфанет",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG} --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=11 --dpi-desync-fooling=md5sig  --dpi-desync-fake-tls-mod=rnd,dupsid,sni=www.google.com --new"""
    },
    "bolvan_fake_tls": {
        "name": "BolVan fake TLS 4",
        "description": "Используется фейковый Clienthello",
        "author": "OrigBolvan",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG} --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=4 --dpi-desync-fake-tls=tls_clienthello_18.bin --dpi-desync-fooling=badseq --new"""
    },
    "multisplit_seqovl": {
        "name": "multisplit и seqovl 1",
        "description": "Используется multisplit и seqovl 1",
        "author": "hz",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG} --dpi-desync=multisplit --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=midsld+1 --new"""
    },
    "fake_multisplit_seqovl_md5sig": {
        "name": "fake multisplit и seqovl 1 md5sig",
        "description": "Используется multisplit и seqovl 1",
        "author": "hz",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG} --dpi-desync=fake,multisplit --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=midsld-1 --dpi-desync-fooling=md5sig,badseq --dpi-desync-fake-tls=tls_clienthello_4.bin --dpi-desync-ttl=2 --new"""
    },
    "split_pos_md5sig": {
        "name": "Нестандартная нарезка позиций и md5sig",
        "description": "method+2,midsld,5 и ttl 0",
        "author": "hz",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG} --dpi-desync=fake,multidisorder --dpi-desync-split-pos=method+2,midsld,5 --dpi-desync-ttl=0 --dpi-desync-fooling=md5sig,badsum,badseq --dpi-desync-repeats=15 --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --new"""
    },
    "multisplit_1": {
        "name": "Мультисплит и смещение +1",
        "description": "Базовая стратегия десинхронизации multisplit",
        "author": "hz",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG} --dpi-desync=multisplit --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=sld+1 --new"""
    },
    "multisplit_2": {
        "name": "Мультисплит и смещение -1",
        "description": "Базовая стратегия десинхронизации multisplit",
        "author": "hz",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG} --dpi-desync=multisplit --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=sld-1 --new"""
    },
    "multisplit_3": {
        "name": "Мультисплит и смещение midsld +1",
        "description": "Базовая стратегия десинхронизации multisplit и смещение midsld",
        "author": "hz",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG} --dpi-desync=multisplit --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=midsld+1 --dpi-desync-split-seqovl-pattern=tls_clienthello_7.bin --new"""
    },
    "multidisorder_fake_tls_1": {
        "name": "multidisorder 7 Fake TLS fonts и badseq",
        "description": "Кастомная и сложная стратегия с фейком fonts",
        "author": "hz",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG} --dpi-desync=fake,multidisorder --dpi-desync-split-pos=7,sld+1 --dpi-desync-fake-tls=0x0F0F0F0F --dpi-desync-fake-tls=tls_clienthello_4.bin --dpi-desync-fake-tls-mod=rnd,dupsid,sni=fonts.google.com --dpi-desync-fooling=badseq --dpi-desync-autottl --new"""
    },
    "multidisorder_fake_tls_2": {
        "name": "multidisorder 7 Fake TLS calendar и badseq",
        "description": "Кастомная и сложная стратегия с фейком calendar",
        "author": "hz",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG} --dpi-desync=fake,multidisorder --dpi-desync-split-pos=7,sld+1 --dpi-desync-fake-tls=0x0F0F0F0F --dpi-desync-fake-tls=tls_clienthello_4.bin --dpi-desync-fake-tls-mod=rnd,dupsid,sni=calendar.google.com --dpi-desync-fooling=badseq --dpi-desync-autottl --new"""
    },
    "multidisorder_badseq_w3": {
        "name": "multidisorder badseq w3",
        "description": "Обратная стратегия с фуллингом badseq и фейком w3",
        "author": "hz",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG} --dpi-desync=fake,multidisorder --dpi-desync-fake-tls=dtls_clienthello_w3_org.bin --dpi-desync-split-pos=1,midsld --dpi-desync-fooling=badseq,md5sig --new"""
    },
    "multidisorder_rnd_split": {
        "name": "multidisorder rnd split",
        "description": "Обратная стратегия с нестандартной стратегией и фейком TLS",
        "author": "hz",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG} --dpi-desync=fake,multidisorder --dpi-desync-fake-tls-mod=rnd,dupsid --dpi-desync-repeats=3 --dpi-desync-split-pos=100,midsld,sniext+1,endhost-2,-10 --dpi-desync-ttl=4 --new"""
    },
    "multisplit_17": {
        "name": "multisplit 17",
        "description": "Мульти нарезка с md5sig и фейком TLS",
        "author": "hz",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG} --dpi-desync=fake,multisplit --dpi-desync-split-pos=2,midsld --dpi-desync-fake-tls=tls_clienthello_17.bin --dpi-desync-fake-tls-mod=rnd,dupsid --dpi-desync-fooling=md5sig --dpi-desync-autottl --dup=2 --dup-fooling=md5sig --dup-autottl --dup-cutoff=n3 --new"""
    },
    "syndata_md5sig": {
        "name": "multisplit и md5sig",
        "description": "Экспериментальная стратегия multisplit и md5sig",
        "author": "hz",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG} --dpi-desync=fake,multisplit --dpi-desync-split-pos=sld+1 --dpi-desync-fake-tls=0x0F0F0E0F --dpi-desync-fake-tls=tls_clienthello_9.bin --dpi-desync-fake-tls-mod=rnd,dupsid --dpi-desync-fooling=md5sig --dpi-desync-autottl --dup=2 --dup-fooling=md5sig --dup-autottl --dup-cutoff=n3 --new""" # раньше тут было syndata --dpi-desync-fake-syndata=tls_clienthello_7.bin
    },
    "fake_multidisorder_seqovl_fake_tls": {
        "name": "fake multidisorder seqovl fake tls",
        "description": "ОЧЕНЬ сложная стратегия с фейком TLS и seqovl",
        "author": "hz",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG} --dpi-desync=fake,multidisorder --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=sld+1 --dpi-desync-fake-tls=0x0F0F0E0F --dpi-desync-fake-tls=tls_clienthello_9.bin --dpi-desync-fake-tls-mod=rnd,dupsid --dpi-desync-fooling=md5sig --dpi-desync-autottl --dup=2 --dup-fooling=md5sig --dup-autottl --dup-cutoff=n3 --new"""
    },
    "syndata_md5sig_2": {
        "name": "multisplit и md5sig 9",
        "description": "Стандартный multisplit и md5sig и фейк TLS 9",
        "author": "hz",
        "label": LABEL_CAUTION,
        "args": f"""{YOUTUBE_BASE_ARG} --ipcache-hostname --dpi-desync=syndata,fake,multisplit --dpi-desync-split-pos=sld+1 --dpi-desync-fake-syndata=tls_clienthello_7.bin --dpi-desync-fake-tls=0x0F0F0E0F --dpi-desync-fake-tls=tls_clienthello_9.bin --dpi-desync-fake-tls-mod=rnd,dupsid --dpi-desync-fooling=md5sig --dpi-desync-autottl --dup=2 --dup-fooling=md5sig --dup-autottl --dup-cutoff=n3 --new"""
    },
    "multisplit_fake_tls_md5sig": {
        "name": "multisplit и md5sig 1",
        "description": "Стандартный multisplit и md5sig и фейк TLS 1",
        "author": "hz",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG} --dpi-desync=fake,multisplit --dpi-desync-split-pos=sld+1 --dpi-desync-fake-tls=0x0F0F0E0F --dpi-desync-fake-tls=tls_clienthello_1.bin --dpi-desync-fake-tls-mod=rnd,dupsid --dpi-desync-fooling=md5sig --dpi-desync-autottl --dup=2 --dup-fooling=md5sig --dup-autottl --dup-cutoff=n3 --new"""
    },
    "multisplit_fake_tls_md5sig_2": {
        "name": "multisplit и md5sig 14",
        "description": "Стандартный multisplit и md5sig и фейк TLS 14",
        "author": "hz",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG} --dpi-desync=fake,multisplit --dpi-desync-split-pos=sld+1 --dpi-desync-fake-tls=0x0F0F0E0F --dpi-desync-fake-tls=tls_clienthello_14.bin --dpi-desync-fake-tls-mod=rnd,dupsid --dpi-desync-fooling=md5sig --dpi-desync-autottl --dup=2 --dup-fooling=md5sig --dup-autottl --dup-cutoff=n3 --new"""
    },
    "multisplit_seqovl_pos": {
        "name": "multisplit seqovl с split pos",
        "description": "Базовый multisplit и seqovl с фейками и нарезкой",
        "author": "hz",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG} --dpi-desync=fake,multisplit --dpi-desync-split-seqovl=2 --dpi-desync-split-pos=3 --dpi-desync-fake-tls=tls_clienthello_2.bin --dpi-desync-ttl=3 --new"""
    },
    "multisplit_seqovl_pos_2": {
        "name": "multisplit seqovl с split pos и badseq",
        "description": "Базовый multisplit и seqovl с фейками, нарезкой и  badseq",
        "author": "hz",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG} --dpi-desync=fake,multisplit --dpi-desync-fooling=badseq --dpi-desync-split-seqovl=2 --dpi-desync-split-pos=2 --dpi-desync-fake-tls=tls_clienthello_2n.bin --dpi-desync-fake-tls-mod=rnd --dpi-desync-autottl --new"""
    },
    "multidisorder_repeats_md5sig": {
        "name": "multidisorder с повторами и md5ig",
        "description": "multidisorder с fake tls mod",
        "author": "hz",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG} --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=11 --dpi-desync-fooling=md5sig --dpi-desync-fake-tls-mod=rnd,dupsid,sni=www.google.com --new"""
    },
    "multidisorder_repeats_md5sig_2": {
        "name": "multidisorder с повторами и md5ig",
        "description": "multidisorder с fake tls clienthello",
        "author": "hz",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG} --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=11 --dpi-desync-fooling=md5sig --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --new"""
    },
    "alt1_161": {
        "name": "general (alt v1) 1.8.2",
        "description": "fake,split autottl 5 repeats 6 badseq и fake tls google",
        "author": "hz",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG} --dpi-desync=fake,split --dpi-desync-autottl=5 --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --new"""
    },
    "alt2_182": {
        "name": "general (alt v2) 1.8.2",
        "description": "fake,split seqovl 652 pos 2 seqovl pattern",
        "author": "hz",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG} --dpi-desync=split2 --dpi-desync-split-seqovl=652 --dpi-desync-split-pos=2 --dpi-desync-split-seqovl-pattern="tls_clienthello_www_google_com.bin"  --new"""
    },
    "general_alt2183": {
        "name": "general (alt v2) 1.8.3",
        "description": "multisplit seqovl 652 pos 2 seqovl pattern",
        "author": "Flowseal",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG} --dpi-desync=multisplit --dpi-desync-split-seqovl=652 --dpi-desync-split-pos=2 --dpi-desync-split-seqovl-pattern=tls_clienthello_www_google_com.bin --new"""
    },
    "general_alt3183": {
        "name": "general (alt v3) 1.6.1",
        "description": "split pos 1 autottl badseq repeats 8",
        "author": "Flowseal",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG} --dpi-desync=split --dpi-desync-split-pos=1 --dpi-desync-autottl --dpi-desync-fooling=badseq --dpi-desync-repeats=8 --new"""
    },
    "general_alt3183_2": {
        "name": "general (alt v3) 1.8.2",
        "description": "fakedsplit pos 1 autottl badseq repeats 8",
        "author": "Flowseal",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG} --dpi-desync=fakedsplit --dpi-desync-split-pos=1 --dpi-desync-autottl --dpi-desync-fooling=badseq --dpi-desync-repeats=8 --new"""
    },
    "general_alt4_161": {
        "name": "general (alt v4) 1.6.1",
        "description": "fake split2 repeats 6 md5sig tls google",
        "author": "Flowseal",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG} --dpi-desync=fake,split2 --dpi-desync-repeats=6 --dpi-desync-fooling=md5sig --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --new"""
    },
    "general_alt4_182": {
        "name": "general (alt v4) 1.8.2",
        "description": "fake multisplit repeats 6 md5sig tls google",
        "author": "Flowseal",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG} --dpi-desync=fake,multisplit --dpi-desync-repeats=6 --dpi-desync-fooling=md5sig --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --new"""
    },
    "general_alt5_182": {
        "name": "general (alt v5) 1.8.2",
        "description": "syndata",
        "author": "Flowseal",
        "label": LABEL_CAUTION,
        "args": f"""{YOUTUBE_BASE_ARG} --ipcache-hostname --dpi-desync=syndata --new"""
    },
    "general_alt6_181": {
        "name": "general (alt v6) 1.8.1",
        "description": "split2 repeats 2 seqovl 681 pos 1 badseq hopbyhop2",
        "author": "Flowseal",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG} --dpi-desync=split2 --dpi-desync-repeats=2 --dpi-desync-split-seqovl=681 --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq,hopbyhop2 --dpi-desync-split-seqovl-pattern=tls_clienthello_www_google_com.bin --new"""
    },
     "general_alt6_182": {
        "name": "general (alt v6) 1.8.2",
        "description": "multisplit repeats 2 seqovl 681 pos 1 badseq hopbyhop2",
        "author": "Flowseal",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG} --dpi-desync=multisplit --dpi-desync-repeats=2 --dpi-desync-split-seqovl=681 --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq,hopbyhop2 --dpi-desync-split-seqovl-pattern=tls_clienthello_www_google_com.bin --new"""
    },
    "fake_autottl_repeats_6_badseq": {
        "name": "alt mgts (v1) 1.6.1",
        "description": "fake autottl repeats 6 badseq",
        "author": "hz",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG} --dpi-desync=fake --dpi-desync-autottl=2 --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --new"""
    },
    "altmgts2_161_2": {
        "name": "alt mgts (v2) 1.6.1",
        "description": "fake autottl repeats 6 md5sig",
        "author": "hz",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG} --dpi-desync=fake --dpi-desync-repeats=6 --dpi-desync-fooling=md5sig --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --new"""
    },
    "altmgts2_161_3": {
        "name": "alt mgts (v3) 1.6.1",
        "description": "fake autottl repeats 6 md5sig",
        "author": "hz",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG} --dpi-desync=fake --dpi-desync-autottl=2 --dpi-desync-repeats=6 --dpi-desync-fooling=md5sig --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --new"""
    },
    "ankddev10": {
        "name": "aankddev (v10)",
        "description": "syndata multidisorder split pos 4 repeats 10 md5sig fake tls vk kyber",
        "author": "hz",
        "label": LABEL_CAUTION,
        "args": f"""{YOUTUBE_BASE_ARG} --ipcache-hostname --dpi-desync=syndata,multidisorder --dpi-desync-split-pos=4 --dpi-desync-repeats=10 --dpi-desync-fooling=md5sig --dpi-desync-fake-tls=tls_clienthello_vk_com_kyber.bin --new"""
    },
    "split2_seqovl_vk": {
        "name": "Устаревший split2 с clienthello от VK",
        "description": "split2 и 625 seqovl с sniext и vk ttl 2 от конторы пидорасов",
        "author": "hz",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG} --dpi-desync=fake,split2 --dpi-desync-split-seqovl=625 --dpi-desync-split-tls=sniext --dpi-desync-fake-tls=tls_clienthello_vk_com.bin --dpi-desync-ttl=2 --new"""
    },
    "split2_seqovl_google": {
        "name": "Устаревший split2 с clienthello от google",
        "description": "split2 и 1 seqovl с sniext и google ttl 4",
        "author": "hz",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG} --dpi-desync=fake,split2 --dpi-desync-split-seqovl=1 --dpi-desync-split-tls=sniext --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --dpi-desync-ttl=4 --new"""
    },
    "split2_split": {
        "name": "Устаревший split2 split",
        "description": "Базовый split2 и нарезка",
        "author": "hz",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG} --dpi-desync=fake,split2 --dpi-desync-split-seqovl=2 --dpi-desync-split-pos=3 --new"""
    },
    "split2_seqovl_652": {
        "name": "split2 seqovl 652",
        "description": "Устаревший split2 с seqovl 652 и паттерном 4",
        "author": "hz",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG} --dpi-desync=fake,split2 --dpi-desync-split-seqovl=652 --dpi-desync-split-pos=3,midsld-1 --dpi-desync-split-seqovl-pattern=tls_clienthello_4.bin --new"""
    },
    "split2_split_google": {
        "name": "Устаревший split2 split seqovl google",
        "description": "Базовый split2 и нарезка с fake tls google",
        "author": "hz",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG} --dpi-desync=fake,split2 --dpi-desync-split-seqovl=2 --dpi-desync-split-pos=3 --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --dpi-desync-ttl=3 --new"""
    },
    "split2_split_2": {
        "name": "Устаревший split2 split seqovl 2",
        "description": "Базовый split2 и нарезка с fake tls 2",
        "author": "hz",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG} --dpi-desync=fake,split2 --dpi-desync-split-seqovl=2 --dpi-desync-split-pos=3 --dpi-desync-fake-tls=tls_clienthello_2.bin --dpi-desync-autottl=2 --new"""
    },
    "fake_split2": {
        "name": "Устаревший fake split2 seqovl 1",
        "description": "fake и split2, нарезка с fake tls 2",
        "author": "hz",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG} --dpi-desync=fake,split2 --dpi-desync-split-seqovl=1 --dpi-desync-split-tls=sniext --dpi-desync-fake-tls=tls_clienthello_3.bin --dpi-desync-ttl=2 --new"""
    },
    "split_seqovl": {
        "name": "Устаревший split и seqovl",
        "description": "Базовый split и seqovl",
        "author": "hz",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG} --dpi-desync=split --dpi-desync-split-seqovl=1 --dpi-desync-split-tls=sniext --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --dpi-desync-ttl=1 --new"""
    },
    "split_pos_badseq": {
        "name": "Ростелеком & Мегафон",
        "description": "Базовый split и badseq",
        "author": "hz",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG} --dpi-desync=split --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq --dpi-desync-repeats=10 --dpi-desync-autottl=2 --new"""
    },
    "split_pos_badseq_10": {
        "name": "split badseq 10 и cutoff",
        "description": "split и badseq разрез и 10 повторов",
        "author": "hz",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG} --dpi-desync=split --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq --dpi-desync-repeats=10 --dpi-desync-cutoff=d2 --dpi-desync-ttl=3 --new"""
    },
    "split_pos_3": {
        "name": "split pos 3 и повторы",
        "description": "split разрез в 3 и 4 повтора",
        "author": "hz",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG} --dpi-desync=split --dpi-desync-split-pos=3 --dpi-desync-repeats=4 --dpi-desync-autottl=1 --new"""
    },
    "general_alt183": {
        "name": "general (alt) 1.8.3",
        "description": "Потом опишу подробнее",
        "author": "Flowseal",
        "label": None,
        "args": f"""{YOUTUBE_BASE_ARG} --dpi-desync=fake,fakedsplit --dpi-desync-autottl=5 --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --new"""
    },
    "youtube_tcp_none": {
        "name": "Не применять для YouTube",
        "description": "Отключить обработку YouTube",
        "author": "System",
        "label": None,
        "args": ""  # Пустая строка = не добавлять аргументы
    }
}
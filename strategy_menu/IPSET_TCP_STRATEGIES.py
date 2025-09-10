from .constants import LABEL_CAUTION, LABEL_GAME, LABEL_RECOMMENDED, LABEL_STABLE 

IPSET_BASE_ARG = "--filter-tcp=80,443,444-65535 --ipset=russia-youtube-rtmps.txt --ipset=ipset-all.txt --ipset=ipset-base.txt --ipset=ipset-all2.txt --ipset=cloudflare-ipset.txt --ipset=ipset-cloudflare1.txt --ipset=ipset-cloudflare.txt --ipset=ipset-discord.txt --ipset-exclude=ipset-dns.txt"

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
        "args": f"""{WARMFRAME_CHAT} {IPSET_BASE_ARG} --dpi-desync=fake,multisplit --dpi-desync-repeats=6 --dpi-desync-fooling=md5sig --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --new"""
    },
    "other_seqovl": {
        "name": "multisplit seqovl 211 & pattern 5",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": LABEL_GAME,
        "args": f"""{WARMFRAME_CHAT} {IPSET_BASE_ARG} --dpi-desync=multisplit --dpi-desync-split-seqovl=211 --dpi-desync-split-seqovl-pattern=tls_clienthello_5.bin --new"""
    },
    "multisplit_286_pattern": {
        "name": "multisplit seqovl 286 с парттерном 11",
        "description": "Дисордер стратегия с фуллингом badseq нарезкой и повтором 11",
        "author": "hz",
        "label": LABEL_GAME,
        "args": f"""{WARMFRAME_CHAT} {IPSET_BASE_ARG} --dpi-desync=multisplit --dpi-desync-split-seqovl=286 --dpi-desync-split-seqovl-pattern=tls_clienthello_11.bin --dup=2 --dup-cutoff=n3 --new"""
    },
    "multisplit_308_pattern": {
        "name": "multisplit seqovl 308 с парттерном 9",
        "description": "Дисордер стратегия с фуллингом badseq нарезкой и повтором 9",
        "author": "hz",
        "label": LABEL_GAME,
        "args": f"""{WARMFRAME_CHAT} {IPSET_BASE_ARG} --dpi-desync=multisplit --dpi-desync-split-seqovl=308 --dpi-desync-split-seqovl-pattern=tls_clienthello_9.bin --dup=2 --dup-cutoff=n3 --new"""
    },
    "original_bolvan_v2_badsum": {
        "name": "Если стратегия не работает смени её!",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""{WARMFRAME_CHAT} {IPSET_BASE_ARG} --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-fake-tls-mod=rnd,dupsid,sni=www.google.com --new"""
    },
    "other_multidisorder": {
        "name": "multidisorder 6 md5sig",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": LABEL_STABLE,
        "args": f"""{WARMFRAME_CHAT} {IPSET_BASE_ARG} --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=6 --dpi-desync-fooling=md5sig --new"""
    },
    "other_multidisorder_2": {
        "name": "multidisorder 6 badseq & md5sig",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": LABEL_STABLE,
        "args": f"""{WARMFRAME_CHAT} {IPSET_BASE_ARG} --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=6 --dpi-desync-fooling=badseq,md5sig --new"""
    },
    "other2": {
        "name": "multidisorder 6 badseq",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": None,
        "args": f"""{WARMFRAME_CHAT} {IPSET_BASE_ARG} --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --new"""
    },
    "multisplit_fake_tls_badseq": {
        "name": "multisplit 14 badseq",
        "description": "Хорошая базовая комлектация для старта",
        "author": "hz",
        "label": None,
        "args": f"""{WARMFRAME_CHAT} {IPSET_BASE_ARG} --dpi-desync=fake,multisplit --dpi-desync-split-pos=sld+1 --dpi-desync-fake-tls=0x0F0F0E0F --dpi-desync-fake-tls=tls_clienthello_14.bin --dpi-desync-fake-tls-mod=rnd,dupsid --dpi-desync-fooling=badseq --dpi-desync-autottl --dup=2 --dup-fooling=badseq --dup-autottl --dup-cutoff=n3 --new"""
    },
    "multisplit_fake_tls_md5sig": {
        "name": "multisplit 14 md5sig",
        "description": "Хорошая базовая комлектация для старта",
        "author": "hz",
        "label": None,
        "args": f"""{WARMFRAME_CHAT} {IPSET_BASE_ARG} --dpi-desync=fake,multisplit --dpi-desync-split-pos=sld+1 --dpi-desync-fake-tls=0x0F0F0E0F --dpi-desync-fake-tls=tls_clienthello_14.bin --dpi-desync-fake-tls-mod=rnd,dupsid --dpi-desync-fooling=md5sig --dpi-desync-autottl --dup=2 --dup-fooling=md5sig --dup-autottl --dup-cutoff=n3 --new"""
    },
    "multisplit_17": {
        "name": "multisplit 17",
        "description": "Мульти нарезка с md5sig и фейком TLS",
        "author": "hz",
        "label": None,
        "args": f"""{WARMFRAME_CHAT} {IPSET_BASE_ARG} --dpi-desync=fake,multisplit --dpi-desync-split-pos=2,midsld --dpi-desync-fake-tls=tls_clienthello_17.bin --dpi-desync-fake-tls-mod=rnd,dupsid --dpi-desync-fooling=md5sig --dpi-desync-autottl --dup=2 --dup-fooling=md5sig --dup-autottl --dup-cutoff=n3 --new"""
    },
    "other4": {
        "name": "fakedsplit badseq 10",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": None,
        "args": f"""{WARMFRAME_CHAT} {IPSET_BASE_ARG} --dpi-desync=fakedsplit --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq --dpi-desync-repeats=10 --dpi-desync-autottl --new"""
    },
    "other5": {
        "name": "multidisorder datanoack deepseek",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": None,
        "args": f"""{WARMFRAME_CHAT} {IPSET_BASE_ARG} --dpi-desync=fake,multidisorder --dpi-desync-fooling=datanoack --dpi-desync-split-pos=midsld --dpi-desync-fake-tls=tls_clienthello_chat_deepseek_com.bin --new"""
    },
    "other6": {
        "name": "general (alt) 1.8.1",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": LABEL_GAME,
        "args": f"""{WARMFRAME_CHAT} {IPSET_BASE_ARG} --dpi-desync=fake,split --dpi-desync-autottl=5 --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --new"""
    },
    "general_alt183": {
        "name": "general (alt) 1.8.3",
        "description": "Потом опишу подробнее",
        "author": "Flowseal",
        "label": LABEL_GAME,
        "args": f"""{WARMFRAME_CHAT} {IPSET_BASE_ARG} --dpi-desync=fake,fakedsplit --dpi-desync-autottl=5 --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --new"""
    },
    "general_alt2183": {
        "name": "general (alt2) 1.8.3",
        "description": "Потом опишу подробнее",
        "author": "Flowseal",
        "label": LABEL_GAME,
        "args": f"""{WARMFRAME_CHAT} {IPSET_BASE_ARG} --dpi-desync=multisplit --dpi-desync-split-seqovl=652 --dpi-desync-split-pos=2 --dpi-desync-split-seqovl-pattern=tls_clienthello_www_google_com.bin --new"""
    },
    "syndata_1": {
        "name": "syndata 4",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""{WARMFRAME_CHAT} {IPSET_BASE_ARG} --dpi-desync=syndata --dpi-desync-fake-syndata=tls_clienthello_4.bin --dpi-desync-autottl --new"""
    },
    "syndata_4_badseq": {
        "name": "syndata 4 badseq",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": None,
        "args": f"""{WARMFRAME_CHAT} {IPSET_BASE_ARG} --dpi-desync=syndata --dpi-desync-fake-syndata=tls_clienthello_4.bin --dpi-desync-fooling=badseq --new"""
    },
    "syndata_7_n3": {
        "name": "syndata 7 n3",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": None,
        "args": f"""{WARMFRAME_CHAT} {IPSET_BASE_ARG} --dpi-desync=syndata --dpi-desync-fake-syndata=tls_clienthello_7.bin --dup=2 --dup-cutoff=n3 --new"""
    },
    "syndata_syn_packet_n3": {
        "name": "syndata syn_packet.bin n3",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": None,
        "args": f"""{WARMFRAME_CHAT} {IPSET_BASE_ARG} --dpi-desync=syndata --dpi-desync-fake-syndata=syn_packet.bin --dup=2 --dup-cutoff=n3 --new"""
    },
    "ipset_tcp_none": {
        "name": "Не применять для остальных",
        "description": "Отключить обработку остальных сайтов",
        "author": "System",
        "label": None,
        "args": ""
    }
}
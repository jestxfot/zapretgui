# strategy_menu/strategy_lists_separated.py

from .constants import LABEL_RECOMMENDED, LABEL_CAUTION, LABEL_EXPERIMENTAL, LABEL_STABLE

# Общие константы для доменов

UDP_YOUTUBE2 = "--filter-udp=443,50000-65535 --hostlist-domains=youtube.com,youtu.be,ytimg.com,googlevideo.com,googleapis.com,gvt1.com,video.google.com --dpi-desync=fake --dpi-desync-repeats=2 --dpi-desync-fake-quic=fake_quic.bin --new"

UDP_YOUTUBE = f"--filter-udp=443 --hostlist=youtube.txt --hostlist=list-general.txt --dpi-desync=fake --dpi-desync-repeats=11 --dpi-desync-fake-quic=quic_initial_www_google_com.bin --new"

"""
--filter-tcp=443 --hostlist-domains=googlevideo.com --dpi-desync=fakedsplit --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq --dpi-desync-repeats=10 --dpi-desync-ttl=4 --new
--filter-tcp=443 --hostlist-domains=googlevideo.com --dpi-desync=split --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq --dpi-desync-repeats=10 --dpi-desync-cutoff=d2 --dpi-desync-ttl=4 --new

--filter-tcp=443 --hostlist-domains=googlevideo.com --dpi-desync=multidisorder --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=1,host+2,sld+2,sld+5,sniext+1,sniext+2,endhost-2 --new
--filter-tcp=443 --ipset-ip=XXX.XXX.XXX.XXX/XX,XXX.XXX.XXX.XXX/XX --hostlist-domains=googlevideo.com --dpi-desync=multidisorder --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=1,host+2,sld+2,sld+5,sniext+1,sniext+2,endhost-2 --new
--filter-tcp=443 --hostlist-domains=googlevideo.com --dpi-desync=multisplit --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=2,midsld-2 --dpi-desync-split-seqovl-pattern=tls_clienthello_7.bin

--filter-tcp=443 --hostlist-domains=googlevideo.com --dpi-desync=fakeddisorder --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=2,midsld-2 --dpi-desync-fakedsplit-pattern=tls_clienthello_7.bin --dpi-desync-fooling=badseq --dpi-desync-autottl
"""

# YouTube стратегии
YOUTUBE_STRATEGIES = {
    "multisplit_seqovl_midsld": {
        "name": "multisplit seqovl midsld",
        "description": "Базовая стратегия multisplit для YouTube",
        "author": None,
        "label": LABEL_RECOMMENDED,
        "args": f"""--filter-tcp=443 --hostlist=youtube.txt --dpi-desync=multisplit --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=midsld-1 --new"""
    },
    "original_bolvan_v2_badsum": {
        "name": "Если стратегия не работает смени её!",
        "description": "Базовая стратегия multidisorder для YouTube",
        "author": "OrigBolvan",
        "label": LABEL_RECOMMENDED,
        "args": f"""--filter-tcp=443 --hostlist=youtube.txt --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-fake-tls-mod=rnd,dupsid,sni=www.google.com --new"""
    },
    "bolvan_md5sig": {
        "name": "BolVan md5sig 11",
        "description": "Другой метод фуллинга + большее число повторений",
        "author": "OrigBolvan",
        "label": None,
        "args": f"""--filter-tcp=443 --hostlist=youtube.txt --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=11 --dpi-desync-fooling=md5sig --new"""
    },
    "bolvan_md5sig_2": {
        "name": "BolVan md5sig 11 + TLS mod Google",
        "description": "Другой метод фуллинга + большее число повторений + tls от гугла",
        "author": "Уфанет",
        "label": None,
        "args": f"""--filter-tcp=443 --hostlist=youtube.txt --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=11 --dpi-desync-fooling=md5sig  --dpi-desync-fake-tls-mod=rnd,dupsid,sni=www.google.com --new"""
    },
    "bolvan_fake_tls": {
        "name": "BolVan fake TLS 4",
        "description": "Используется фейковый Clienthello",
        "author": "OrigBolvan",
        "label": None,
        "args": f"""--filter-tcp=443 --hostlist=youtube.txt --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=4 --dpi-desync-fake-tls=tls_clienthello_18.bin --dpi-desync-fooling=badseq --new"""
    },
    "multisplit_seqovl": {
        "name": "multisplit и seqovl 1",
        "description": "Используется multisplit и seqovl 1",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=443 --hostlist=youtube.txt --dpi-desync=multisplit --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=midsld+1 --new"""
    },
    "fake_multisplit_seqovl_md5sig": {
        "name": "fake multisplit и seqovl 1 md5sig",
        "description": "Используется multisplit и seqovl 1",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=443 --hostlist=youtube.txt --dpi-desync=fake,multisplit --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=midsld-1 --dpi-desync-fooling=md5sig,badseq --dpi-desync-fake-tls=tls_clienthello_4.bin --dpi-desync-ttl=2 --new"""
    },
    "split_pos_md5sig": {
        "name": "Нестандартная нарезка позиций и md5sig",
        "description": "method+2,midsld,5 и ttl 0",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=443 --hostlist=youtube.txt --dpi-desync=fake,multidisorder --dpi-desync-split-pos=method+2,midsld,5 --dpi-desync-ttl=0 --dpi-desync-fooling=md5sig,badsum,badseq --dpi-desync-repeats=15 --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --new"""
    },
    "multisplit_1": {
        "name": "Мультисплит и смещение +1",
        "description": "Базовая стратегия десинхронизации multisplit",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=443 --hostlist=youtube.txt --dpi-desync=multisplit --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=sld+1 --new"""
    },
    "multisplit_2": {
        "name": "Мультисплит и смещение -1",
        "description": "Базовая стратегия десинхронизации multisplit",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=443 --hostlist=youtube.txt --dpi-desync=multisplit --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=sld-1 --new"""
    },
    "multisplit_3": {
        "name": "Мультисплит и смещение midsld +1",
        "description": "Базовая стратегия десинхронизации multisplit и смещение midsld",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=443 --hostlist=youtube.txt --dpi-desync=multisplit --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=midsld+1 --dpi-desync-split-seqovl-pattern=tls_clienthello_7.bin --new"""
    },
    "multidisorder_fake_tls_1": {
        "name": "multidisorder 7 Fake TLS fonts и badseq",
        "description": "Кастомная и сложная стратегия с фейком fonts",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=443 --hostlist=youtube.txt --dpi-desync=fake,multidisorder --dpi-desync-split-pos=7,sld+1 --dpi-desync-fake-tls=0x0F0F0F0F --dpi-desync-fake-tls=tls_clienthello_4.bin --dpi-desync-fake-tls-mod=rnd,dupsid,sni=fonts.google.com --dpi-desync-fooling=badseq --dpi-desync-autottl --new"""
    },
    "multidisorder_fake_tls_2": {
        "name": "multidisorder 7 Fake TLS calendar и badseq",
        "description": "Кастомная и сложная стратегия с фейком calendar",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=443 --hostlist=youtube.txt --dpi-desync=fake,multidisorder --dpi-desync-split-pos=7,sld+1 --dpi-desync-fake-tls=0x0F0F0F0F --dpi-desync-fake-tls=tls_clienthello_4.bin --dpi-desync-fake-tls-mod=rnd,dupsid,sni=calendar.google.com --dpi-desync-fooling=badseq --dpi-desync-autottl --new"""
    },
    "multidisorder_split_repeat": {
        "name": "multidisorder split pos 15",
        "description": "Обратная стратегия с нестандартной нарезкой и фейком clienthello",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=443 --hostlist=youtube.txt --dpi-desync=fake,multidisorder --dpi-desync-split-pos=method+2,midsld,5 --dpi-desync-ttl=0 --dpi-desync-fooling=md5sig,badsum,badseq --dpi-desync-repeats=15 --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --new"""
    },
    "multidisorder_badseq_w3": {
        "name": "multidisorder badseq w3",
        "description": "Обратная стратегия с фуллингом badseq и фейком w3",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=443 --hostlist=youtube.txt --dpi-desync=fake,multidisorder --dpi-desync-fake-tls=dtls_clienthello_w3_org.bin --dpi-desync-split-pos=1,midsld --dpi-desync-fooling=badseq,md5sig --new"""
    },
    "multidisorder_rnd_split": {
        "name": "multidisorder rnd split",
        "description": "Обратная стратегия с нестандартной стратегией и фейком TLS",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=443 --hostlist=youtube.txt --dpi-desync=fake,multidisorder --dpi-desync-fake-tls-mod=rnd,dupsid --dpi-desync-repeats=3 --dpi-desync-split-pos=100,midsld,sniext+1,endhost-2,-10 --dpi-desync-ttl=4 --new"""
    },
    "multisplit_17": {
        "name": "multisplit 17",
        "description": "Мульти нарезка с md5sig и фейком TLS",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=443 --hostlist=youtube.txt --dpi-desync=fake,multisplit --dpi-desync-split-pos=2,midsld --dpi-desync-fake-tls=tls_clienthello_17.bin --dpi-desync-fake-tls-mod=rnd,dupsid --dpi-desync-fooling=md5sig --dpi-desync-autottl --dup=2 --dup-fooling=md5sig --dup-autottl --dup-cutoff=n3 --new"""
    },
    "syndata_md5sig": {
        "name": "multisplit и md5sig",
        "description": "Экспериментальная стратегия multisplit и md5sig",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=443 --hostlist=youtube.txt --ipcache-hostname --dpi-desync=fake,multisplit --dpi-desync-split-pos=sld+1 --dpi-desync-fake-tls=0x0F0F0E0F --dpi-desync-fake-tls=tls_clienthello_9.bin --dpi-desync-fake-tls-mod=rnd,dupsid --dpi-desync-fooling=md5sig --dpi-desync-autottl --dup=2 --dup-fooling=md5sig --dup-autottl --dup-cutoff=n3 --new""" # раньше тут было syndata --dpi-desync-fake-syndata=tls_clienthello_7.bin
    },
    "multisplit_fake_tls_md5sig": {
        "name": "multisplit и md5sig 1",
        "description": "Стандартный multisplit и md5sig и фейк TLS 1",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=443 --hostlist=youtube.txt --dpi-desync=fake,multisplit --dpi-desync-split-pos=sld+1 --dpi-desync-fake-tls=0x0F0F0E0F --dpi-desync-fake-tls=tls_clienthello_1.bin --dpi-desync-fake-tls-mod=rnd,dupsid --dpi-desync-fooling=md5sig --dpi-desync-autottl --dup=2 --dup-fooling=md5sig --dup-autottl --dup-cutoff=n3 --new"""
    },
    "multisplit_fake_tls_md5sig_2": {
        "name": "multisplit и md5sig 14",
        "description": "Стандартный multisplit и md5sig и фейк TLS 14",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=443 --hostlist=youtube.txt --dpi-desync=fake,multisplit --dpi-desync-split-pos=sld+1 --dpi-desync-fake-tls=0x0F0F0E0F --dpi-desync-fake-tls=tls_clienthello_14.bin --dpi-desync-fake-tls-mod=rnd,dupsid --dpi-desync-fooling=md5sig --dpi-desync-autottl --dup=2 --dup-fooling=md5sig --dup-autottl --dup-cutoff=n3 --new"""
    },
    "multisplit_seqovl_pos": {
        "name": "multisplit seqovl с split pos",
        "description": "Базовый multisplit и seqovl с фейками и нарезкой",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=443 --hostlist=youtube.txt --dpi-desync=fake,multisplit --dpi-desync-split-seqovl=2 --dpi-desync-split-pos=3 --dpi-desync-fake-tls=tls_clienthello_2.bin --dpi-desync-ttl=3 --new"""
    },
    "multisplit_seqovl_pos_2": {
        "name": "multisplit seqovl с split pos и badseq",
        "description": "Базовый multisplit и seqovl с фейками, нарезкой и  badseq",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=443 --hostlist=youtube.txt --dpi-desync=fake,multisplit --dpi-desync-fooling=badseq --dpi-desync-split-seqovl=2 --dpi-desync-split-pos=2 --dpi-desync-fake-tls=tls_clienthello_2n.bin --dpi-desync-fake-tls-mod=rnd --dpi-desync-autottl --new"""
    },
    "multidisorder_repeats_md5sig": {
        "name": "multidisorder с повторами и md5ig",
        "description": "multidisorder с fake tls mod",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=443 --hostlist=youtube.txt --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=11 --dpi-desync-fooling=md5sig --dpi-desync-fake-tls-mod=rnd,dupsid,sni=www.google.com --new"""
    },
    "multidisorder_repeats_md5sig_2": {
        "name": "multidisorder с повторами и md5ig",
        "description": "multidisorder с fake tls clienthello",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=443 --hostlist=youtube.txt --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=11 --dpi-desync-fooling=md5sig --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --new"""
    },
    "split2_seqovl_vk": {
        "name": "Устаревший split2 с clienthello от VK",
        "description": "split2 и 625 seqovl с sniext и vk ttl 2 от конторы пидорасов",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=443 --hostlist=youtube.txt --dpi-desync=fake,split2 --dpi-desync-split-seqovl=625 --dpi-desync-split-tls=sniext --dpi-desync-fake-tls=tls_clienthello_vk_com.bin --dpi-desync-ttl=2 --new"""
    },
    "split2_seqovl_google": {
        "name": "Устаревший split2 с clienthello от google",
        "description": "split2 и 1 seqovl с sniext и google ttl 4",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=443 --hostlist=youtube.txt --dpi-desync=fake,split2 --dpi-desync-split-seqovl=1 --dpi-desync-split-tls=sniext --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --dpi-desync-ttl=4 --new"""
    },
    "split2_split": {
        "name": "Устаревший split2 split",
        "description": "Базовый split2 и нарезка",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=443 --hostlist=youtube.txt --dpi-desync=fake,split2 --dpi-desync-split-seqovl=2 --dpi-desync-split-pos=3 --new"""
    },
    "split2_seqovl_652": {
        "name": "split2 seqovl 652",
        "description": "Устаревший split2 с seqovl 652 и паттерном 4",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=443 --hostlist=discord.txt --dpi-desync=fake,split2 --dpi-desync-split-seqovl=652 --dpi-desync-split-pos=3,midsld-1 --dpi-desync-split-seqovl-pattern=tls_clienthello_4.bin --new"""
    },
    "split2_split_google": {
        "name": "Устаревший split2 split seqovl google",
        "description": "Базовый split2 и нарезка с fake tls google",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=443 --hostlist=youtube.txt --dpi-desync=fake,split2 --dpi-desync-split-seqovl=2 --dpi-desync-split-pos=3 --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --dpi-desync-ttl=3 --new"""
    },
    "split2_split_2": {
        "name": "Устаревший split2 split seqovl 2",
        "description": "Базовый split2 и нарезка с fake tls 2",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=443 --hostlist=youtube.txt --dpi-desync=fake,split2 --dpi-desync-split-seqovl=2 --dpi-desync-split-pos=3 --dpi-desync-fake-tls=tls_clienthello_2.bin --dpi-desync-autottl=2 --new"""
    },
    "fake_split2": {
        "name": "Устаревший fake split2 seqovl 1",
        "description": "fake и split2, нарезка с fake tls 2",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=443 --hostlist=youtube.txt --dpi-desync=fake,split2 --dpi-desync-split-seqovl=1 --dpi-desync-split-tls=sniext --dpi-desync-fake-tls=tls_clienthello_3.bin --dpi-desync-ttl=2 --new"""
    },
    "split_seqovl": {
        "name": "Устаревший split и seqovl",
        "description": "Базовый split и seqovl",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=443 --hostlist=youtube.txt --dpi-desync=split --dpi-desync-split-seqovl=1 --dpi-desync-split-tls=sniext --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --dpi-desync-ttl=1 --new"""
    },
    "split_pos_badseq": {
        "name": "Устаревший split и badseq",
        "description": "Базовый split и badseq",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=443 --hostlist=youtube.txt --dpi-desync=split --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq --dpi-desync-repeats=10 --dpi-desync-autottl=2 --new"""
    },
    "split_pos_badseq_10": {
        "name": "split badseq 10 и cutoff",
        "description": "split и badseq разрез и 10 повторов",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=443 --hostlist=youtube.txt --dpi-desync=split --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq --dpi-desync-repeats=10 --dpi-desync-cutoff=d2 --dpi-desync-ttl=3 --new"""
    },
    "split_pos_3": {
        "name": "split pos 3 и повторы",
        "description": "split разрез в 3 и 4 повтора",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=443 --hostlist=youtube.txt --dpi-desync=split --dpi-desync-split-pos=3 --dpi-desync-repeats=4 --dpi-desync-autottl=1 --new"""
    },
    "youtube_none": {
        "name": "Не применять для YouTube",
        "description": "Отключить обработку YouTube",
        "author": "System",
        "label": None,
        "args": ""  # Пустая строка = не добавлять аргументы
    }
}

DISCORD_STRATEGIES = {
    "dis4": {
        "name": "split2 seqovl 652",
        "description": "Устаревший split2 с seqovl 652 и паттерном 4",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""--filter-tcp=443 --hostlist=discord.txt --dpi-desync=split --dpi-desync=split2 --dpi-desync-split-seqovl=652 --dpi-desync-split-pos=2 --dpi-desync-split-seqovl-pattern=tls_clienthello_4.bin --new"""
    },
    "multisplit_fake_tls_badseq": {
        "name": "multisplit fake tls и badseq",
        "description": "Хорошая базовая комлектация для старта",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=443 --hostlist=discord.txt --ipset=ipset-cloudflare.txt --dpi-desync=fake,multisplit --dpi-desync-split-pos=sld+1 --dpi-desync-fake-tls=0x0F0F0E0F --dpi-desync-fake-tls=tls_clienthello_14.bin --dpi-desync-fake-tls-mod=rnd,dupsid --dpi-desync-fooling=badseq --dpi-desync-autottl --dup=2 --dup-fooling=badseq --dup-autottl --dup-cutoff=n3 --new"""
    },
    "multisplit_fake_tls_md5sig": {
        "name": "multisplit fake tls и md5sig",
        "description": "Хорошая базовая комлектация для старта",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=443 --hostlist=discord.txt --ipset=ipset-cloudflare.txt --dpi-desync=fake,multisplit --dpi-desync-split-pos=sld+1 --dpi-desync-fake-tls=0x0F0F0E0F --dpi-desync-fake-tls=tls_clienthello_14.bin --dpi-desync-fake-tls-mod=rnd,dupsid --dpi-desync-fooling=md5sig --dpi-desync-autottl --dup=2 --dup-fooling=md5sig --dup-autottl --dup-cutoff=n3 --new"""
    },
    "multidisorder_md5sig_pos": {
        "name": "multidisorder md5sig и сплит",
        "description": "Дисордер стратегия с фуллингом md5sig нарезкой и повтором 6",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=443 --hostlist=discord.txt --ipset=ipset-cloudflare.txt --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=6 --dpi-desync-fooling=badseq,md5sig --new"""
    },
    "multidisorder_ipset_syndata": {
        "name": "Адреса discord с фуллингом syndata",
        "description": "Использует адреса дискорда, вместо доменов",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""--filter-tcp=443 --ipset=ipset-discord.txt --dpi-desync=syndata --dpi-desync-fake-syndata=tls_clienthello_3.bin --dpi-desync-autottl --new"""
    },
    "multidisorder_badseq_pos": {
        "name": "multidisorder badseq и сплит",
        "description": "Дисордер стратегия с фуллингом badseq нарезкой и повтором 6",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=443 --hostlist=discord.txt --ipset=ipset-cloudflare.txt --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --new"""
    },
    "multisplit_286_pattern": {
        "name": "multisplit seqovl 286 с парттерном 11",
        "description": "Дисордер стратегия с фуллингом badseq нарезкой и повтором 11",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=443 --hostlist=discord.txt --ipset=ipset-cloudflare.txt --dpi-desync=multisplit --dpi-desync-split-seqovl=286 --dpi-desync-split-seqovl-pattern=tls_clienthello_11.bin --dup=2 --dup-cutoff=n3 --new"""
    },
    "multidisorder_super_split_md5sig": {
        "name": "multidisorder super split md5sig",
        "description": "Обратная стратегия с нестандартной нарезкой и md5sig",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=443 --hostlist=discord.txt --ipset=ipset-cloudflare.txt --dpi-desync=fake,multidisorder --dpi-desync-split-pos=method+2,midsld,5 --dpi-desync-ttl=0 --dpi-desync-fooling=md5sig,badsum,badseq --dpi-desync-repeats=15 --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --new"""
    },
    "multidisorder_super_split_badseq": {
        "name": "multidisorder super split ",
        "description": "Обратная стратегия с нестандартной нарезкой и badseq",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=443 --hostlist=discord.txt --ipset=ipset-cloudflare.txt --dpi-desync=fake,multidisorder --dpi-desync-split-pos=method+2,midsld,5 --dpi-desync-ttl=0 --dpi-desync-fooling=badsum,badseq --dpi-desync-repeats=15 --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --new"""
    },
    "multidisorder_w3": {
        "name": "multidisorder с фейком w3 ",
        "description": "Обратная стратегия с фейком tls w3 и md5sig",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=443 --hostlist=discord.txt --ipset=ipset-cloudflare.txt --dpi-desync=fake,multidisorder --dpi-desync-fake-tls=dtls_clienthello_w3_org.bin --dpi-desync-split-pos=1,midsld --dpi-desync-fooling=badseq,md5sig --new"""
    },
    "multidisorder_pos_100": {
        "name": "multidisorder с разрезом 100",
        "description": "Обратная стратегия с нестандартной нарезкой и фейком TLS",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=443 --hostlist=discord.txt --ipset=ipset-cloudflare.txt --dpi-desync=fake,multidisorder --dpi-desync-fake-tls-mod=rnd,dupsid --dpi-desync-repeats=3 --dpi-desync-split-pos=100,midsld,sniext+1,endhost-2,-10 --dpi-desync-ttl=4 --new"""
    },
    "fake_badseq_rnd": {
        "name": "Фейк с фуулингом badseq и фейком tls rnd",
        "description": "Базовая стратегия десинхронизации с фейком tls rnd",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=443 --hostlist=discord.txt --ipset=ipset-cloudflare.txt --dpi-desync=fake --dpi-desync-fooling=badseq --dpi-desync-fake-tls=tls_clienthello_7.bin --dpi-desync-fake-tls-mod=rnd --new"""
    },
    "fakedsplit_badseq_4": {
        "name": "Фейк с фуулингом badseq и фейком tls 4",
        "description": "Десинхронизация badseq с фейком tls 4",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=443 --hostlist=discord.txt --ipset=ipset-cloudflare.txt --dpi-desync=fakedsplit --dpi-desync-split-pos=midsld-1,1 --dpi-desync-fooling=badseq --dpi-desync-fakedsplit-pattern=tls_clienthello_4.bin --dpi-desync-autottl --new"""
    },
    "fake_md5sig_fake_tls": {
        "name": "Фейк с фуулингом md5sig и фейком tls",
        "description": "Базовая десинхронизация md5sig с фейком tls",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=443 --hostlist=discord.txt --ipset=ipset-cloudflare.txt --dpi-desync=fake --dpi-desync-fooling=md5sig --dpi-desync-fake-tls-mod=rnd,rndsni,padencap --new"""
    },
    "fake_autottl_faketls": {
        "name": "Фейк с авто ttl и фейком tls",
        "description": "Фейк с авто ttl и фейком tls (использовать с осторожностью)",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=443 --hostlist=discord.txt --ipset=ipset-cloudflare.txt --dpi-desync=fake --dpi-desync-ttl=1 --dpi-desync-autottl=4 --dpi-desync-fake-tls-mod=rnd,rndsni,padencap --new"""
    },
    "fake_datanoack_fake_tls": {
        "name": "Фейк с datanoack и фейком tls",
        "description": "Фейк с datanoack и фейком tls",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=443 --hostlist=discord.txt --ipset=ipset-cloudflare.txt --dpi-desync=fake --dpi-desync-fooling=datanoack --dpi-desync-fake-tls-mod=rnd,rndsni,padencap --new"""
    },
    "dis1": {
        "name": "Фейк с datanoack и padencap",
        "description": "Улучшенная стратегия с datanoack и padencap",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=443 --hostlist=discord.txt --ipset=ipset-cloudflare.txt --dpi-desync=fake,fakeddisorder --dpi-desync-fooling=datanoack --dpi-desync-split-pos=midsld --dpi-desync-fake-tls-mod=rnd,rndsni,padencap --new"""
    },
    "dis2": {
        "name": "multisplit split pos padencap",
        "description": "Стандартный мультисплит с нарезкой и фейком padencap",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=443 --hostlist=discord.txt --ipset=ipset-cloudflare.txt --dpi-desync=fake,multisplit --dpi-desync-ttl=1 --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls-mod=rnd,rndsni,padencap --new"""
    },
    "dis3": {
        "name": "split badseq 10",
        "description": "Стандартный сплит с фуллингом badseq и 10 повторами",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=443 --hostlist=discord.txt --dpi-desync=split --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq --dpi-desync-repeats=10 --dpi-desync-ttl=4 --new"""
    },
    "dis5": {
        "name": "fake split 6 google",
        "description": "Фейковый сплит с повторением 6 и фейком google",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=443 --hostlist=discord.txt --ipset=ipset-cloudflare.txt --dpi-desync=fake,split --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --new"""
    },
    "dis5": {
        "name": "fake split2 6 sberbank",
        "description": "Фейковый сплит2 с повторением 6 и фейком от сбербанка много деняк",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=443 --hostlist=discord.txt --ipset=ipset-cloudflare.txt --dpi-desync=fake,split2 --dpi-desync-ttl=1 --dpi-desync-autottl=5 --dpi-desync-repeats=6 --dpi-desync-fake-tls=tls_clienthello_sberbank_ru.bin --new"""
    },
    "dis6": {
        "name": "syndata (на все домены!)",
        "description": "Стратегия работает на все домены и может ломать сайты (на свой страх и риск)",
        "author": "hz",
        "label": LABEL_CAUTION,
        "args": f"""--filter-tcp=443 --hostlist=discord.txt --ipset=ipset-cloudflare.txt --dpi-desync=syndata --dpi-desync-fake-syndata=tls_clienthello_3.bin --dpi-desync-ttl=5 --new"""
    },
    "dis7": {
        "name": "split 6 badseq",
        "description": "Сплит с повторением 6 и фуллингом badseq и фейком tls от Google",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=443 --hostlist=discord.txt --ipset=ipset-cloudflare.txt --dpi-desync=fake,split --dpi-desync-autottl=2 --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --new"""
    },
    "dis8": {
        "name": "split2 sniext 4",
        "description": "Cплит2 с фейком tls 4 и ttl 4 (короче одни четвёрки)",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=443 --hostlist=discord.txt --ipset=ipset-cloudflare.txt --dpi-desync=fake,split2 --dpi-desync-split-seqovl=1 --dpi-desync-split-tls=sniext --dpi-desync-fake-tls=tls_clienthello_4.bin --dpi-desync-ttl=4 --new"""
    },
    "dis9": {
        "name": "split2 sniext google",
        "description": "Cплит2 с фейком tls от Google",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=443 --hostlist=discord.txt --ipset=ipset-cloudflare.txt --dpi-desync=fake,split2 --dpi-desync-split-seqovl=1 --dpi-desync-split-tls=sniext --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --dpi-desync-ttl=2 --new"""
    },
    "dis10": {
        "name": "disorder2 badseq tls google",
        "description": "Cплит2 badseq с фейком tls от Google",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=443 --hostlist=discord.txt --ipset=ipset-cloudflare.txt --dpi-desync=syndata,disorder2 --dpi-desync-split-pos=3 --dpi-desync-repeats=11 --dpi-desync-fooling=badseq --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --new"""
    },
    "dis11": {
        "name": "split badseq 10",
        "description": "Cплит2 с фуллингом badseq и 10 повторами",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=443 --hostlist=discord.txt --ipset=ipset-cloudflare.txt --dpi-desync=split --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq --dpi-desync-repeats=10 --dpi-desync-autottl --new"""
    },
    "dis12": {
        "name": "split badseq 10 ttl",
        "description": "Cплит2 с фуллингом badseq и 10 повторами и ttl 3",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=443 --hostlist=discord.txt --ipset=ipset-cloudflare.txt --dpi-desync=split --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq --dpi-desync-repeats=10 --dpi-desync-ttl=3 --new"""
    },
    "dis13": {
        "name": "fakedsplit badsrq 10",
        "description": "Фейки и сплиты с фуллингом badseq и 10 повторами",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=443 --hostlist=discord.txt --ipset=ipset-cloudflare.txt --dpi-desync=fakedsplit --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq --dpi-desync-repeats=10 --dpi-desync-autottl --new"""
    },
    "dis14": {
        "name": "multisplit и seqovl",
        "description": "Мульти нарезка с seqovl и нестандартной позицией",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=443 --hostlist=discord.txt --ipset=ipset-cloudflare.txt --dpi-desync=multisplit --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=midsld+1 --new"""
    },
    "discord_none": {
        "name": "Не применять для Discord",
        "description": "Отключить обработку Discord",
        "author": "System",
        "label": None,
        "args": ""
    }
}

DISCORD_VOICE_STRATEGIES = {
    "ipv4_dup2_autottl_cutoff_n3": {
        "name": "IPv4 & IPv6 DUP, AutoTTL, Cutoff n3",
        "description": "Стратегия для IPv4 с дублированием пакетов, автоматическим TTL и обрезкой n3.",
        "author": "Community",
        "label": LABEL_RECOMMENDED,
        "args": f"""--filter-l3=ipv4 --filter-l7=discord,stun --dpi-desync=fake --dpi-desync-autottl --dup=2 --dup-autottl --dup-cutoff=n3 --new --filter-l3=ipv6 --filter-l7=discord,stun --dpi-desync=fake --dpi-desync-autottl6 --dup=2 --dup-autottl6 --dup-cutoff=n3 --new"""
    },
    "fake_l7": {
        "name": "Fake L7",
        "description": "Базовая стратегия с DPI Desync 'fake' и фильтрацией L7 для Discord и STUN.",
        "author": "Community",
        "label": LABEL_STABLE,
        "args": f"""--filter-l7=discord,stun --dpi-desync=fake --new"""
    },
    "fake_tamper_repeats_6": {
        "name": "Fake, Tamper, Repeats 6",
        "description": "Стратегия с подменой и изменением пакетов, 6 повторений.",
        "author": "Community",
        "label": None,
        "args": f"""--filter-l7=discord,stun --dpi-desync=fake,tamper --dpi-desync-repeats=6 --dpi-desync-fake-discord=0x00 --new"""
    },
    "fake_any_proto_repeats_6_cutoff_n4": {
        "name": "Fake, Any Proto, Repeats 6, Cutoff n4",
        "description": "Стратегия с Fake Desync для любого протокола, 6 повторениями и обрезкой n4.",
        "author": "Community",
        "label": None,
        "args": f"""--filter-l7=discord,stun --dpi-desync=fake --dpi-desync-repeats=6 --dpi-desync-any-protocol --dpi-desync-cutoff=n4 --new"""
    },
    "fake_tamper_any_proto_repeats_11_cutoff_d5": {
        "name": "Fake, Tamper, Repeats 11, Cutoff d5",
        "description": "Комбинированная стратегия с 11 повторениями и обрезкой d5 для любого протокола.",
        "author": "Community",
        "label": None,
        "args": f"""--filter-l7=discord,stun --dpi-desync=fake,tamper --dpi-desync-any-protocol --dpi-desync-cutoff=d5 --dpi-desync-repeats=11 --new"""
    },
    "fake_any_proto_quic1_cutoff_d2": {
        "name": "Fake, Any Proto, QUIC 1, Cutoff d2",
        "description": "Использование поддельного QUIC-пакета (quic_1.bin) с обрезкой d2.",
        "author": "Community",
        "label": None,
        "args": f"""--filter-l7=discord,stun --dpi-desync=fake --dpi-desync-any-protocol --dpi-desync-cutoff=d2 --dpi-desync-fake-quic=quic_1.bin --new"""
    },
    "fake_repeats_6": {
        "name": "Fake Repeats 6",
        "description": "Простая стратегия с 6 повторениями фейкового пакета.",
        "author": "Community",
        "label": None,
        "args": f"""--filter-l7=discord,stun --dpi-desync=fake --dpi-desync-repeats=6 --new"""
    },
    "ipset_fake_any_proto_cutoff_d3_repeats_6": {
        "name": "IPSet Fake, Any Proto, Cutoff d3, Repeats 6",
        "description": "Стратегия, использующая IPSet, с 6 повторениями и обрезкой d3.",
        "author": "Community",
        "label": LABEL_RECOMMENDED,
        "args": f"""--ipset=ipset-discord.txt --dpi-desync=fake --dpi-desync-any-protocol --dpi-desync-cutoff=d3 --dpi-desync-repeats=6 --new"""
    },
    "ipset_fake_any_proto_cutoff_d3_repeats_8": {
        "name": "IPSet Fake, Any Proto, Cutoff d3, Repeats 8",
        "description": "Стратегия, использующая IPSet, с 8 повторениями и обрезкой d3.",
        "author": "Community",
        "label": LABEL_RECOMMENDED,
        "args": f"""--ipset=ipset-discord.txt --dpi-desync=fake --dpi-desync-any-protocol --dpi-desync-cutoff=d3 --dpi-desync-repeats=8 --new"""
    },
    "ipset_fake_any_proto_cutoff_d4_repeats_8": {
        "name": "IPSet Fake, Any Proto, Cutoff d4, Repeats 8",
        "description": "Стратегия, использующая IPSet, с 8 повторениями и обрезкой d4.",
        "author": "Community",
        "label": LABEL_RECOMMENDED,
        "args": f"""--ipset=ipset-discord.txt --dpi-desync=fake --dpi-desync-any-protocol --dpi-desync-cutoff=d4 --dpi-desync-repeats=8 --new"""
    },
    "fake_any_proto_cutoff_n3": {
        "name": "Fake, Any Proto, Cutoff n3",
        "description": "Минималистичная стратегия с обрезкой n3 для любого протокола.",
        "author": "Community",
        "label": None,
        "args": f"""--ipset=ipset-discord.txt --dpi-desync=fake --dpi-desync-any-protocol --dpi-desync-cutoff=n3 --new"""
    },
    "fake_split2_quic_test_cutoff_d2": {
        "name": "Fake, Split2, QUIC Test, Cutoff d2",
        "description": "Разделение пакета в сочетании с поддельным тестовым QUIC-пакетом.",
        "author": "Community",
        "label": None,
        "args": f"""--ipset=ipset-discord.txt --dpi-desync=fake,split2 --dpi-desync-any-protocol --dpi-desync-cutoff=d2 --dpi-desync-fake-quic=quic_test_00.bin --new"""
    },
    "fake_any_proto_google_quic_cutoff_n2": {
        "name": "Fake, Any Proto, Google QUIC, Cutoff n2",
        "description": "Поддельный QUIC-пакет от Google с обрезкой n2.",
        "author": "Community",
        "label": LABEL_RECOMMENDED,
        "args": f"""--ipset=ipset-discord.txt --dpi-desync=fake --dpi-desync-any-protocol --dpi-desync-cutoff=n2 --dpi-desync-fake-quic=quic_initial_www_google_com.bin --new"""
    },
    "fake_any_proto_google_quic_cutoff_d3_repeats_6": {
        "name": "Fake, Any Proto, Google QUIC, Cutoff d3, Repeats 6",
        "description": "Поддельный QUIC от Google с 6 повторениями и обрезкой d3.",
        "author": "Community",
        "label": None,
        "args": f"""--ipset=ipset-discord.txt --dpi-desync=fake --dpi-desync-any-protocol --dpi-desync-cutoff=d3 --dpi-desync-repeats=6 --dpi-desync-fake-quic=quic_initial_www_google_com.bin --new"""
    },
    "fake_tamper_any_proto_google_quic_cutoff_d3_repeats_6": {
        "name": "Fake, Tamper, Google QUIC, Cutoff d3, Repeats 6",
        "description": "Комбинация Fake и Tamper с QUIC от Google, 6 повторениями и обрезкой d3.",
        "author": "Community",
        "label": None,
        "args": f"""--ipset=ipset-discord.txt --dpi-desync=fake,tamper --dpi-desync-any-protocol --dpi-desync-cutoff=d3 --dpi-desync-repeats=6 --dpi-desync-fake-quic=quic_initial_www_google_com.bin --new"""
    },
    "fake_tamper_any_proto_google_quic_cutoff_n5_repeats_10": {
        "name": "Fake, Tamper, Google QUIC, Cutoff n5, Repeats 10",
        "description": "Агрессивная стратегия с 10 повторениями и обрезкой n5.",
        "author": "Community",
        "label": None,
        "args": f"""--ipset=ipset-discord.txt --dpi-desync=fake,tamper --dpi-desync-any-protocol --dpi-desync-cutoff=n5 --dpi-desync-repeats=10 --dpi-desync-fake-quic=quic_initial_www_google_com.bin --new"""
    },
    "fake_tamper_any_proto_google_quic_cutoff_n4": {
        "name": "Fake, Tamper, Google QUIC, Cutoff n4",
        "description": "Комбинация Fake и Tamper с QUIC от Google и обрезкой n4.",
        "author": "Community",
        "label": None,
        "args": f"""--ipset=ipset-discord.txt --dpi-desync=fake,tamper --dpi-desync-any-protocol --dpi-desync-cutoff=n4 --dpi-desync-fake-quic=quic_initial_www_google_com.bin"""
    },
    "discord_voice_none": {
        "name": "Не применять для Discord Voice",
        "description": "Отключить обработку голосовых чатов Discord.",
        "author": "System",
        "label": None,
        "args": ""
    }
}

DISCORD_UPD_STRATEGIES = {
    "fake_6_google": {
        "name": "fake 6 google",
        "description": "Стандартная стратегия для Discord Voice",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""--filter-udp=443 --hostlist=discord.txt --ipset=ipset-cloudflare.txt --dpi-desync=fake --dpi-desync-repeats=6 --dpi-desync-fake-quic=quic_initial_www_google_com.bin --new"""
    },
    "fake_6_1": {
        "name": "fake 6 quic 1",
        "description": "Стандартная стратегия для Discord Voice с другим Fake QUIC",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""--filter-udp=443 --hostlist=discord.txt --ipset=ipset-cloudflare.txt --dpi-desync=fake --dpi-desync-repeats=6 --dpi-desync-fake-quic=quic_1.bin --new"""
    },
    "fake_6_vk_com": {
        "name": "fake 6 quic vk.com",
        "description": "Стандартная стратегия для Discord Voice с другим QUIC от VK",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""--filter-udp=443 --hostlist=discord.txt --ipset=ipset-cloudflare.txt --dpi-desync=fake --dpi-desync-repeats=6 --dpi-desync-fake-quic=quic_initial_vk_com.bin --new"""
    },
    "fake_8_google": {
        "name": "fake 8 google",
        "description": "Стандартная стратегия для Discord Voice",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""--filter-udp=443 --hostlist=discord.txt --ipset=ipset-cloudflare.txt --dpi-desync=fake --dpi-desync-repeats=8 --dpi-desync-fake-quic=quic_initial_www_google_com.bin --new"""
    },
    "fake_10_pattern": {
        "name": "fake 10 pattern",
        "description": "Стандартная стратегия для Discord Voice с доп. улучшениями",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""--filter-udp=443 --hostlist=discord.txt --ipset=ipset-cloudflare.txt --dpi-desync=fake --dpi-desync-udplen-increment=10 --dpi-desync-repeats=6 --dpi-desync-udplen-pattern=0xDEADBEEF --dpi-desync-fake-quic=quic_initial_www_google_com.bin --new"""
    },
    "fake_udplen": {
        "name": "fake udplen 7",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""--filter-udp=443 --hostlist=discord.txt --ipset=ipset-cloudflare.txt --dpi-desync=fake,udplen --dpi-desync-udplen-increment=5 --dpi-desync-udplen-pattern=0xDEADBEEF --dpi-desync-fake-quic=quic_2.bin --dpi-desync-repeats=7 --dpi-desync-cutoff=n2 --new"""
    },
    "fake_updlen_7_quic_cutoff": {
        "name": "fake udplen 7 quic cutoff",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""--filter-udp=443 --hostlist=discord.txt --ipset=ipset-cloudflare.txt --dpi-desync=fake --dpi-desync-udplen-increment=10 --dpi-desync-repeats=7 --dpi-desync-udplen-pattern=0xDEADBEEF --dpi-desync-fake-quic=quic_test_00.bin --dpi-desync-cutoff=n2 --new"""
    },
    "fake_updlen_7_quic_google": {
        "name": "fake udplen 7 quic google",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""--filter-udp=443 --hostlist=discord.txt --ipset=ipset-cloudflare.txt --dpi-desync=fake --dpi-desync-udplen-increment=10 --dpi-desync-repeats=7 --dpi-desync-udplen-pattern=0xDEADBEEF --dpi-desync-fake-quic=quic_initial_www_google_com.bin --new"""
    },
    "fake_updlen_10_pattern": {
        "name": "fake udplen 10 pattern",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""--filter-udp=443 --hostlist=discord.txt --ipset=ipset-cloudflare.txt --dpi-desync=fake --dpi-desync-udplen-increment=10 --dpi-desync-udplen-pattern=0xDEADBEEF --dpi-desync-fake-quic=quic_2.bin --dpi-desync-repeats=8 --dpi-desync-cutoff=n2 --new"""
    },
    "fake_split2_repeats_6": {
        "name": "fake split2 repeats 6",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""--filter-udp=443 --hostlist=discord.txt --ipset=ipset-cloudflare.txt --dpi-desync=fake,split2 --dpi-desync-udplen-increment=10 --dpi-desync-repeats=6 --dpi-desync-udplen-pattern=0xDEADBEEF --dpi-desync-fake-quic=quic_initial_www_google_com.bin --new"""
    },
    "fake_split2_repeats_11": {
        "name": "fake split2 repeats 11",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""--filter-udp=443 --hostlist=discord.txt --ipset=ipset-cloudflare.txt --dpi-desync=fake,split2 --dpi-desync-repeats=11 --dpi-desync-udplen-increment=15 --dpi-desync-fake-quic=quic_initial_www_google_com.bin --new"""
    },
    "discord_voice_none": {
        "name": "Не применять для Discord",
        "description": "Отключить обработку Discord",
        "author": "System",
        "label": None,
        "args": ""
    }
}


# Стратегии для остальных сайтов
OTHER_STRATEGIES = {
    "other_seqovl": {
        "name": "multisplit seqovl 211 & pattern 5",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""--filter-tcp=80,443 --hostlist=other.txt --hostlist=other2.txt --hostlist=russia-blacklist.txt --dpi-desync=multisplit --dpi-desync-split-seqovl=211 --dpi-desync-split-seqovl-pattern=tls_clienthello_5.bin --new"""
    },
    "multisplit_286_pattern": {
        "name": "multisplit seqovl 286 с парттерном 11",
        "description": "Дисордер стратегия с фуллингом badseq нарезкой и повтором 11",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=80,443 --hostlist=other.txt --hostlist=other2.txt --hostlist=russia-blacklist.txt --dpi-desync=multisplit --dpi-desync-split-seqovl=286 --dpi-desync-split-seqovl-pattern=tls_clienthello_11.bin --dup=2 --dup-cutoff=n3 --new"""
    },
    "multisplit_308_pattern": {
        "name": "multisplit seqovl 308 с парттерном 9",
        "description": "Дисордер стратегия с фуллингом badseq нарезкой и повтором 9",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=80,443 --hostlist=other.txt --hostlist=other2.txt --hostlist=russia-blacklist.txt --dpi-desync=multisplit --dpi-desync-split-seqovl=308 --dpi-desync-split-seqovl-pattern=tls_clienthello_9.bin --dup=2 --dup-cutoff=n3 --new"""
    },
    "original_bolvan_v2_badsum": {
        "name": "Если стратегия не работает смени её!",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""--filter-tcp=80,443 --hostlist=other.txt --hostlist=other2.txt --hostlist=russia-blacklist.txt --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-fake-tls-mod=rnd,dupsid,sni=www.google.com --new"""
    },
    "other_multidisorder": {
        "name": "multidisorder 6 md5sig",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": LABEL_STABLE,
        "args": f"""--filter-tcp=80,443 --hostlist=other.txt --hostlist=other2.txt --hostlist=russia-blacklist.txt --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=6 --dpi-desync-fooling=md5sig --new"""
    },
    "other_multidisorder_2": {
        "name": "multidisorder 6 badseq & md5sig",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": LABEL_STABLE,
        "args": f"""--filter-tcp=80,443 --hostlist=other.txt --hostlist=other2.txt --hostlist=russia-blacklist.txt --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=6 --dpi-desync-fooling=badseq,md5sig --new"""
    },
    "other2": {
        "name": "multidisorder 6 badseq",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=80,443 --hostlist=other.txt --hostlist=other2.txt --hostlist=russia-blacklist.txt --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --new"""
    },
    "multisplit_fake_tls_badseq": {
        "name": "multisplit 14 badseq",
        "description": "Хорошая базовая комлектация для старта",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=80,443 --hostlist=other.txt --hostlist=other2.txt --hostlist=russia-blacklist.txt --dpi-desync=fake,multisplit --dpi-desync-split-pos=sld+1 --dpi-desync-fake-tls=0x0F0F0E0F --dpi-desync-fake-tls=tls_clienthello_14.bin --dpi-desync-fake-tls-mod=rnd,dupsid --dpi-desync-fooling=badseq --dpi-desync-autottl --dup=2 --dup-fooling=badseq --dup-autottl --dup-cutoff=n3 --new"""
    },
    "multisplit_fake_tls_md5sig": {
        "name": "multisplit 14 md5sig",
        "description": "Хорошая базовая комлектация для старта",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=80,443 --hostlist=other.txt --hostlist=other2.txt --hostlist=russia-blacklist.txt --dpi-desync=fake,multisplit --dpi-desync-split-pos=sld+1 --dpi-desync-fake-tls=0x0F0F0E0F --dpi-desync-fake-tls=tls_clienthello_14.bin --dpi-desync-fake-tls-mod=rnd,dupsid --dpi-desync-fooling=md5sig --dpi-desync-autottl --dup=2 --dup-fooling=md5sig --dup-autottl --dup-cutoff=n3 --new"""
    },
    "multisplit_17": {
        "name": "multisplit 17",
        "description": "Мульти нарезка с md5sig и фейком TLS",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=443 --hostlist=other.txt --hostlist=other2.txt --hostlist=russia-blacklist.txt --dpi-desync=fake,multisplit --dpi-desync-split-pos=2,midsld --dpi-desync-fake-tls=tls_clienthello_17.bin --dpi-desync-fake-tls-mod=rnd,dupsid --dpi-desync-fooling=md5sig --dpi-desync-autottl --dup=2 --dup-fooling=md5sig --dup-autottl --dup-cutoff=n3 --new"""
    },
    "other4": {
        "name": "fakedsplit badseq 10",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=80,443 --hostlist=other.txt --hostlist=other2.txt --hostlist=russia-blacklist.txt --dpi-desync=fakedsplit --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq --dpi-desync-repeats=10 --dpi-desync-autottl --new"""
    },
    "other5": {
        "name": "multidisorder datanoack deepseek",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=80,443 --hostlist=other.txt --hostlist=other2.txt --hostlist=russia-blacklist.txt --dpi-desync=fake,multidisorder --dpi-desync-fooling=datanoack --dpi-desync-split-pos=midsld --dpi-desync-fake-tls=tls_clienthello_chat_deepseek_com.bin --new"""
    },
    "other6": {
        "name": "fake split 6",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": None,
        "args": f"""--filter-tcp=80,443 --hostlist=other.txt --hostlist=other2.txt --hostlist=russia-blacklist.txt --dpi-desync=fake,split --dpi-desync-autottl=5 --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --new"""
    },
    "other_none": {
        "name": "Не применять для остальных",
        "description": "Отключить обработку остальных сайтов",
        "author": "System",
        "label": None,
        "args": ""
    }
}

# Базовые аргументы (применяются всегда)
BASE_ARGS = "--wf-raw=@windivert.all.txt"

def combine_strategies(youtube_id: str, discord_id: str, discord_voice_id: str, other_id: str) -> dict:
    """
    Объединяет выбранные стратегии в одну общую
    
    Args:
        youtube_id: ID стратегии для YouTube
        discord_id: ID стратегии для Discord
        discord_voice_id: ID стратегии для Discord Voice
        other_id: ID стратегии для остальных сайтов
        
    Returns:
        Словарь с объединенной стратегией
    """
    # Собираем аргументы
    args_parts = [BASE_ARGS]

    # Добавляем стратегию для остальных сайтов
    if other_id and other_id in OTHER_STRATEGIES:
        other_args = OTHER_STRATEGIES[other_id]["args"]
        if other_args:
            args_parts.append(other_args)

    # Добавляем YouTube стратегию
    if youtube_id and youtube_id in YOUTUBE_STRATEGIES:
        youtube_args = YOUTUBE_STRATEGIES[youtube_id]["args"]
        if youtube_args:
            args_parts.append(youtube_args)
    
    # Добавляем Discord стратегию
    if discord_id and discord_id in DISCORD_STRATEGIES:
        discord_args = DISCORD_STRATEGIES[discord_id]["args"]
        if discord_args:
            args_parts.append(discord_args)
    
    # Добавляем Discord Voice стратегию
    if discord_voice_id and discord_voice_id in DISCORD_VOICE_STRATEGIES:
        discord_voice_args = DISCORD_VOICE_STRATEGIES[discord_voice_id]["args"]
        if discord_voice_args:
            args_parts.append(discord_voice_args)
    
    # Объединяем все части через пробел
    combined_args = " ".join(args_parts)
    
    # Формируем описание
    descriptions = []
    if youtube_id and youtube_id != "youtube_none":
        descriptions.append(f"YouTube: {YOUTUBE_STRATEGIES[youtube_id]['name']}")
    if discord_id and discord_id != "discord_none":
        descriptions.append(f"Discord: {DISCORD_STRATEGIES[discord_id]['name']}")
    if discord_voice_id and discord_voice_id != "discord_voice_none":
        descriptions.append(f"Discord Voice: {DISCORD_VOICE_STRATEGIES[discord_voice_id]['name']}")
    if other_id and other_id != "other_none":
        descriptions.append(f"Остальные: {OTHER_STRATEGIES[other_id]['name']}")
    
    combined_description = " | ".join(descriptions) if descriptions else "Пользовательская комбинация"
    
    return {
        "name": "Комбинированная стратегия",
        "description": combined_description,
        "version": "1.0",
        "provider": "universal",
        "author": "Combined",
        "updated": "2024",
        "label": LABEL_STABLE,
        "all_sites": True,
        "args": combined_args,
        "_is_builtin": True,
        "_youtube_id": youtube_id,
        "_discord_id": discord_id,
        "_discord_voice_id": discord_voice_id,
        "_other_id": other_id
    }

def get_default_selections():
    """Возвращает выборы по умолчанию"""
    return {
        'youtube': 'multisplit_seqovl_midsld',
        'discord': 'dis4',
        'discord_voice': 'ipv4_dup2_autottl_cutoff_n3',
        'other': 'other_seqovl'
    }
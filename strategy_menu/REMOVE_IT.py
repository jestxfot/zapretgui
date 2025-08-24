"""
Censorliber, [08.08.2025 1:02]
ну окей начнем с дискодра и ютуба

Censorliber, [08.08.2025 1:02]
а там добавим возможность отключения для обхода части сайтов

Censorliber, [08.08.2025 1:02]
хз как

Censorliber, [08.08.2025 1:02]
чет тту без идей

Censorliber, [08.08.2025 1:02]
или делать нулевую стратегию в качестве затычки в коде чтобы проще было или... прям кнопку добавлять
"""

from .constants import LABEL_CAUTION, LABEL_EXPERIMENTAL, LABEL_RECOMMENDED, LABEL_STABLE, LABEL_WARP

"""
------ остальные 80 --------------------
--filter-tcp=80 --dpi-desync=fake,multisplit --dpi-desync-split-seqovl=2 --dpi-desync-split-pos=sld+1 --dpi-desync-fake-http=0x0F0F0F0F --dpi-desync-fooling=md5sig --dup=2 --dup-fooling=md5sig --dup-cutoff=n3 --new
--filter-tcp=80 --dpi-desync=fake,fakedsplit --dpi-desync-autottl=2 --dpi-desync-fooling=md5sig --new
--filter-tcp=80 --dpi-desync=fake,fakedsplit --dpi-desync-autottl=2 --dpi-desync-fooling=badseq --new
--filter-tcp=80 --dpi-desync=fake,split2 --dpi-desync-autottl=2 --dpi-desync-fooling=md5sig --new

------ добавить параметр который удаляет ipset-all чтобы спамить по всем айпишникам, по умолчанию выключено во вкладке Игры UDP --------------------
--filter-udp=1024-65535 --ipset=ipset-all.txt --dpi-desync=fake --dpi-desync-autottl=2 --dpi-desync-repeats=12 --dpi-desync-any-protocol=1 --dpi-desync-fake-unknown-udp=quic_initial_www_google_com.bin --dpi-desync-cutoff=n2
--filter-udp=1024-65535 --ipset=ipset-all.txt --dpi-desync=fake --dpi-desync-autottl=2 --dpi-desync-repeats=12 --dpi-desync-any-protocol=1 --dpi-desync-fake-unknown-udp=quic_initial_www_google_com.bin --dpi-desync-cutoff=n3

--filter-udp=1024-65535 --ipset=ipset-all.txt --dpi-desync=fake --dpi-desync-autottl=2 --dpi-desync-repeats=10 --dpi-desync-any-protocol=1 --dpi-desync-fake-unknown-udp=quic_initial_www_google_com.bin --dpi-desync-cutoff=n2
--filter-udp=1024-65535 --ipset=ipset-all.txt --dpi-desync=fake --dpi-desync-autottl=2 --dpi-desync-repeats=14 --dpi-desync-any-protocol=1 --dpi-desync-fake-unknown-udp=quic_initial_www_google_com.bin --dpi-desync-cutoff=n3
--filter-udp=5056,27002 --dpi-desync-any-protocol --dpi-desync=fake --dpi-desync-repeats=6 --dpi-desync-cutoff=n15 --dpi-desync-fake-unknown-udp=quic_initial_www_google_com.bin --new

------ добавить в остьальное tcp по всем портам --------------------
--filter-tcp=4950-4955 --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=8 --dpi-desync-fooling=md5sig,badseq --new
--filter-tcp=6695-6705 --dpi-desync=fake,split2 --dpi-desync-repeats=8 --dpi-desync-fooling=md5sig --dpi-desync-autottl=2 --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --new

------ иногда тут писал  --ipset=ipset-all.txt, лучше убрать чтобы по всем портам пробивать --------------------
--filter-udp=443 --dpi-desync=fake --dpi-desync-repeats=11 --new
--filter-udp=443 --dpi-desync=fake --dpi-desync-repeats=6 --dpi-desync-fake-quic=quic_initial_www_google_com.bin --new

------ ВАЖНЫЕ И НЕОБЫЧНЫЕ СТРАТЕГИИ по идее надо писать syndata в конце в порядке исключения для всех доменов--------------------
--filter-tcp=443 --ipset=russia-youtube-rtmps.txt --dpi-desync=syndata --dpi-desync-fake-syndata=tls_clienthello_4.bin --dpi-desync-autottl --new
--filter-tcp=443 --ipset=russia-youtube-rtmps.txt --dpi-desync=syndata --dpi-desync-fake-syndata=tls_clienthello_4.bin --dpi-desync-fooling=badseq --new
--filter-tcp=443 --ipset=russia-youtube-rtmps.txt --dpi-desync=syndata --dpi-desync-fake-syndata=tls_clienthello_7.bin --dup=2 --dup-cutoff=n3 --new
--filter-tcp=443 --ipset=russia-youtube-rtmps.txt --dpi-desync=syndata --dpi-desync-fake-syndata=syn_packet.bin --dup=2 --dup-cutoff=n3 --new

--filter-udp=443 --hostlist=youtubeQ.txt --dpi-desync=fake,udplen --dpi-desync-udplen-increment=4 --dpi-desync-fake-quic=quic_3.bin --dpi-desync-cutoff=n3 --dpi-desync-repeats=2 --new

--filter-tcp=443 --hostlist=list-general.txt --hostlist=other.txt --dpi-desync=split2 --dpi-desync-split-seqovl=652 --dpi-desync-split-pos=2 --dpi-desync-split-seqovl-pattern=tls_clienthello_www_google_com.bin --new
--filter-tcp=443 --hostlist=list-general.txt --hostlist=other.txt --dpi-desync=split --dpi-desync-split-pos=1 --dpi-desync-autottl --dpi-desync-fooling=badseq --dpi-desync-repeats=8 --new
--filter-tcp=443 --hostlist=list-general.txt --hostlist=other.txt --dpi-desync=fake,split2 --dpi-desync-repeats=6 --dpi-desync-fooling=md5sig --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --new
--filter-tcp=443 --hostlist=list-general.txt --hostlist=other.txt --dpi-desync=split2 --dpi-desync-repeats=2 --dpi-desync-split-seqovl=681 --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq,hopbyhop2 --dpi-desync-split-seqovl-pattern=tls_clienthello_www_google_com.bin --new
--filter-tcp=443,1024-65535 --ipset=ipset-all.txt --dpi-desync=split2 --dpi-desync-split-seqovl=681 --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq,hopbyhop2 --dpi-desync-split-seqovl-pattern=tls_clienthello_www_google_com.bin --new

--filter-tcp=443,1024-65535 --ipset=ipset-all.txt --dpi-desync=split2 --dpi-desync-split-seqovl=652 --dpi-desync-split-pos=2 --dpi-desync-split-seqovl-pattern=tls_clienthello_www_google_com.bin --new
--filter-tcp=443,1024-65535 --ipset=ipset-all.txt --dpi-desync=split --dpi-desync-split-pos=1 --dpi-desync-autottl --dpi-desync-fooling=badseq --dpi-desync-repeats=8 --new
--filter-tcp=443,1024-65535 --ipset=ipset-all.txt --dpi-desync=fake,split2 --dpi-desync-repeats=6 --dpi-desync-fooling=md5sig --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --new
--filter-tcp=443,1024-65535 --dpi-desync=syndata --new
"""

BUILTIN_STRATEGIES = {
    "faketlsautoalt": {
        "name": "FAKE TLS AUTO ALT 1.8.1",
        "description": "Стратегия с fake TLS и split для общего использования",
        "version": "1.0",
        "provider": "universal",
        "author": "Unknown",
        "updated": "2025-06-21",
        "label": LABEL_STABLE,
        "all_sites": True,
        "ports": [80, 443, 1024, 65535],
        "use_https": True,
        "fragments": True,
        "ttl": "auto",
        "args": f"""--wf-l3=ipv4,ipv6 --wf-tcp=80,443 --wf-udp=,1024-65535

--filter-tcp=80 --hostlist=list-general.txt --dpi-desync=fake,fakedsplit --dpi-desync-autottl=2 --dpi-desync-fooling=md5sig --new
--filter-tcp=443 --hostlist=list-general.txt --hostlist=other.txt --dpi-desync=split --dpi-desync-split-pos=1 --dpi-desync-autottl --dpi-desync-fooling=badseq --dpi-desync-repeats=8 --dpi-desync-fake-tls-mod=rnd,dupsid,sni=www.google.com --new
--filter-tcp=80 --ipset=ipset-all.txt --dpi-desync=fake,fakedsplit --dpi-desync-autottl=2 --dpi-desync-fooling=md5sig --new
--filter-tcp=443,1024-65535 --ipset=ipset-all.txt --dpi-desync=split --dpi-desync-split-pos=1 --dpi-desync-autottl --dpi-desync-fooling=badseq --dpi-desync-repeats=8 --dpi-desync-fake-tls-mod=rnd,dupsid,sni=www.google.com --new
"""
    },
    "faketlsalt_181": {
        "name": "FAKE TLS ALT 1.8.1",
        "description": "Стратегия с fake TLS mod для расширенной поддержки",
        "version": "1.0",
        "provider": "universal",
        "author": "Unknown",
        "updated": "2025-06-21",
        "label": LABEL_RECOMMENDED,
        "all_sites": True,
        "ports": [80, 443, 1024, 65535],
        "use_https": True,
        "fragments": True,
        "ttl": "auto",
        "args": f"""--wf-l3=ipv4,ipv6 --wf-tcp=80,443 --wf-udp=,1024-65535



--filter-tcp=443 --hostlist=list-general.txt --hostlist=other.txt --dpi-desync=fake --dpi-desync-fooling=md5sig --dpi-desync-fake-tls-mod=rnd,rndsni,padencap --new
--filter-udp=443 --dpi-desync=fake --dpi-desync-repeats=6 --dpi-desync-fake-quic=quic_initial_www_google_com.bin --new
--filter-tcp=80 --dpi-desync=fake,split2 --dpi-desync-autottl=2 --dpi-desync-fooling=md5sig --new
--filter-tcp=443,1024-65535 --dpi-desync=fake --dpi-desync-fooling=md5sig --dpi-desync-fake-tls-mod=rnd,rndsni,padencap --new"""
    },
    "faketlsalt2_181": {
        "name": "FAKE TLS ALT2 1.8.1",
        "description": "Стратегия с fake TLS и split2 seqovl=681",
        "version": "1.0",
        "provider": "universal",
        "author": "Unknown",
        "updated": "2025-06-21",
        "label": LABEL_RECOMMENDED,
        "all_sites": True,
        "ports": [80, 443, 1024, 65535],
        "use_https": True,
        "fragments": True,
        "ttl": "auto",
        "args": f"""--wf-l3=ipv4,ipv6 --wf-tcp=80,443 --wf-udp=,1024-65535


--filter-tcp=443 --hostlist=list-general.txt --hostlist=other.txt --dpi-desync=fake,split2 --dpi-desync-split-seqovl=681 --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq --dpi-desync-repeats=8 --dpi-desync-split-seqovl-pattern=tls_clienthello_www_google_com.bin --dpi-desync-fake-tls-mod=rnd,dupsid,sni=www.google.com --new
--filter-tcp=80 --ipset=ipset-all.txt --dpi-desync=fake,fakedsplit --dpi-desync-autottl=2 --dpi-desync-fooling=md5sig --new
--filter-tcp=443,1024-65535 --ipset=ipset-all.txt --dpi-desync=fake,split2 --dpi-desync-split-seqovl=681 --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq --dpi-desync-repeats=8 --dpi-desync-split-seqovl-pattern=tls_clienthello_www_google_com.bin --dpi-desync-fake-tls-mod=rnd,dupsid,sni=www.google.com --new
"""
    },
    "faketlsauto_181": {
        "name": "FAKE TLS AUTO",
        "description": "Стратегия с fake TLS и multidisorder",
        "version": "1.0",
        "provider": "universal",
        "author": "Unknown",
        "updated": "2025-06-21",
        "label": LABEL_STABLE,
        "all_sites": True,
        "ports": [80, 443, 1024, 65535],
        "use_https": True,
        "fragments": True,
        "ttl": "auto",
        "args": f"""--wf-l3=ipv4,ipv6 --wf-tcp=80,443 --wf-udp=,1024-65535


--filter-tcp=443 --hostlist=list-general.txt --hostlist=other.txt --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=11 --dpi-desync-fooling=md5sig --dpi-desync-fake-tls-mod=rnd,dupsid,sni=www.google.com --new
--filter-tcp=80 --ipset=ipset-all.txt --dpi-desync=fake,fakedsplit --dpi-desync-autottl=2 --dpi-desync-fooling=md5sig --new
--filter-tcp=443,1024-65535 --ipset=ipset-all.txt --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=11 --dpi-desync-fooling=md5sig --dpi-desync-fake-tls-mod=rnd,dupsid,sni=www.google.com --new
"""
    },
    "mgts_181": {
        "name": "МГТС 1.8.1",
        "description": "Оптимизировано для провайдера МГТС",
        "version": "1.0",
        "provider": "МГТС",
        "author": "Unknown",
        "updated": "2025-06-21",
        "label": LABEL_RECOMMENDED,
        "all_sites": True,
        "ports": [80, 443, 1024, 65535],
        "use_https": True,
        "fragments": True,
        "ttl": "auto",
        "args": f"""--wf-l3=ipv4,ipv6 --wf-tcp=80,443 --wf-udp=,1024-65535



--filter-tcp=443 --hostlist=list-general.txt --hostlist=other.txt --dpi-desync=fake --dpi-desync-autottl=2 --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --new


--filter-tcp=443,1024-65535 --ipset=ipset-all.txt --dpi-desync=fake --dpi-desync-autottl=2 --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --new
"""
    },
    "mgts2_181": {
        "name": "МГТС2 1.8.1",
        "description": "Альтернативная стратегия для провайдера МГТС",
        "version": "1.1",
        "provider": "МГТС",
        "author": "Unknown",
        "updated": "2025-06-21",
        "label": LABEL_STABLE,
        "all_sites": True,
        "ports": [80, 443, 1024, 65535],
        "use_https": True,
        "fragments": True,
        "ttl": "auto",
        "args": f"""


--filter-tcp=443 --hostlist=list-general.txt --hostlist=other.txt --dpi-desync=fake --dpi-desync-repeats=6 --dpi-desync-fooling=md5sig --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --new


--filter-tcp=443,1024-65535 --ipset=ipset-all.txt --dpi-desync=fake --dpi-desync-repeats=6 --dpi-desync-fooling=md5sig --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --new
"""
    },
    "YTDisBystro_34_Amazon1": {
        "name": "YTDisBystro 3.4 Amazon 1",
        "description": "Оптимизировано для Amazon Games, Discord и YouTube",
        "version": "1.0",
        "provider": "universal",
        "author": "Unknown",
        "updated": "2025-06-22",
        "label": LABEL_RECOMMENDED,
        "all_sites": True,
        "ports": [80, 443, 444, 65535],
        "use_https": True,
        "fragments": True,
        "ttl": "auto",
        "args": f"""--wf-tcp=80,443,444-65535 --wf-udp=443,444-65535
--filter-udp=443 --hostlist=russia-youtubeQ.txt --dpi-desync=fake,udplen --dpi-desync-udplen-increment=8 --dpi-desync-udplen-pattern=0x0E0F0E0F --dpi-desync-fake-quic=quic_7.bin --dpi-desync-cutoff=n3 --dpi-desync-repeats=2 --new

--filter-tcp=80 --hostlist-domains=cloudfront.net,amazon.com,amazonaws.com,awsstatic.com,epicgames.com --dpi-desync=fake,multisplit --dpi-desync-split-seqovl=2 --dpi-desync-split-pos=sld+1 --dpi-desync-fake-http=http_fake_MS.bin --dpi-desync-fooling=md5sig --dup=2 --dup-fooling=md5sig --dup-cutoff=n3 --new
--filter-tcp=80 --ipset=cloudflare-ipset.txt --ipset-exclude-ip=1.1.1.1,1.0.0.1,212.109.195.93,83.220.169.155,141.105.71.21,18.244.96.0/19,18.244.128.0/19 --dpi-desync=fake,multisplit --dpi-desync-split-seqovl=2 --dpi-desync-split-pos=sld+1 --dpi-desync-fake-http=http_fake_MS.bin --dpi-desync-fooling=md5sig --dup=2 --dup-fooling=md5sig --dup-cutoff=n3 --new

--filter-udp=443,444-65535 --hostlist-domains=awsglobalaccelerator.com,cloudfront.net,amazon.com,amazonaws.com,awsstatic.com,epicgames.com --ipset=cloudflare-ipset.txt --ipset-exclude-ip=1.1.1.1,1.0.0.1,212.109.195.93,83.220.169.155,141.105.71.21,18.244.96.0/19,18.244.128.0/19 --dpi-desync=fake --dpi-desync-any-protocol --dpi-desync-fake-unknown-udp=quic_6.bin --dpi-desync-repeats=2 --dpi-desync-cutoff=n4 --dpi-desync-ttl=7 --new

--filter-tcp=443,444-65535 --hostlist-domains=awsglobalaccelerator.com,cloudfront.net,amazon.com,amazonaws.com,awsstatic.com,epicgames.com --ipset=cloudflare-ipset.txt --ipset-exclude-ip=1.1.1.1,1.0.0.1,212.109.195.93,83.220.169.155,141.105.71.21,18.244.96.0/19,18.244.128.0/19 --dpi-desync=multisplit --dpi-desync-split-seqovl=211 --dpi-desync-split-seqovl-pattern=tls_clienthello_5.bin --new 

"""
    },
    "YTDisBystro_34_Amazon2": {
        "name": "YTDisBystro 3.4 Amazon 2",
        "description": "Альтернативная версия для Amazon Games с ipfrag2",
        "version": "1.0",
        "provider": "universal",
        "author": "Unknown",
        "updated": "2025-06-22",
        "label": LABEL_RECOMMENDED,
        "all_sites": True,
        "ports": [80, 443, 444, 65535],
        "use_https": True,
        "fragments": True,
        "ttl": "auto",
        "args": f"""--wf-tcp=80,443,444-65535 --wf-udp=443,444-65535
--filter-udp=443 --hostlist=russia-youtubeQ.txt --dpi-desync=fake,ipfrag2 --dpi-desync-fake-quic=quic_7.bin --dpi-desync-cutoff=n3 --dpi-desync-repeats=3 --new
--filter-tcp=80 --hostlist-domains=cloudfront.net,amazon.com,amazonaws.com,awsstatic.com,epicgames.com --dpi-desync=fake,multisplit --dpi-desync-split-seqovl=2 --dpi-desync-split-pos=sld+1 --dpi-desync-fake-http=http_fake_MS.bin --dpi-desync-fooling=md5sig --dup=2 --dup-fooling=md5sig --dup-cutoff=n3 --new





"""
    },
    "YTDisBystro_34_Amazon3": {
        "name": "YTDisBystro 3.4 Amazon 3",
        "description": "Версия с syndata и ipcache для YouTube",
        "version": "1.0",
        "provider": "universal",
        "author": "Unknown",
        "updated": "2025-06-22",
        "label": LABEL_RECOMMENDED,
        "all_sites": True,
        "ports": [80, 443, 444, 65535],
        "use_https": True,
        "fragments": True,
        "ttl": "auto",
        "args": f"""--wf-tcp=80,443,444-65535 --wf-udp=443,444-65535
--filter-udp=443 --hostlist=russia-youtubeQ.txt --dpi-desync=fake,udplen --dpi-desync-udplen-increment=4 --dpi-desync-fake-quic=quic_4.bin --dpi-desync-cutoff=n3 --dpi-desync-repeats=2 --new

--filter-tcp=80 --hostlist-domains=cloudfront.net,amazon.com,amazonaws.com,awsstatic.com,epicgames.com --dpi-desync=fake,multisplit --dpi-desync-split-seqovl=2 --dpi-desync-split-pos=sld+1 --dpi-desync-fake-http=http_fake_MS.bin --dpi-desync-fooling=md5sig --dup=2 --dup-fooling=md5sig --dup-cutoff=n3 --new




"""
    },
    "YTDisBystro_34_1": {
        "name": "YTDisBystro 3.4 v1",
        "description": "Универсальная стратегия для YouTube, Discord и общих сайтов",
        "version": "1.0",
        "provider": "universal",
        "author": "Unknown",
        "updated": "2025-06-22",
        "label": LABEL_STABLE,
        "all_sites": True,
        "ports": [80, 443],
        "use_https": True,
        "fragments": True,
        "ttl": "auto",
        "args": f"""--wf-tcp=80,443 --wf-udp=443



--filter-udp=443 --hostlist=russia-youtubeQ.txt --dpi-desync=fake,udplen --dpi-desync-udplen-increment=8 --dpi-desync-udplen-pattern=0x0F0F0E0F --dpi-desync-fake-quic=quic_6.bin --dpi-desync-cutoff=n3 --dpi-desync-repeats=2 --new
--filter-tcp=80 --hostlist=other.txt --hostlist=russia-blacklist.txt --dpi-desync=fake,multisplit --dpi-desync-split-seqovl=2 --dpi-desync-split-pos=sld+1 --dpi-desync-fake-http=http_fake_MS.bin --dpi-desync-fooling=md5sig --dup=2 --dup-fooling=md5sig --dup-cutoff=n3 --new

--filter-tcp=443 --hostlist-domains=updates.discord.com,stable.dl2.discordapp.net,animego.online,animejoy.ru,rutracker.org,static.rutracker.cc,pixiv.net,cdn77.com --dpi-desync=multisplit --dpi-desync-split-seqovl=293 --dpi-desync-split-seqovl-pattern=tls_clienthello_12.bin --new
--filter-tcp=443 --hostlist-domains=awsglobalaccelerator.com,cloudfront.net,amazon.com,amazonaws.com,awsstatic.com --dpi-desync=multisplit --dpi-desync-split-seqovl=211 --dpi-desync-split-seqovl-pattern=tls_clienthello_5.bin --new
--filter-l3=ipv6 --filter-tcp=443 --ipset=cloudflare-ipset_v6.txt --ipset-exclude-ip=2606:4700:4700::1111,2606:4700:4700::1001 --dpi-desync=multisplit --dpi-desync-split-seqovl=226 --dpi-desync-split-seqovl-pattern=tls_clienthello_18.bin --dup=2 --dup-cutoff=n3 --new
--filter-l3=ipv4 --filter-tcp=443 --ipset=cloudflare-ipset.txt --ipset-exclude-ip=1.1.1.1,1.0.0.1,212.109.195.93,83.220.169.155,141.105.71.21,18.244.96.0/19,18.244.128.0/19 --dpi-desync=multisplit --dpi-desync-split-seqovl=226 --dpi-desync-split-seqovl-pattern=tls_clienthello_18.bin --dup=2 --dup-cutoff=n3 --new

 --new
--filter-l3=ipv4 --filter-tcp=80 --hostlist-exclude=netrogat.txt --dpi-desync=fake,multisplit --dpi-desync-split-seqovl=2 --dpi-desync-split-pos=host+1 --dpi-desync-fake-http=0x0E0E0F0E --dpi-desync-fooling=md5sig --new
--filter-l3=ipv4 --filter-tcp=443 --hostlist-exclude=netrogat.txt --dpi-desync=fake,fakedsplit --dpi-desync-split-pos=1 --dpi-desync-fake-tls=tls_clienthello_9.bin --dpi-desync-fooling=badseq --dpi-desync-autottl"""
    },
    "YTDisBystro_34_2": {
        "name": "YTDisBystro 3.4 v2",
        "description": "Версия с ipfrag2 и autohostlist",
        "version": "1.0",
        "provider": "universal",
        "author": "Unknown",
        "updated": "2025-06-22",
        "label": LABEL_STABLE,
        "all_sites": True,
        "use_https": True,
        "fragments": True,
        "ttl": "auto",
        "args": f"""--wf-tcp=80,443

--filter-udp=443 --hostlist=russia-youtubeQ.txt --dpi-desync=fake,ipfrag2 --dpi-desync-fake-quic=quic_5.bin --dpi-desync-cutoff=n3 --dpi-desync-repeats=3 --new

--filter-tcp=443 --hostlist-domains=updates.discord.com,stable.dl2.discordapp.net,animego.online,animejoy.ru,rutracker.org,static.rutracker.cc,pixiv.net,cdn77.com --dpi-desync=multisplit --dpi-desync-split-seqovl=293 --dpi-desync-split-seqovl-pattern=tls_clienthello_12.bin --new
--filter-tcp=443 --hostlist-domains=awsglobalaccelerator.com,cloudfront.net,amazon.com,amazonaws.com,awsstatic.com --dpi-desync=multisplit --dpi-desync-split-seqovl=211 --dpi-desync-split-seqovl-pattern=tls_clienthello_5.bin --new
--filter-l3=ipv6 --filter-tcp=443 --ipset=cloudflare-ipset_v6.txt --ipset-exclude-ip=2606:4700:4700::1111,2606:4700:4700::1001 --dpi-desync=multisplit --dpi-desync-split-seqovl=226 --dpi-desync-split-seqovl-pattern=tls_clienthello_18.bin --dup=2 --dup-cutoff=n3 --new
--filter-l3=ipv4 --filter-tcp=443 --ipset=cloudflare-ipset.txt --ipset-exclude-ip=1.1.1.1,1.0.0.1,212.109.195.93,83.220.169.155,141.105.71.21,18.244.96.0/19,18.244.128.0/19 --dpi-desync=multisplit --dpi-desync-split-seqovl=286 --dpi-desync-split-seqovl-pattern=tls_clienthello_11.bin --dup=2 --dup-cutoff=n3 --new

 --new
--filter-l3=ipv4 --filter-tcp=80 --hostlist-auto=autohostlist.txt --hostlist-exclude=netrogat.txt --dpi-desync=fake,multisplit --dpi-desync-split-seqovl=2 --dpi-desync-split-pos=host+1 --dpi-desync-fake-http=0x0E0E0F0E --dpi-desync-fooling=md5sig --new
--filter-l3=ipv4 --filter-tcp=443 --hostlist-auto=autohostlist.txt --hostlist-exclude=netrogat.txt --dpi-desync=fake,fakedsplit --dpi-desync-split-pos=1 --dpi-desync-fake-tls=tls_clienthello_9.bin --dpi-desync-fooling=badseq --dpi-desync-autottl"""
    },
    "YTDisBystro_34_3": {
        "name": "YTDisBystro 3.4 v3",
        "description": "Версия с udplen pattern 0xFEA82025 и syndata",
        "version": "1.0",
        "provider": "universal",
        "author": "Unknown",
        "updated": "2025-06-22",
        "label": LABEL_STABLE,
        "all_sites": True,
        "ports": [80, 443],
        "use_https": True,
        "fragments": True,
        "ttl": "auto",
        "args": f"""--wf-tcp=80,443

--filter-udp=443 --hostlist=russia-youtubeQ.txt --dpi-desync=fake,udplen --dpi-desync-udplen-increment=8 --dpi-desync-udplen-pattern=0xFEA82025 --dpi-desync-fake-quic=quic_4.bin --dpi-desync-cutoff=n4 --dpi-desync-repeats=2 --new


--dpi-desync-fake-tls=0x0F0F0E0F --dpi-desync-fake-tls=tls_clienthello_9.bin --dpi-desync-fake-tls-mod=rnd,dupsid --dpi-desync-fooling=md5sig --dpi-desync-autottl --dup=2 --dup-fooling=md5sig --dup-autottl --dup-cutoff=n3 --new


--filter-tcp=443 --hostlist-domains=updates.discord.com,stable.dl2.discordapp.net,animego.online,animejoy.ru,rutracker.org,static.rutracker.cc,pixiv.net,cdn77.com --dpi-desync=multisplit --dpi-desync-split-seqovl=293 --dpi-desync-split-seqovl-pattern=tls_clienthello_12.bin --new
--filter-tcp=443 --hostlist-domains=awsglobalaccelerator.com,cloudfront.net,amazon.com,amazonaws.com,awsstatic.com --dpi-desync=multisplit --dpi-desync-split-seqovl=211 --dpi-desync-split-seqovl-pattern=tls_clienthello_5.bin --new
--filter-l3=ipv6 --filter-tcp=443 --ipset=cloudflare-ipset_v6.txt --ipset-exclude-ip=2606:4700:4700::1111,2606:4700:4700::1001 --dpi-desync=multisplit --dpi-desync-split-seqovl=226 --dpi-desync-split-seqovl-pattern=tls_clienthello_18.bin --dup=2 --dup-cutoff=n3 --new
--filter-l3=ipv4 --filter-tcp=443 --ipset=cloudflare-ipset.txt --ipset-exclude-ip=1.1.1.1,1.0.0.1,212.109.195.93,83.220.169.155,141.105.71.21,18.244.96.0/19,18.244.128.0/19 --dpi-desync=fake,multisplit --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls=0x0F0F0E0F --dpi-desync-fake-tls=tls_clienthello_9.bin --dpi-desync-fake-tls-mod=rnd,dupsid --dpi-desync-fooling=md5sig --dpi-desync-autottl --dup=2 --dup-fooling=md5sig --dup-autottl --dup-cutoff=n3 --new

 --new
--filter-l3=ipv4 --filter-tcp=80 --hostlist-auto=autohostlist.txt --hostlist-exclude=netrogat.txt --dpi-desync=fake,multisplit --dpi-desync-split-seqovl=2 --dpi-desync-split-pos=host+1 --dpi-desync-fake-http=0x0E0E0F0E --dpi-desync-fooling=md5sig --new
--filter-l3=ipv4 --filter-tcp=443 --hostlist-auto=autohostlist.txt --hostlist-exclude=netrogat.txt --dpi-desync=fake,fakedsplit --dpi-desync-split-pos=1 --dpi-desync-fake-tls=tls_clienthello_9.bin"""
    },
    "YTDisBystro_34_4": {
        "name": "YTDisBystro 3.4 v4",
        "description": "Версия с multidisorder и sni=fonts.google.com",
        "version": "1.0",
        "provider": "universal",
        "author": "Unknown",
        "updated": "2025-06-22",
        "label": LABEL_STABLE,
        "all_sites": True,
        "ports": [80, 443],
        "use_https": True,
        "fragments": True,
        "ttl": "auto",
        "args": f"""--wf-tcp=80,443

--filter-udp=443 --hostlist=russia-youtubeQ.txt --dpi-desync=fake,udplen --dpi-desync-udplen-increment=25 --dpi-desync-fake-quic=quic_5.bin --dpi-desync-repeats=2 --dpi-desync-cutoff=n3 --new

--filter-tcp=443 --hostlist-domains=updates.discord.com,stable.dl2.discordapp.net,animego.online,animejoy.ru,rutracker.org,static.rutracker.cc,pixiv.net,cdn77.com --dpi-desync=multisplit --dpi-desync-split-seqovl=293 --dpi-desync-split-seqovl-pattern=tls_clienthello_12.bin --new
--filter-tcp=443 --hostlist-domains=awsglobalaccelerator.com,cloudfront.net,amazon.com,amazonaws.com,awsstatic.com --dpi-desync=multisplit --dpi-desync-split-seqovl=211 --dpi-desync-split-seqovl-pattern=tls_clienthello_5.bin --new
--filter-l3=ipv6 --filter-tcp=443 --ipset=cloudflare-ipset_v6.txt --ipset-exclude-ip=2606:4700:4700::1111,2606:4700:4700::1001 --dpi-desync=multisplit --dpi-desync-split-seqovl=226 --dpi-desync-split-seqovl-pattern=tls_clienthello_18.bin --dup=2 --dup-cutoff=n3 --new
--filter-l3=ipv4 --filter-tcp=443 --ipset=cloudflare-ipset.txt --ipset-exclude-ip=1.1.1.1,1.0.0.1,212.109.195.93,83.220.169.155,141.105.71.21,18.244.96.0/19,18.244.128.0/19 --dpi-desync=syndata,multisplit --dpi-desync-split-seqovl=2 --dpi-desync-fake-syndata=tls_clienthello_16.bin --dup=2 --dup-cutoff=n3 --new

 --new
--filter-l3=ipv4 --filter-tcp=80 --hostlist-auto=autohostlist.txt --hostlist-exclude=netrogat.txt --dpi-desync=fake,multisplit --dpi-desync-split-seqovl=2 --dpi-desync-split-pos=host+1 --dpi-desync-fake-http=0x0E0E0F0E --dpi-desync-fooling=md5sig --new
--filter-l3=ipv4 --filter-tcp=443 --hostlist-auto=autohostlist.txt --hostlist-exclude=netrogat.txt --dpi-desync=fake,fakedsplit --dpi-desync-split-pos=1 --dpi-desync-fake-tls=tls_clienthello_9.bin --dpi-desync-fooling=badseq --dpi-desync-autottl"""
    },
    "discord_voice_md5sig_badseq": {
        "name": "Discord Voice & YT (md5sig и badseq)",
        "description": "Оптимизировано для Discord голосовых чатов с md5sig и badseq",
        "version": "1.0",
        "provider": "universal",
        "author": "kkalugin",
        "updated": "2025-07-13",
        "label": LABEL_STABLE,
        "all_sites": True,
        "ports": [80, 443],
        "use_https": True,
        "fragments": True,
        "ttl": "0",
        "args": f"""--wf-l3=ipv4,ipv6 --wf-tcp=80,443 --wf-udp=

--filter-tcp=80 --hostlist=russia-blacklist.txt --dpi-desync=fake,multisplit --dpi-desync-ttl=0 --dpi-desync-fooling=md5sig,badsum --new
--filter-tcp=443 --hostlist=russia-blacklist.txt --hostlist=ipset-all.txt --hostlist=other.txt --hostlist=list-general.txt --dpi-desync=fake,multidisorder --dpi-desync-split-pos=method+2,midsld,5 --dpi-desync-ttl=0 --dpi-desync-fooling=md5sig,badsum,badseq --dpi-desync-repeats=15 --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --new
--filter-udp=443 --dpi-desync=fake --dpi-desync-repeats=15 --dpi-desync-ttl=0 --dpi-desync-any-protocol --dpi-desync-cutoff=d4 --dpi-desync-fooling=md5sig,badsum --dpi-desync-fake-quic=quic_initial_www_google_com.bin --new
"""
    },
    "discord_voice_badseq": {
        "name": "Discord Voice & YT (badseq)",
        "description": "Оптимизировано для Discord голосовых чатов с badseq",
        "version": "1.0",
        "provider": "universal",
        "author": "kkalugin",
        "updated": "2025-07-13",
        "label": LABEL_STABLE,
        "all_sites": True,
        "ports": [80, 443],
        "use_https": True,
        "fragments": True,
        "ttl": "0",
        "args": f"""--wf-l3=ipv4,ipv6 --wf-tcp=80,443 --wf-udp=
--filter-tcp=80 --hostlist=russia-blacklist.txt --dpi-desync=fake,multisplit --dpi-desync-ttl=0 --dpi-desync-fooling=md5sig,badsum --new
--filter-tcp=443 --hostlist=russia-blacklist.txt --hostlist=ipset-all.txt --hostlist=other.txt --hostlist=list-general.txt --dpi-desync=fake,multidisorder --dpi-desync-split-pos=method+2,midsld,5 --dpi-desync-ttl=0 --dpi-desync-fooling=badsum,badseq --dpi-desync-repeats=15 --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --new
--filter-udp=443 --dpi-desync=fake --dpi-desync-repeats=15 --dpi-desync-ttl=0 --dpi-desync-any-protocol --dpi-desync-cutoff=d4 --dpi-desync-fooling=badsum --dpi-desync-fake-quic=quic_initial_www_google_com.bin --new
"""
    },
    "discord_voice_dtls": {
        "name": "Discord Voice & YT (DTLS)",
        "description": "Оптимизировано для Discord голосовых чатов с DTLS",
        "version": "1.0",
        "provider": "universal",
        "author": "",
        "updated": "2025-07-13",
        "label": LABEL_STABLE,
        "all_sites": True,
        "use_https": True,
        "fragments": True,
        "ttl": "auto",
        "args": f"""--wf-l3=ipv4,ipv6 --wf-tcp=80,443 --wf-udp=
--filter-tcp=80 --hostlist=russia-blacklist.txt --dpi-desync=fake,multisplit --dpi-desync-split-pos=method+2 --dpi-desync-fooling=md5sig --new
--filter-tcp=443 --hostlist=russia-blacklist.txt --dpi-desync=fake,multidisorder --dpi-desync-fake-tls=dtls_clienthello_w3_org.bin --dpi-desync-split-pos=1,midsld --dpi-desync-fooling=badseq,md5sig --new
--filter-udp=443 --dpi-desync=fake --dpi-desync-fake-quic=quic_initial_www_google_com.bin --dpi-desync-repeats=6 --new"""
    },
    "split_pos": {
        "name": "Split Position",
        "description": "Стратегия с multidisorder и различными позициями разделения",
        "version": "1.0",
        "provider": "universal",
        "author": "Unknown",
        "updated": "2025-07-13",
        "label": LABEL_STABLE,
        "all_sites": True,
        "ports": [80, 443],
        "use_https": True,
        "fragments": True,
        "ttl": "4",
        "args": f"""--wf-l3=ipv4,ipv6 --wf-tcp=80,443 --wf-udp=
--filter-tcp=443 --hostlist=russia-blacklist.txt --hostlist=other.txt --dpi-desync=fake,multidisorder --dpi-desync-fake-tls-mod=rnd,dupsid --dpi-desync-repeats=3 --dpi-desync-split-pos=100,midsld,sniext+1,endhost-2,-10 --dpi-desync-ttl=4 --new
--filter-udp=443 --dpi-desync=fake --dpi-desync-fake-quic=quic_initial_www_google_com.bin --dpi-desync-repeats=6 --new

"""
    },
    "alt1": {
        "name": "Alt 1",
        "description": "Взята с репозитория https://github.com/Flowseal/zapret-discord-youtube",
        "version": "1.9",
        "provider": "universal",
        "author": "Flowseal",
        "updated": "2025",
        "label": LABEL_STABLE,
        "all_sites": True,
        "ports": [80, 443, 27002],
        "use_https": True,
        "fragments": True,
        "ttl": "auto",
        "args": f"""--wf-tcp=80,443 --wf-udp=

--filter-tcp=80 --hostlist=discord.txt --ipset=ipset-cloudflare.txt --dpi-desync=fake,split2 --dpi-desync-autottl=2 --dpi-desync-fooling=md5sig --new

--filter-udp=443 --ipset=ipset-cloudflare.txt --dpi-desync=fake --dpi-desync-repeats=6 --dpi-desync-fake-quic=quic_initial_www_google_com.bin"""
    },
    "alt2": {
        "name": "Alt 2",
        "description": "Взята с репозитория https://github.com/Flowseal/zapret-discord-youtube",
        "version": "2.6",
        "provider": "universal",
        "author": "Flowseal",
        "updated": "2025",
        "label": LABEL_STABLE,
        "all_sites": True,
        "ports": [80, 443],
        "use_https": True,
        "fragments": True,
        "ttl": "auto",
        "args": f"""--wf-tcp=80,443 --wf-udp=


--filter-tcp=80 --hostlist=discord.txt --ipset=ipset-cloudflare.txt --dpi-desync=fake,split2 --dpi-desync-autottl=2 --dpi-desync-fooling=md5sig --new
--filter-tcp=443 --hostlist-exclude=netrogat.txt --dpi-desync=split2 --dpi-desync-split-seqovl=652 --dpi-desync-split-pos=2 --dpi-desync-split-seqovl-pattern=tls_clienthello_www_google_com.bin --new
--filter-udp=443 --ipset=ipset-cloudflare.txt --dpi-desync=fake --dpi-desync-repeats=6 --dpi-desync-fake-quic=quic_initial_www_google_com.bin"""
    },
    "alt3": {
        "name": "Alt 3",
        "description": "Взята с репозитория https://github.com/Flowseal/zapret-discord-youtube",
        "version": "3.6",
        "provider": "universal",
        "author": "Flowseal",
        "updated": "2025",
        "label": LABEL_RECOMMENDED,
        "all_sites": True,
        "ports": [80, 443, 27002],
        "use_https": True,
        "fragments": True,
        "ttl": "auto",
        "args": f"""--wf-tcp=80,443 --wf-udp=


--filter-tcp=80 --hostlist=discord.txt --ipset=ipset-cloudflare.txt --dpi-desync=fake,split2 --dpi-desync-autottl=2 --dpi-desync-fooling=md5sig --new

--filter-tcp=443 --hostlist-exclude=netrogat.txt --dpi-desync=split --dpi-desync-split-pos=1 --dpi-desync-autottl --dpi-desync-fooling=badseq --dpi-desync-repeats=8 --new
--filter-udp=443 --ipset=ipset-cloudflare.txt --dpi-desync=fake --dpi-desync-repeats=6 --dpi-desync-fake-quic=quic_initial_www_google_com.bin"""
    },
    "alt3_game": {
        "name": "Alt 3 (для игр)",
        "description": "Оптимизирована для игр с расширенным диапазоном портов",
        "version": "1.5",
        "provider": "universal",
        "author": "Flowseal",
        "updated": "2025",
        "label": LABEL_STABLE,
        "all_sites": True,
        "ports": [80, 443, 444, 27002],
        "use_https": True,
        "fragments": True,
        "ttl": "auto",
        "args": f"""
--filter-udp=443 --hostlist-domains=riotcdn.net,playvalorant.com,riotgames.com,pvp.net,rgpub.io,rdatasrv.net,riotcdn.com,riotgames.es,RiotClientServices.com,LeagueofLegends.com --dpi-desync=fake --dpi-desync-repeats=6 --dpi-desync-fake-quic=quic_initial_www_google_com.bin --new

--filter-tcp=80 --dpi-desync=fake,split2 --dpi-desync-autottl=2 --dpi-desync-fooling=md5sig --new
--filter-tcp=443 --hostlist-exclude=netrogat.txt --dpi-desync=split --dpi-desync-split-pos=1 --dpi-desync-autottl --dpi-desync-fooling=badseq --dpi-desync-repeats=8 --new
--filter-udp=443-9000 --dpi-desync=fake --dpi-desync-repeats=6 --dpi-desync-fake-quic=quic_initial_www_google_com.bin --new

--filter-tcp=2000-8400 --dpi-desync=syndata"""
    },
    "alt3_lol11": {
        "name": "Alt 3 LOL 11 (для игр)",
        "description": "Оптимизирована для League of Legends и других игр",
        "version": "1.2",
        "provider": "universal",
        "author": "G1NEX666",
        "updated": "2025",
        "label": LABEL_STABLE,
        "all_sites": True,
        "ports": [80, 443, 2099, 7002],
        "use_https": True,
        "fragments": True,
        "ttl": "auto",
        "args": f"""
--filter-udp=443 --dpi-desync=fake --dpi-desync-repeats=6 --dpi-desync-fake-quic=quic_initial_www_google_com.bin --new

--filter-tcp=80 --dpi-desync=fake,split2 --dpi-desync-autottl=2 --dpi-desync-fooling=md5sig --new
--filter-tcp=443 --hostlist-exclude=netrogat.txt --dpi-desync=split --dpi-desync-split-pos=1 --dpi-desync-autottl --dpi-desync-fooling=badseq --dpi-desync-repeats=8 --new
--filter-tcp=2099,5222,5223,8393-8400 --ipset=ipset-cloudflare.txt --dpi-desync=syndata --new
--filter-udp=2099,5222,5223,8393-8400 --ipset=ipset-cloudflare.txt --dpi-desync=fake --dpi-desync-repeats=6 --dpi-desync-fake-quic=quic_initial_www_google_com.bin --new

--filter-udp=5000-5500 --ipset=ipset-lol-ru.txt --dpi-desync=fake --dpi-desync-repeats=6 --new

--filter-tcp=2099 --ipset=ipset-lol-ru.txt --dpi-desync=syndata --new
--filter-tcp=5222,5223 --ipset=ipset-lol-euw.txt --dpi-desync=syndata --new
--filter-udp=5000-5500 --ipset=ipset-lol-euw.txt --dpi-desync=fake --dpi-desync-repeats=6"""
    },
    "alt4": {
        "name": "Alt 4",
        "description": "Взята с репозитория https://github.com/Flowseal/zapret-discord-youtube",
        "version": "1.9",
        "provider": "universal",
        "author": "Flowseal",
        "updated": "2025",
        "label": LABEL_STABLE,
        "all_sites": True,
        "ports": [80, 443, 27002],
        "use_https": True,
        "fragments": True,
        "ttl": "auto",
        "args": f"""--wf-tcp=80,443 --wf-udp=


--filter-tcp=80 --hostlist=discord.txt --ipset=ipset-cloudflare.txt --dpi-desync=fake,split2 --dpi-desync-autottl=2 --dpi-desync-fooling=md5sig --new
--filter-tcp=443 --hostlist-exclude=netrogat.txt --dpi-desync=fake,split2 --dpi-desync-repeats=6 --dpi-desync-fooling=md5sig --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --new

--filter-udp=443 --ipset=ipset-cloudflare.txt --dpi-desync=fake --dpi-desync-repeats=6 --dpi-desync-fake-quic=quic_initial_www_google_com.bin"""
    },
    "alt5": {
        "name": "Alt 5",
        "description": "Взята с репозитория https://github.com/Flowseal/zapret-discord-youtube",
        "version": "2.0",
        "provider": "universal",
        "author": "Flowseal",
        "updated": "2025",
        "label": LABEL_STABLE,
        "all_sites": True,
        "ports": [80, 443, 27002],
        "use_https": True,
        "fragments": True,
        "ttl": "auto",
        "args": f"""--wf-tcp=80,443 --wf-udp=



--filter-tcp=80 --hostlist=discord.txt --ipset=ipset-cloudflare.txt --dpi-desync=fake,split2 --dpi-desync-autottl=2 --dpi-desync-fooling=md5sig --new
--filter-l3=ipv4 --filter-tcp=443 --hostlist-exclude=netrogat.txt --dpi-desync=syndata"""
    },
    "alt1_161": {
        "name": "Alt v1 1.6.1 (Discord)",
        "description": "Взята с репозитория https://github.com/Flowseal/zapret-discord-youtube",
        "version": "1.3",
        "provider": "universal",
        "author": "Flowseal",
        "updated": "2024",
        "label": LABEL_STABLE,
        "all_sites": True,
        "ports": [80, 443, 27002],
        "use_https": True,
        "fragments": True,
        "ttl": "auto",
        "args": f"""--wf-tcp=80,443 --wf-udp=



"""
    },
    "alt2_161": {
        "name": "Alt v2 1.6.1 (Discord)",
        "description": "Взята с репозитория https://github.com/Flowseal/zapret-discord-youtube",
        "version": "1.4",
        "provider": "universal",
        "author": "Flowseal",
        "updated": "2024",
        "label": LABEL_RECOMMENDED,
        "all_sites": True,
        "ports": [80, 443, 27002],
        "use_https": True,
        "fragments": True,
        "ttl": "auto",
        "args": f"""--wf-tcp=80,443 --wf-udp=




--filter-tcp=443 --hostlist=list-general.txt --dpi-desync=split2 --dpi-desync-split-seqovl=652 --dpi-desync-split-pos=2 --dpi-desync-split-seqovl-pattern=tls_clienthello_www_google_com.bin --new
--filter-tcp=443 --hostlist=other.txt --dpi-desync=split2 --dpi-desync-split-seqovl=652 --dpi-desync-split-pos=2 --dpi-desync-split-seqovl-pattern=tls_clienthello_www_google_com.bin"""
    },
    "alt3_161": {
        "name": "Alt v3 1.6.1 (Discord)",
        "description": "Взята с репозитория https://github.com/Flowseal/zapret-discord-youtube",
        "version": "1.4",
        "provider": "universal",
        "author": "Flowseal",
        "updated": "2024",
        "label": LABEL_RECOMMENDED,
        "all_sites": True,
        "ports": [80, 443, 27002],
        "use_https": True,
        "fragments": True,
        "ttl": "auto",
        "args": f"""--wf-tcp=80,443 --wf-udp=




--filter-tcp=443 --hostlist=list-general.txt --dpi-desync=split --dpi-desync-split-pos=1 --dpi-desync-autottl --dpi-desync-fooling=badseq --dpi-desync-repeats=8 --new
--filter-tcp=443 --hostlist=other.txt --dpi-desync=split --dpi-desync-split-pos=1 --dpi-desync-autottl --dpi-desync-fooling=badseq --dpi-desync-repeats=8"""
    },
    "alt4_161": {
        "name": "Alt v4 1.6.1 (Discord)",
        "description": "Взята с репозитория https://github.com/Flowseal/zapret-discord-youtube",
        "version": "1.3",
        "provider": "universal",
        "author": "Flowseal",
        "updated": "2024",
        "label": LABEL_STABLE,
        "all_sites": True,
        "ports": [80, 443, 27002],
        "use_https": True,
        "fragments": True,
        "ttl": "auto",
        "args": f"""--wf-tcp=80,443 --wf-udp=



--filter-tcp=443 --hostlist=list-general.txt --dpi-desync=fake,split2 --dpi-desync-repeats=6 --dpi-desync-fooling=md5sig --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --new

--filter-tcp=443 --hostlist=other.txt --dpi-desync=fake,split2 --dpi-desync-repeats=6 --dpi-desync-fooling=md5sig --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin"""
    },
    "alt5_161": {
        "name": "Alt v5 1.6.1 (Discord)",
        "description": "Взята с репозитория https://github.com/Flowseal/zapret-discord-youtube",
        "version": "1.2",
        "provider": "universal",
        "author": "Flowseal",
        "updated": "2024",
        "label": LABEL_STABLE,
        "all_sites": True,
        "ports": [80, 443, 27002],
        "use_https": True,
        "fragments": True,
        "ttl": "auto",
        "args": f"""--wf-tcp=80,443 --wf-udp=




--filter-l3=ipv4 --filter-tcp=443 --dpi-desync=syndata"""
    },
    "altmgts1_161": {
        "name": "Alt MGTS v1 1.6.1 (Discord)",
        "description": "Взята с репозитория https://github.com/Flowseal/zapret-discord-youtube",
        "version": "1.1",
        "provider": "МГТС",
        "author": "Flowseal",
        "updated": "2024",
        "label": LABEL_STABLE,
        "all_sites": True,
        "ports": [80, 443, 27002],
        "use_https": True,
        "fragments": True,
        "ttl": "auto",
        "args": f"""--wf-tcp=80,443 --wf-udp=




--filter-tcp=443 --hostlist=list-general.txt --dpi-desync=fake --dpi-desync-autottl=2 --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin"""
    },
    "altmgts2_161": {
        "name": "Alt MGTS v2 1.6.1 (Discord)",
        "description": "Взята с репозитория https://github.com/Flowseal/zapret-discord-youtube",
        "version": "1.1",
        "provider": "МГТС",
        "author": "Flowseal",
        "updated": "2024",
        "label": LABEL_STABLE,
        "all_sites": True,
        "ports": [80, 443, 27002],
        "use_https": True,
        "fragments": True,
        "ttl": "auto",
        "args": f"""--wf-tcp=80,443 --wf-udp=




--filter-tcp=443 --hostlist=list-general.txt --dpi-desync=fake --dpi-desync-repeats=6 --dpi-desync-fooling=md5sig --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin"""
    },
    "YTDisBystro_31_1": {
        "name": "YTDisBystro 3.1 v1",
        "description": "Оптимизировано для YouTube и Discord с syndata",
        "version": "1.4",
        "provider": "universal",
        "author": "KDS",
        "updated": "2025-04-27",
        "label": LABEL_RECOMMENDED,
        "all_sites": True,
        "ports": [80, 443],
        "use_https": True,
        "fragments": True,
        "ttl": "auto",
        "args": f"""--wf-tcp=80,443

--filter-udp=443 --hostlist=russia-youtubeQ.txt --dpi-desync=fake,udplen --dpi-desync-udplen-increment=8 --dpi-desync-udplen-pattern=0x0F0F0E0F --dpi-desync-fake-quic=quic_6.bin --dpi-desync-cutoff=n3 --dpi-desync-repeats=2 --dpi-desync-autottl --new
--filter-udp=443 --hostlist=russia-youtubeQ.txt --dpi-desync=fake,ipfrag2 --dpi-desync-fake-quic=quic_5.bin --dpi-desync-cutoff=n3 --dpi-desync-repeats=3 --new

--filter-udp=443 --hostlist=youtubeQ.txt --dpi-desync=fake,udplen --dpi-desync-udplen-increment=4 --dpi-desync-fake-quic=quic_4.bin --dpi-desync-cutoff=n3 --dpi-desync-repeats=2 --new
--filter-udp=443 --hostlist=youtubeQ.txt --dpi-desync=fake,ipfrag2 --dpi-desync-fake-quic=quic_3.bin --dpi-desync-cutoff=n3 --dpi-desync-repeats=2 --new

--filter-tcp=80 --hostlist=other.txt --hostlist-exclude=netrogat.txt --dpi-desync=fake,multisplit --dpi-desync-split-seqovl=2 --dpi-desync-split-pos=host+1 --dpi-desync-fake-http=0x0F0F0F0F --dpi-desync-fooling=md5sig --new
--filter-tcp=80 --dpi-desync=fake,multisplit --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=sld+1 --dpi-desync-fooling=badseq --new

---------------- CLOUD -------------------------
--filter-tcp=80 --hostlist-domains=cloudflareportal.com,cloudflareok.com,cloudflareclient.com,cloudflarecp.com --dpi-desync=fake,multisplit --dpi-desync-split-pos=sld+1 --dpi-desync-fooling=md5sig --dpi-desync-autottl --new

--filter-tcp=443 --hostlist-domains=cloudflareok.com,cloudflareclient.com,cloudflareportal.com,cloudflarecp.com --dpi-desync=fake,multisplit --dpi-desync-split-seqovl=1 --dpi-desync-fooling=md5sig,badseq 
--dpi-desync-fake-tls=tls_clienthello_7.bin --dpi-desync-fake-tls-mod=rnd,padencap --dpi-desync-autottl --new

--filter-udp=8886 --ipset-ip=188.114.96.0/22 --dpi-desync=fake --dpi-desync-any-protocol --dpi-desync-fake-unknown-udp=quic_4.bin --dpi-desync-cutoff=d2 --dpi-desync-autottl --new

--filter-tcp=443 --dpi-desync=fake,multidisorder --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=midsld+1 --dpi-desync-fooling=md5sig,badseq --dpi-desync-fake-tls=tls_clienthello_5.bin --dpi-desync-fake-tls-mod=rnd --dpi-desync-autottl
---------------- CLOUD -------------------------


--filter-tcp=80,443 --hostlist=other.txt --dpi-desync=fakeddisorder --dpi-desync-split-pos=2,midsld --dpi-desync-fakedsplit-pattern=tls_clienthello_1.bin --dpi-desync-fooling=badseq --new

--filter-tcp=443 --hostlist-domains=animego.online,doramy.club,animejoy.ru,getchu.com --dpi-desync=multisplit --dpi-desync-split-seqovl=308 --dpi-desync-split-seqovl-pattern=tls_clienthello_15.bin --new

--filter-tcp=443 --ipset-exclude-ip=1.1.1.1,1.0.0.1,212.109.195.93,83.220.169.155,141.105.71.21 --ipset=cloudflare-ipset.txt --dpi-desync=syndata,multisplit --dpi-desync-split-seqovl=1 --dpi-desync-fake-syndata=tls_clienthello_16.bin --dup=2 --dup-cutoff=n3 --new
--filter-tcp=443 --ipset-exclude-ip=1.1.1.1,1.0.0.1,212.109.195.93,83.220.169.155,141.105.71.21 --ipset=cloudflare-ipset.txt --dpi-desync=fakedsplit --dpi-desync-split-pos=7 --dpi-desync-fakedsplit-pattern=tls_clienthello_5.bin --dpi-desync-fooling=md5sig --dpi-desync-autottl --dup=2 --dup-fooling=md5sig --dup-autottl --dup-cutoff=n3 --new

--filter-tcp=443 --ipset-exclude-ip=1.1.1.1,1.0.0.1,212.109.195.93,83.220.169.155,141.105.71.21 --ipset=cloudflare-ipset.txt --dpi-desync=fake,multidisorder --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=sld+1 --dpi-desync-fake-tls=0x0F0F0E0F --dpi-desync-fake-tls=tls_clienthello_9.bin --dpi-desync-fake-tls-mod=rnd,dupsid --dpi-desync-fooling=md5sig --dpi-desync-autottl --dup=2 --dup-fooling=md5sig --dup-autottl --dup-cutoff=n3 --new

--filter-tcp=443 --hostlist=russia-blacklist.txt --hostlist=other.txt --dpi-desync=multisplit --dpi-desync-split-seqovl=308 --dpi-desync-split-seqovl-pattern=tls_clienthello_5.bin --dup=2 --dup-cutoff=n3 --new


--filter-tcp=443 --hostlist=other.txt --hostlist-exclude=netrogat.txt --dpi-desync=fake,fakedsplit --dpi-desync-split-pos=1 --dpi-desync-fake-tls=tls_clienthello_9.bin --dpi-desync-fooling=badseq --dpi-desync-autottl
--filter-tcp=443 --hostlist=other.txt --hostlist-exclude=netrogat.txt --dpi-desync=fake,fakedsplit --dpi-desync-split-pos=1 --dpi-desync-fake-tls=tls_clienthello_7.bin --dpi-desync-fooling=badseq --dpi-desync-autottl

--filter-tcp=443 --hostlist-exclude=netrogat.txt --dpi-desync=fakedsplit --dpi-desync-fooling=badseq --dpi-desync-split-pos=2,midsld-1 --dpi-desync-fakedsplit-pattern=tls_clienthello_4.bin --new
--filter-tcp=443 --hostlist-exclude=netrogat.txt --dpi-desync=fakeddisorder --dpi-desync-split-pos=2,midsld+1 --dpi-desync-fakedsplit-pattern=tls_clienthello_4.bin --dpi-desync-fooling=badseq --new

"""
    },
    "original_bolvan_2": {
        "name": "Оригинальная bol-van v2 (07.04.2025)",
        "description": "Оригинальная стратегия для большинства провайдеров",
        "version": "3.8",
        "provider": "universal",
        "author": "bol-van",
        "updated": "2025-04-10",
        "label": LABEL_STABLE,
        "all_sites": True,
        "use_https": True,
        "fragments": True,
        "ttl": "auto",
        "args": f"""


--filter-udp=443 --dpi-desync=fake --dpi-desync-repeats=11 --new"""
    },

    "original_bolvan": {
        "name": "Оригинальная bol-van v1 (07.04.2025)",
        "description": "Оптимизировано для Билайн",
        "version": "2.5",
        "provider": "Билайн",
        "author": "bol-van",
        "updated": "2025-04-10",
        "label": LABEL_RECOMMENDED,
        "all_sites": True,
        "use_https": True,
        "fragments": True,
        "ttl": "auto",
        "args": f"""

--filter-tcp=443 --dpi-desync=fake,multidisorder --dpi-desync-split-pos=midsld --dpi-desync-repeats=6 --dpi-desync-fooling=badseq,md5sig --new
--filter-udp=443 --dpi-desync=fake --dpi-desync-repeats=11 --new"""
    },
    "faketlsmod": {
        "name": "Fake TLS Mod ttl 4",
        "description": "Оптимизировано для Дискорда. Взята с репозитория https://github.com/Flowseal/zapret-discord-youtube",
        "version": "1.6",
        "provider": "universal",
        "author": "Flowseal",
        "updated": "2025",
        "label": LABEL_STABLE,
        "all_sites": True,
        "ports": [80, 443],
        "use_https": True,
        "fragments": True,
        "ttl": "4",
        "args": f"""--wf-tcp=80,443 --wf-udp=

--filter-tcp=80 --hostlist=discord.txt --ipset=ipset-cloudflare.txt --dpi-desync=fake,split2 --dpi-desync-autottl=3 --dpi-desync-fooling=md5sig --new
--filter-tcp=443 --dpi-desync=fake --dpi-desync-ttl=4 --dpi-desync-fake-tls-mod=rnd,rndsni,padencap"""
    },
    "faketlsmod2": {
        "name": "Fake TLS Mod 2 md5sig",
        "description": "Оптимизировано для Дискорда. Взята с репозитория https://github.com/Flowseal/zapret-discord-youtube",
        "version": "1.4",
        "provider": "universal",
        "author": "Flowseal",
        "updated": "2025",
        "label": LABEL_STABLE,
        "all_sites": True,
        "ports": [80, 443],
        "use_https": True,
        "fragments": True,
        "ttl": "auto",
        "args": f"""--wf-tcp=80,443 --wf-udp=



--filter-tcp=80 --hostlist=discord.txt --ipset=ipset-cloudflare.txt --dpi-desync=fake,split2 --dpi-desync-autottl=2 --dpi-desync-fooling=md5sig --new
--filter-tcp=443 --dpi-desync=fake --dpi-desync-fooling=md5sig --dpi-desync-fake-tls-mod=rnd,rndsni,padencap"""
    },
    "md5sigpadencap": {
        "name": "md5sig padencap",
        "description": "Использует md5sig и уникальный флаг rnd,rndsni,padencap",
        "version": "1.2",
        "provider": "Билайн",
        "author": "Unknown",
        "updated": "2025",
        "label": LABEL_STABLE,
        "all_sites": True,
        "ports": [80, 443],
        "use_https": True,
        "fragments": True,
        "ttl": "auto",
        "args": f"""--wf-tcp=443 --wf-udp=443
--filter-tcp=443 --hostlist=other.txt --hostlist=faceinsta.txt --dpi-desync=fake,multisplit --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=1 --dpi-desync-fake-tls=tls_clienthello_vk_com.bin --dpi-desync-ttl=5 --new



--filter-tcp=443 --hostlist=other.txt --dpi-desync=fake,split2 --dpi-desync-split-seqovl=625 --dpi-desync-split-tls=sniext --dpi-desync-fake-tls=tls_clienthello_vk_com.bin --dpi-desync-ttl=2 --new"""
    },
    "ttlpadencap": {
        "name": "ttl padencap",
        "description": "Использует ttl 1 и уникальный флаг rnd,rndsni,padencap",
        "version": "1.2",
        "provider": "Билайн",
        "author": "Unknown",
        "updated": "2025",
        "label": LABEL_STABLE,
        "all_sites": True,
        "ports": [443, 65535],
        "use_https": True,
        "fragments": True,
        "ttl": "auto",
        "args": f"""--wf-tcp=443 --wf-udp=443
--filter-tcp=443 --hostlist=other.txt --hostlist=faceinsta.txt --dpi-desync=fake,multisplit --dpi-desync-fooling=md5sig --dpi-desync-autottl --new


"""
    },
    "datanoackpadencap": {
        "name": "datanoack padencap (20.03.2025)",
        "description": "Использует datanoack и уникальный флаг rnd,rndsni,padencap",
        "version": "1.2",
        "provider": "Билайн",
        "author": "Unknown",
        "updated": "2025-03-20",
        "label": LABEL_STABLE,
        "all_sites": True,
        "ports": [443, 65535],
        "use_https": True,
        "fragments": True,
        "ttl": "auto",
        "args": f"""--wf-tcp=443 --wf-udp=443
--filter-tcp=443 --hostlist=other.txt --hostlist=faceinsta.txt --dpi-desync=fake,multisplit --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=1 --dpi-desync-fake-tls=tls_clienthello_vk_com.bin --dpi-desync-ttl=5 --new


"""
    },
    "datanoackpadencapmidsld": {
        "name": "datanoack padencap midsld (20.03.2025)",
        "description": "Использует datanoack, midsld и уникальный флаг rnd,rndsni,padencap",
        "version": "1.2",
        "provider": "Билайн",
        "author": "Unknown",
        "updated": "2025-03-20",
        "label": LABEL_STABLE,
        "all_sites": True,
        "ports": [443, 65535],
        "use_https": True,
        "fragments": True,
        "ttl": "auto",
        "args": f"""--wf-tcp=443 --wf-udp=443
--filter-tcp=443 --hostlist=other.txt --hostlist=faceinsta.txt --dpi-desync=fake,multisplit --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=1 --dpi-desync-fake-tls=tls_clienthello_vk_com.bin --dpi-desync-ttl=5 --new



--filter-tcp=443 --ipset=ipset-cloudflare.txt --dpi-desync=fake,fakeddisorder --dpi-desync-fooling=datanoack --dpi-desync-split-pos=midsld --dpi-desync-fake-tls-mod=rnd,rndsni,padencap"""
    },
    "multisplitmd5sigpadencap": {
        "name": "multisplit 1,md5sig padencap (discord)",
        "description": "Использует multisplit midsld и уникальный флаг rnd,rndsni,padencap",
        "version": "1.2",
        "provider": "Билайн",
        "author": "Unknown",
        "updated": "2025-03-25",
        "label": LABEL_STABLE,
        "all_sites": True,
        "ports": [443, 65535],
        "use_https": True,
        "fragments": True,
        "ttl": "1",
        "args": f"""--wf-tcp=443 --wf-udp=443
--filter-tcp=443 --hostlist=other.txt --hostlist=faceinsta.txt --dpi-desync=fake,multisplit --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=1 --dpi-desync-fake-tls=tls_clienthello_vk_com.bin --dpi-desync-ttl=5 --new


"""
    },
    "multisplitmd5sigpadencap": {
        "name": "multisplit 1,md5sig padencap (discord)",
        "description": "Использует multisplit midsld и уникальный флаг rnd,rndsni,padencap",
        "version": "1.2",
        "provider": "Билайн",
        "author": "Unknown",
        "updated": "2025-03-25",
        "label": LABEL_CAUTION,
        "all_sites": True,
        "ports": [443, 65535],
        "use_https": True,
        "fragments": True,
        "ttl": "1",
        "args": f"""--wf-tcp=443 --wf-udp=443



--filter-tcp=443 --dpi-desync=fake,multisplit --dpi-desync-ttl=1 --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls-mod=rnd,rndsni,padencap"""
    },
    "md5sigpadencap": {
        "name": "md5sig padencap (20.03.2025)",
        "description": "Использует midsld и уникальный флаг rnd,rndsni,padencap",
        "version": "1.2",
        "provider": "Билайн",
        "author": "Unknown",
        "updated": "2025-03-20",
        "label": LABEL_CAUTION,
        "all_sites": True,
        "ports": [443, 65535],
        "use_https": True,
        "fragments": True,
        "ttl": "auto",
        "args": f"""--wf-tcp=443 --wf-udp=443



--filter-tcp=443 --dpi-desync=fake --dpi-desync-fooling=md5sig --dpi-desync-fake-tls-mod=rnd,rndsni,padencap"""
    },
    "badsumpadencap": {
        "name": "badsum padencap (06.08.2025)",
        "description": "Использует badsum и уникальный флаг rnd,rndsni,padencap",
        "version": "1.2",
        "provider": "Билайн",
        "author": "Unknown",
        "updated": "2025-03-20",
        "label": LABEL_CAUTION,
        "all_sites": True,
        "ports": [443, 65535],
        "use_https": True,
        "fragments": True,
        "ttl": "auto",
        "args": f"""--wf-tcp=443 --wf-udp=443



--filter-tcp=443 --dpi-desync=fake --dpi-desync-fooling=badsum --dpi-desync-fake-tls-mod=rnd,rndsni,padencap"""
    },
    "datanoackpadencapmidsld": {
        "name": "datanoack padencap midsld (20.03.2025)",
        "description": "Использует datanoack, midsld и уникальный флаг rnd,rndsni,padencap",
        "version": "1.2",
        "provider": "Билайн",
        "author": "Unknown",
        "updated": "2025-03-20",
        "label": LABEL_CAUTION,
        "all_sites": True,
        "ports": [443, 65535],
        "use_https": True,
        "fragments": True,
        "ttl": "auto",
        "args": f"""--wf-tcp=443 --wf-udp=443



--filter-tcp=443 --dpi-desync=fake,fakeddisorder --dpi-desync-fooling=datanoack --dpi-desync-split-pos=midsld --dpi-desync-fake-tls-mod=rnd,rndsni,padencap"""
    },
    "discordtcp80": {
        "name": "Discord TCP 80",
        "description": "Рекомендуется для Дискорда",
        "version": "1.3",
        "provider": "universal",
        "author": "Unknown",
        "updated": "2024",
        "label": LABEL_STABLE,
        "all_sites": True,
        "ports": [80, 443],
        "use_https": True,
        "fragments": True,
        "ttl": "auto",
        "args": f"""--wf-tcp=80,443 --wf-udp=443
--filter-udp=443 --hostlist=youtubeQ.txt --dpi-desync=fake --dpi-desync-repeats=2 --dpi-desync-cutoff=n2 --dpi-desync-fake-quic=quic_test_00.bin --new

--filter-tcp=80 --hostlist=discord.txt --dpi-desync=fake,split2 --dpi-desync-autottl=2 --dpi-desync-fooling=md5sig --new

"""
    },
    "discordfake": {
        "name": "Discord Fake",
        "description": "Рекомендуется для Дискорда",
        "version": "1.3",
        "provider": "universal",
        "author": "Unknown",
        "updated": "2024",
        "label": LABEL_STABLE,
        "all_sites": True,
        "ports": [80, 443],
        "use_https": True,
        "fragments": True,
        "ttl": "auto",
        "args": f"""--wf-tcp=80,443 --wf-udp=443




"""
    },
    "discordfakesplit": {
        "name": "Discord Fake Split",
        "description": "Рекомендуется для Дискорда",
        "version": "1.3",
        "provider": "universal",
        "author": "Unknown",
        "updated": "2024",
        "label": LABEL_STABLE,
        "all_sites": True,
        "ports": [80, 443],
        "use_https": True,
        "fragments": True,
        "ttl": "auto",
        "args": f"""--wf-tcp=80,443 --wf-udp=

--filter-tcp=80 --hostlist=discord.txt --dpi-desync=fake,split2 --dpi-desync-autottl=2 --dpi-desync-fooling=md5sig --new


"""
    },
    "ultimatealt": {
        "name": "Ultimate Fix ALT",
        "description": "Рекомендуется для Билайна и Ростелекома",
        "version": "1.3",
        "provider": "Билайн",
        "author": "Unknown",
        "updated": "2024",
        "label": LABEL_STABLE,
        "all_sites": True,
        "ports": [80, 443, 65535],
        "use_https": True,
        "fragments": True,
        "ttl": "auto",
        "args": f"""--wf-tcp=80,443 --wf-udp=443

--filter-tcp=80 --hostlist=discord.txt --dpi-desync=fake,split2 --dpi-desync-autottl=2 --dpi-desync-fooling=md5sig --new


"""
    },
    "splitsniext": {
        "name": "Split с sniext",
        "description": "Стратегия с использованием split и sniext для YouTube и Discord",
        "version": "1.2",
        "provider": "universal",
        "author": "Unknown",
        "updated": "2024",
        "label": LABEL_STABLE,
        "all_sites": True,
        "ports": [80, 443],
        "use_https": True,
        "fragments": True,
        "ttl": "auto",
        "args": f"""--wf-tcp=80,443 --wf-udp=443
--filter-udp=443 --hostlist=youtubeQ.txt --dpi-desync=fake --dpi-desync-repeats=4 --dpi-desync-fake-quic=quic_initial_www_google_com.bin --new



--filter-tcp=443 --hostlist=other.txt --hostlist=faceinsta.txt"""
    },
    "splitbadseq": {
        "name": "Split с badseq",
        "description": "Стратегия с использованием split и badseq для YouTube и Discord",
        "version": "1.2",
        "provider": "universal",
        "author": "Unknown",
        "updated": "2024",
        "label": LABEL_STABLE,
        "all_sites": True,
        "ports": [80, 443],
        "use_https": True,
        "fragments": True,
        "ttl": "auto",
        "args": f"""--wf-tcp=80,443 --wf-udp=443




--filter-tcp=443 --hostlist=other.txt --hostlist=faceinsta.txt"""
    },
    "rosmega": {
        "name": "Ростелеком и Мегафон и ТТК",
        "description": "Оптимизировано для провайдеров Ростелеком, Мегафон и ТТК",
        "version": "1.4",
        "provider": "Ростелеком",
        "author": "Unknown",
        "updated": "2024",
        "label": LABEL_STABLE,
        "all_sites": True,
        "ports": [80, 443],
        "use_https": True,
        "fragments": True,
        "ttl": "auto",
        "args": f"""--wf-tcp=80,443 --wf-udp=443


"""
    },
    "rosmts": {
        "name": "Ростелеком и МГТС",
        "description": "Оптимизировано для провайдеров Ростелеком и МГТС",
        "version": "1.3",
        "provider": "Ростелеком",
        "author": "Unknown",
        "updated": "2024",
        "label": LABEL_STABLE,
        "all_sites": True,
        "ports": [80, 443],
        "use_https": True,
        "fragments": True,
        "ttl": "auto",
        "args": f"""--wf-tcp=80,443 --wf-udp=443
--filter-udp=443 --hostlist=youtubeQ.txt --dpi-desync=fake --dpi-desync-repeats=4 --dpi-desync-fake-quic=quic_1.bin --new


--filter-tcp=443 --dpi-desync=fake,split --dpi-desync-autottl=2 --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin"""
    },
    "other1": {
        "name": "Другие провайдеры 1",
        "description": "Универсальная стратегия для различных провайдеров",
        "version": "1.3",
        "provider": "universal",
        "author": "Unknown",
        "updated": "2024",
        "label": LABEL_STABLE,
        "all_sites": True,
        "ports": [443, 65535],
        "use_https": True,
        "fragments": True,
        "ttl": "auto",
        "args": f"""--wf-l3=ipv4,ipv6 --wf-tcp=443 --wf-udp=443



"""
    },
    "other2": {
        "name": "Другие провайдеры 2",
        "description": "Альтернативная универсальная стратегия",
        "version": "1.4",
        "provider": "universal",
        "author": "Unknown",
        "updated": "2024",
        "label": LABEL_STABLE,
        "all_sites": True,
        "ports": [443, 65535],
        "use_https": True,
        "fragments": True,
        "ttl": "auto",
        "args": f"""--wf-l3=ipv4,ipv6 --wf-tcp=443 --wf-udp=443

"""
    },
    "ankddev10": {
        "name": "Ankddev v10",
        "description": "Стратегия с syndata и disorder2 для Discord",
        "version": "1.5",
        "provider": "universal",
        "author": "Ankddev",
        "updated": "2024",
        "label": LABEL_STABLE,
        "all_sites": True,
        "ports": [443, 65535],
        "use_https": True,
        "fragments": True,
        "ttl": "auto",
        "args": f"""--wf-l3=ipv4,ipv6 --wf-tcp=443 --wf-udp=443


--filter-tcp=443 --hostlist-exclude=netrogat.txt --dpi-desync=syndata,multidisorder --dpi-desync-split-pos=4 --dpi-desync-repeats=10 --dpi-desync-fooling=md5sig --dpi-desync-fake-tls=tls_clienthello_vk_com_kyber.bin --new
--filter-udp=443 --hostlist=youtubeQ.txt --dpi-desync=fake,split2 --dpi-desync-repeats=10 --dpi-desync-udplen-increment=25 --dpi-desync-fake-quic=quic_initial_www_google_com.bin"""
    },
    "mgts2": {
        "name": "МГТС 2",
        "description": "Альтернативная стратегия для МГТС",
        "version": "1.7",
        "provider": "МГТС",
        "author": "Unknown",
        "updated": "2024",
        "label": LABEL_STABLE,
        "all_sites": True,
        "ports": [80, 443, 50900],
        "use_https": True,
        "fragments": True,
        "ttl": "3",
        "args": f"""--wf-tcp=80,443 --wf-udp=443

--filter-udp=443 --hostlist=youtubeQ.txt --dpi-desync=fake --dpi-desync-repeats=2 --dpi-desync-cutoff=n2 --dpi-desync-fake-quic=quic_initial_www_google_com.bin --new

--filter-tcp=443 --hostlist=other.txt --hostlist=faceinsta.txt --ipset=ipset-cloudflare.txt --dpi-desync=fake,split2 --dpi-desync-split-seqovl=1 --dpi-desync-split-tls=sniext --dpi-desync-fake-tls=tls_clienthello_2.bin --dpi-desync-ttl=2"""
    },
    "mgts3": {
        "name": "МГТС 3",
        "description": "Третья версия стратегии для МГТС",
        "version": "1.8",
        "provider": "МГТС",
        "author": "Unknown",
        "updated": "2024",
        "label": LABEL_STABLE,
        "all_sites": True,
        "ports": [80, 443, 50900],
        "use_https": True,
        "fragments": True,
        "ttl": "auto",
        "args": f"""--wf-tcp=80,443 --wf-udp=443

--filter-udp=443 --hostlist=youtubeQ.txt --dpi-desync=fake --dpi-desync-repeats=2 --dpi-desync-cutoff=n2 --dpi-desync-fake-quic=quic_initial_www_google_com.bin --new

"""
    },
    "mgts4": {
        "name": "МГТС 4",
        "description": "Четвертая версия стратегии для МГТС",
        "version": "1.9",
        "provider": "МГТС",
        "author": "Unknown",
        "updated": "2024",
        "label": LABEL_STABLE,
        "all_sites": True,
        "ports": [80, 443, 50900],
        "use_https": True,
        "fragments": True,
        "ttl": "auto",
        "args": f"""--wf-tcp=80,443 --wf-udp=443


--filter-tcp=443 --hostlist=other.txt --hostlist=faceinsta.txt --ipset=ipset-cloudflare.txt --dpi-desync=fake,split2 --dpi-desync-split-seqovl=2 --dpi-desync-split-pos=3 --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --dpi-desync-ttl=3 --new

--filter-tcp=443 --hostlist=other.txt --hostlist=faceinsta.txt --ipset=ipset-cloudflare.txt --dpi-desync=split --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq --dpi-desync-repeats=10 --dpi-desync-ttl=4"""
    },
    "ultazl": {
        "name": "Ульта конфиг ZL",
        "description": "Универсальная стратегия ZL",
        "version": "1.3",
        "provider": "universal",
        "author": "Unknown",
        "updated": "2024",
        "label": LABEL_STABLE,
        "all_sites": True,
        "use_https": True,
        "fragments": True,
        "ttl": "auto",
        "args": f"""
--filter-udp=443 --hostlist=youtubeQ.txt --dpi-desync=fake --dpi-desync-fake-quic=quic_1.bin --dpi-desync-repeats=4 --new


"""
    },
    "ulta2": {
        "name": "Ульта конфиг v2",
        "description": "Универсальная стратегия v2 с syndata",
        "version": "1.3",
        "provider": "universal",
        "author": "Unknown",
        "updated": "2024",
        "label": LABEL_STABLE,
        "all_sites": True,
        "use_https": True,
        "fragments": True,
        "ttl": "auto",
        "args": f"""

--filter-udp=443 --hostlist=youtubeQ.txt --dpi-desync=fake,udplen --dpi-desync-udplen-increment=2 --dpi-desync-fake-quic=quic_3.bin --dpi-desync-cutoff=n3 --dpi-desync-repeats=2 --new
"""
    }
}
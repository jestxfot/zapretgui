"""
Embedded fallback for Zapret categories.

If `{INDEXJSON_FOLDER}/strategies/builtin/categories.txt` is missing or corrupted,
the app falls back to this built-in copy.

NOTE: This file is generated from the upstream Zapret categories.txt.
"""

DEFAULT_CATEGORIES_TXT = """\
# Categories configuration
version = 1.0
description = Встроенные категории сервисов для обхода блокировок

[youtube]
full_name = YouTube TCP
description = YouTube через TCP протокол (порты 80, 443)
tooltip = 🎬 YouTube через TCP протокол (порты 80, 443)\nОбходит блокировку обычного YouTube трафика через стандартные веб-порты.\nТакже обходит Google Video трафик через TCP протокол (если вкладка GoogleVideo ВЫКЛЮЧЕНА!)\nTCP - это надежный протокол передачи данных, используется для загрузки веб-страниц и видео.\nРаботает с youtube.com и youtu.be.
color = #ff6666
default_strategy = multidisorder_legacy_midsld
ports = 80, 443
protocol = TCP
order = 1
command_order = 3
needs_new_separator = true
command_group = youtube
icon_name = fa5b.youtube
icon_color = #FF0000
base_filter_ipset = --filter-tcp=80,443 --ipset=ipset-youtube.txt
base_filter_hostlist = --filter-tcp=80,443 --hostlist=youtube.txt
strategy_type = tcp

[youtube_udp]
full_name = YouTube QUIC
description = YouTube через QUIC/UDP протокол (порт 443)
tooltip = 🎬 YouTube через QUIC/UDP протокол (порт 443)\nОбходит блокировку YouTube при использовании современного протокола QUIC (HTTP/3).\nQUIC работает поверх UDP и обеспечивает более быструю загрузку видео.\nМногие браузеры автоматически используют QUIC для YouTube.
color = #ff3c00
default_strategy = none
ports = 443
protocol = QUIC/UDP
order = 2
command_order = 4
needs_new_separator = true
command_group = youtube
icon_name = fa5b.youtube
icon_color = #FF0000
base_filter = --filter-udp=443 --ipset=ipset-youtube.txt
strategy_type = udp

[googlevideo_tcp]
full_name = GoogleVideo
description = YouTube видео с CDN серверов GoogleVideo
tooltip = 🎬 YouTube видео с CDN серверов GoogleVideo\nОбходит блокировку видеопотоков с серверов *.googlevideo.com (порт 443).\nЭто серверы доставки контента (CDN), откуда загружаются сами видеофайлы YouTube.\nНужно включать если видео не загружаются при работающем основном YouTube.
color = #ff9900
default_strategy = none
ports = 443
protocol = TCP
order = 3
command_order = 2
needs_new_separator = true
command_group = youtube
icon_name = fa5b.youtube
icon_color = #FF0000
base_filter = --filter-tcp=80,443 --ipset=ipset-googlevideo.txt
strategy_type = tcp

[discord_tcp]
full_name = Discord TCP
description = Discord мессенджер (порты 80, 443)
tooltip = 💬 Discord мессенджер (порты 80, 443)\nОбходит блокировку текстовых чатов и загрузки файлов в Discord.\nРаботает с основным трафиком Discord через TCP протокол.\nВключите если не работают текстовые сообщения и картинки.
color = #7289da
default_strategy = multidisorder_legacy_midsld
ports = 80, 443
protocol = TCP
order = 4
command_order = 5
needs_new_separator = true
command_group = discord
icon_name = fa5b.discord
icon_color = #7289DA
base_filter_ipset = --filter-tcp=80,443,1080,2053,2083,2087,2096,8443 --ipset=ipset-discord.txt
base_filter_hostlist = --filter-tcp=80,443,1080,2053,2083,2087,2096,8443 --hostlist=discord.txt
strategy_type = tcp

[discord_voice_udp]
full_name = Голосовые звонки/чаты
description = Голосовые звонки и демонстрация экрана для Discord, Telegram и WhatsApp (stun трафик)
tooltip = 🔊 Голосовые звонки и демонстрация экрана для Discord, Telegram и WhatsApp (stun трафик)
color = #9b59b6
default_strategy = fake_x6_stun_discord
ports = stun ports
protocol = UDP
order = 5
command_order = 6
needs_new_separator = true
command_group = discord
icon_name = fa5s.microphone
icon_color = #7289DA
base_filter = --filter-l7=stun,discord --payload=stun,discord_ip_discovery
strategy_type = discord_voice

[udp_discord]
full_name = Discord UDP
description = UDP протокол Discord мессенджер (порт 443)
tooltip = 💬 UDP для веб интерфейса дискорда, обычно не нужен но пусть будет.
color = #7289da
default_strategy = none
ports = 443
protocol = TCP
order = 6
command_order = 7
needs_new_separator = true
command_group = discord
icon_name = fa5b.discord
icon_color = #7289DA
base_filter = --filter-udp=443 --ipset=ipset-discord.txt
strategy_type = udp

[update_discord]
full_name = Update Discord
description = Обновления Discord мессенджер (порт 443)
tooltip = 💬 Пробивает прицельно отдельно апдейт дискорда. Полезно когда сайт discord.com грузится, а приложение Windows постоянно ищет обновления.
color = #7289da
default_strategy = none
ports = 443
protocol = TCP
order = 7
command_order = 4
needs_new_separator = true
command_group = discord
icon_name = fa5b.discord
icon_color = #7289DA
base_filter = --filter-tcp=443 --hostlist-domains=updates.discord.com
strategy_type = tcp

[telegram_tcp]
full_name = Telegram (TCP)
description = Telegram (веб версия и сайты)
tooltip = ✈ Telegram (веб версия и сайты)\nОбходит блокировку САЙТОВ и веб версии в Telegram. НЕ ПОДХОДИТ ДЛЯ ПРИЛОЖЕНИЯ!\nВключите если не работают сайты telegram.org и другие.
color = #9b59b6
default_strategy = none
ports = 80, 443
protocol = TCP
order = 8
command_order = 8
needs_new_separator = true
command_group = telegram
icon_name = fa5b.telegram
icon_color = #3CA7FF
base_filter_ipset = --filter-tcp=80,443 --ipset=ipset-telegram.txt
base_filter_hostlist = --filter-tcp=80,443 --hostlist=telegram.txt
strategy_type = tcp
strip_payload = true

[whatsapp_tcp]
full_name = ⛔ WhatsApp (БАН ПО IP!)
description = WhatsApp интерфейс (порты 80, 443)
tooltip = ЗАБЛОКИРОВАН ПО IP И БОЛЬШЕ НЕ ПРОБИВАЕТСЯ ЧЕРЕЗ ZAPRET!
color = #25D366
default_strategy = multidisorder_legacy_midsld
ports = 80, 443
protocol = TCP
order = 10
command_order = 10
needs_new_separator = true
command_group = messengers
icon_name = fa5b.whatsapp
icon_color = #25D366
base_filter_ipset = --filter-tcp=80,443 --ipset=ipset-whatsapp.txt
base_filter_hostlist = --filter-tcp=80,443 --hostlist=whatsapp.txt
strategy_type = tcp

[facebook_tcp]
full_name = Facebook
description = Facebook (порты 80, 443)
tooltip = 📘 Facebook (порты 80, 443)\nОбходит блокировку Facebook через стандартные веб-порты.\nПодходит для web и приложения.
color = #1877f2
default_strategy = multidisorder_legacy_midsld
ports = 80, 443
protocol = TCP
order = 11
command_order = 11
needs_new_separator = true
command_group = social
icon_name = fa5b.facebook
icon_color = #1877F2
base_filter_ipset = --filter-tcp=80,443 --ipset=ipset-facebook.txt
base_filter_hostlist = --filter-tcp=80,443 --hostlist=facebook.txt
strategy_type = tcp

[instagram_tcp]
full_name = Instagram
description = Instagram (порты 80, 443)
tooltip = 📸 Instagram (порты 80, 443)\nОбходит блокировку Instagram через стандартные веб-порты.\nПодходит для web и приложения.
color = #e1306c
default_strategy = multidisorder_legacy_midsld
ports = 80, 443
protocol = TCP
order = 12
command_order = 12
needs_new_separator = true
command_group = social
icon_name = fa5b.instagram
icon_color = #E1306C
base_filter_ipset = --filter-tcp=80,443 --ipset=ipset-instagram.txt
base_filter_hostlist = --filter-tcp=80,443 --hostlist=instagram.txt
strategy_type = tcp

[twitter_tcp]
full_name = Twitter/X
description = Twitter/X (порты 80, 443)
tooltip = 🐦 Twitter/X (порты 80, 443)\nОбходит блокировку Twitter/X через стандартные веб-порты.\nПодходит для web и приложения.
color = #1da1f2
default_strategy = multidisorder_legacy_midsld
ports = 80, 443
protocol = TCP
order = 13
command_order = 13
needs_new_separator = true
command_group = social
icon_name = fa5b.twitter
icon_color = #1DA1F2
base_filter_ipset = --filter-tcp=80,443 --ipset=ipset-twitter.txt
base_filter_hostlist = --filter-tcp=80,443 --hostlist=twitter.txt
strategy_type = tcp

[soundcloud_tcp]
full_name = SoundCloud
description = SoundCloud (порт 443)
tooltip = 🎵 SoundCloud (порт 443)\nОбходит блокировку SoundCloud через стандартные веб-порты.\nРаботает с основным трафиком SoundCloud через TCP протокол.
color = #ff5500
default_strategy = multidisorder_legacy_midsld
ports = 443
protocol = TCP
order = 14
command_order = 14
needs_new_separator = true
command_group = music
icon_name = fa5b.soundcloud
icon_color = #FF5500
base_filter_ipset = --filter-tcp=80,443 --ipset=ipset-soundcloud.txt
base_filter_hostlist = --filter-tcp=80,443 --hostlist=soundcloud.txt
strategy_type = tcp

[github_tcp]
full_name = GitHub
description = GitHub (порты 80, 443)
tooltip = 🐙 GitHub (порты 80, 443)\nОбходит блокировку GitHub через стандартные веб-порты.\nРаботает с основным трафиком GitHub через TCP протокол.
color = #808080
default_strategy = multidisorder_legacy_midsld
ports = 443
protocol = TCP
order = 15
command_order = 15
needs_new_separator = true
command_group = github
icon_name = fa5b.github
icon_color = #FCFCFC
base_filter_ipset = --filter-tcp=443 --ipset=ipset-github.txt
base_filter_hostlist = --filter-tcp=443 --hostlist=github.txt
strategy_type = tcp

[anydesk_tcp]
full_name = AnyDesk TCP
description = AnyDesk (порты 443, 6568)
tooltip = 🖥️ AnyDesk (порты 443, 6568)\nОбходит блокировку AnyDesk через основные порты.\nРаботает с трафиком удалённого доступа AnyDesk через TCP протокол.
color = #EF443B
default_strategy = none
ports = 443, 6568
protocol = TCP
order = 16
command_order = 16
needs_new_separator = true
command_group = remote
icon_name = fa5s.desktop
icon_color = #EF443B
base_filter = --filter-tcp=80,443,6568 --ipset=ipset-anydesk.txt
strategy_type = tcp
strip_payload = true

[anydesk_udp]
full_name = AnyDesk UDP
description = AnyDesk (порты 443, 6568)
tooltip = 🖥️ AnyDesk (порты 443, 6568)\nОбходит блокировку AnyDesk через основные порты.\nРаботает с трафиком удалённого доступа AnyDesk через TCP протокол.
color = #EF443B
default_strategy = none
ports = 443, 6568
protocol = UDP
order = 16
command_order = 16
needs_new_separator = true
command_group = remote
icon_name = fa5s.desktop
icon_color = #EF443B
base_filter = --filter-udp=80,443,6568,50000-51000 --ipset=ipset-anydesk.txt
strategy_type = udp
strip_payload = true
requires_all_ports = true

[rutracker_tcp]
full_name = Rutracker.org
description = Rutracker (порты 80, 443)
tooltip = 🛠 Rutracker (порты 80, 443)\nОбходит блокировку торрент-трекера Rutracker через стандартные веб-порты.\nРаботает с основным трафиком Rutracker через TCP протокол.
color = #6c5ce7
default_strategy = multidisorder_legacy_midsld
ports = 80, 443
protocol = TCP
order = 17
command_order = 17
needs_new_separator = true
command_group = trackers
icon_name = fa5s.download
icon_color = #457AEB
base_filter_ipset = --filter-tcp=80,443 --ipset=ipset-rutracker.txt
base_filter_hostlist = --filter-tcp=80,443 --hostlist=rutracker.txt
strategy_type = tcp

[rutor_tcp]
full_name = Rutor.info (.is)
description = Rutor.info (порты 80, 443)
tooltip = 🛠 Rutor.info (порты 80, 443)\nОбходит блокировку торрент-трекера Rutor.info через стандартные веб-порты.\nРаботает с основным трафиком Rutor.info через TCP протокол.
color = #6c5ce7
default_strategy = multisplit_split_pos_1
ports = 80, 443
protocol = TCP
order = 18
command_order = 18
needs_new_separator = true
command_group = trackers
icon_name = fa5s.download
icon_color = #457AEB
base_filter = --filter-tcp=80,443 --hostlist=rutor.txt
strategy_type = tcp

[ntcparty_tcp]
full_name = NtcParty
description = NtcParty (порты 80, 443)
tooltip = 🛠 NtcParty (порты 80, 443)\nОбходит блокировку технического форума NtcParty отдельно от основных хостлистов.\nРаботает с основным трафиком NtcParty через TCP протокол.
color = #d9d8e0
default_strategy = multidisorder_legacy_midsld
ports = 80, 443
protocol = TCP
order = 19
command_order = 19
needs_new_separator = true
command_group = trackers
icon_name = fa5s.tools
icon_color = #6C5CE7
base_filter = --filter-tcp=80,443 --ipset-ip=130.255.77.28
strategy_type = tcp

[twitch_tcp]
full_name = Twitch
description = Twitch стриминг (порты 80, 443)
tooltip = 🎙 Twitch стриминг (порты 80, 443)\nОбходит блокировку Twitch стримов через стандартные веб-порты.\nРаботает с основным трафиком Twitch через TCP протокол.\nВключите если не работают стримы на Twitch.
color = #9146ff
default_strategy = none
ports = 80, 443
protocol = TCP
order = 20
command_order = 20
needs_new_separator = true
command_group = streaming
icon_name = fa5b.twitch
icon_color = #9146FF
base_filter_ipset = --filter-tcp=443 --ipset=ipset-twitch.txt
base_filter_hostlist = --filter-tcp=443 --hostlist=twitch.txt
strategy_type = tcp

[speedtest_tcp]
full_name = Speedtest
description = Speedtest (порт 443)
tooltip = 🌐 Speedtest (порт 443)\nОбходит блокировку Speedtest через стандартные веб-порты.\nРаботает с основным трафиком Speedtest через TCP протокол.
color = #9146ff
default_strategy = other_seqovl
ports = 443
protocol = TCP
order = 21
command_order = 21
needs_new_separator = true
command_group = hostlists
icon_name = fa5s.tachometer-alt
icon_color = #4671FF
base_filter = --filter-tcp=443,8080 --hostlist=speedtest.txt
strategy_type = tcp

[steam_tcp]
full_name = Steam
description = Steam (порты 80, 443)
tooltip = 🎮 Steam (порты 80, 443)\nОбходит блокировку Steam через стандартные веб-порты.\nРаботает с основным трафиком Steam через TCP протокол.
color = #9146ff
default_strategy = multidisorder_legacy_midsld
ports = 80, 443
protocol = TCP
order = 22
command_order = 22
needs_new_separator = true
command_group = hostlists
icon_name = fa5b.steam
icon_color = #7390F0
base_filter_ipset = --filter-tcp=80,443 --ipset=ipset-steam.txt
base_filter_hostlist = --filter-tcp=80,443 --hostlist=steam.txt
strategy_type = tcp

[itch_tcp]
full_name = Itch.io TCP
description = Itch.io (порты 80, 443)
tooltip = 🎮 Itch.io (порты 80, 443)\nОбходит блокировку Itch.io через стандартные веб-порты.\nРаботает с основным трафиком Itch.io через TCP протокол.
color = #ff4757
default_strategy = disorder2_badseq_tls_google
ports = 443
protocol = TCP
order = 23
command_order = 23
needs_new_separator = true
command_group = games
icon_name = fa5b.itch-io
icon_color = #FA5C5C
base_filter = --filter-tcp=443 --hostlist=itch.txt
strategy_type = tcp

[google_tcp]
full_name = Google TCP
description = Google TCP (порты 443, 853)
tooltip = 🌐 Google TCP (порты 443, 853)\nОбходит блокировки основных сайтов и сервисов Google
color = #4285F4
default_strategy = none
ports = 80, 443
protocol = TCP
order = 24
command_order = 24
needs_new_separator = true
command_group = hostlists
icon_name = fa5b.google
icon_color = #4285F4
base_filter = --filter-tcp=80,443 --hostlist=google.txt
strategy_type = tcp

[amazon_tcp]
full_name = Amazon TCP
description = Amazon TCP (порты 80, 443-65535)
tooltip = 📦 Amazon TCP (порты 80, 443-65535)\nОбходит блокировку сервисов Amazon (AWS, Prime, Twitch и др.) через TCP.\nРаботает по хостлисту amazon.txt.
color = #FF9900
default_strategy = none
ports = 80, 443-65535
protocol = TCP
order = 25
command_order = 25
needs_new_separator = true
command_group = hostlists
icon_name = fa5b.amazon
icon_color = #FF9900
base_filter = --filter-tcp=80,443-65535 --hostlist=amazon.txt
strategy_type = tcp
requires_all_ports = true

[amazon_udp]
full_name = Amazon UDP
description = Amazon UDP (порты 443-65535)
tooltip = 📦 Amazon UDP (порты 443-65535)\nОбходит блокировку сервисов Amazon (AWS, Prime, игровые сервера) через UDP.\nРаботает по IP-диапазонам Amazon AWS.
color = #FF9900
default_strategy = none
ports = 443-65535
protocol = UDP
order = 26
command_order = 26
needs_new_separator = true
command_group = ipsets
icon_name = fa5b.amazon
icon_color = #FF9900
base_filter = --filter-udp=443-65535 --ipset=ipset-amazon.txt
strategy_type = udp
requires_all_ports = true

[roblox_tcp]
full_name = Roblox TCP
description = Roblox TCP (порты 80, 443)
tooltip = 🎮 Roblox TCP (порты 80, 443)\nОбходит блокировку Roblox через стандартные веб-порты.\nРаботает с основным трафиком Roblox через TCP протокол.
color = #4285F4
default_strategy = none
ports = 80, 443
protocol = TCP
order = 27
command_order = 27
needs_new_separator = true
command_group = games
icon_name = fa5s.gamepad
icon_color = #7390F0
base_filter_ipset = --filter-tcp=80,443 --ipset=ipset-roblox.txt
base_filter_hostlist = --filter-tcp=80,443 --hostlist=roblox.txt
strategy_type = tcp

[roblox_udp]
full_name = Roblox UDP
description = Roblox UDP (порты 49152-65535)
tooltip = 🎮 Roblox UDP (порты 49152-65535)\nОбходит блокировку Roblox через игровые порты.\nРаботает с основным трафиком Roblox через UDP протокол.
color = #4285F4
default_strategy = none
ports = 49152-65535
protocol = UDP
order = 28
command_order = 28
needs_new_separator = true
command_group = games
icon_name = fa5s.gamepad
icon_color = #7390F0
base_filter = --filter-udp=443,49152-65535 --ipset=ipset-roblox.txt
strategy_type = udp

[phasmophobia_udp]
full_name = Phasmophobia UDP
description = Phasmophobia UDP (порты 5056, 27002)
tooltip = 🎮 Phasmophobia UDP (порты 5056, 27002)\nОбходит блокировку Phasmophobia через игровые порты.\nРаботает с основным трафиком Phasmophobia через UDP протокол.
color = #ff4757
default_strategy = none
ports = 5056, 27002
protocol = UDP
order = 29
command_order = 29
needs_new_separator = true
command_group = games
icon_name = fa5s.ghost
icon_color = #8B4789
base_filter = --filter-udp=5056,27002
strategy_type = udp
requires_all_ports = true

[battlefield_6_udp]
full_name = Battlefield 6 UDP
description = Battlefield 6 UDP (порты 21000-21999)
tooltip = 🎮 Battlefield UDP (порты 21000-21999)\nОбходит блокировку Battlefield через игровые порты.\nРаботает с основным трафиком Battlefield через UDP протокол.
color = #ff4757
default_strategy = none
ports = 21000-21999
protocol = UDP
order = 30
command_order = 30
needs_new_separator = true
command_group = games
icon_name = fa5s.fighter-jet
icon_color = #8B4789
base_filter = --filter-udp=21000-21999
strategy_type = udp
requires_all_ports = true

[warp_tcp]
full_name = Warp TCP
description = Warp TCP (порты 443, 853)
tooltip = 🎮 Warp TCP (порты 443, 853)\nОбходит блокировку Warp через стандартные веб-порты.\nРаботает с основным трафиком Warp через UDP протокол.
color = #ff4757
default_strategy = none
ports = 443, 853
protocol = TCP
order = 31
command_order = 31
needs_new_separator = true
command_group = hostlists
icon_name = fa5b.cloudflare
icon_color = #FD7A3E
base_filter = --filter-tcp=443,853 --ipset=ipset-warp.txt
strategy_type = tcp
strip_payload = true
requires_all_ports = true

[claude_tcp]
full_name = Claude AI TCP
description = Claude TCP (порты 443, 853)
tooltip = Claude TCP (порты 443, 853)\nОбходит блокировку Claude через стандартные веб-порты.\nРаботает с основным трафиком Claude через TCP протокол.
color = #ff4757
default_strategy = none
ports = 443
protocol = TCP
order = 32
command_order = 32
needs_new_separator = true
command_group = hostlists
icon_name = fa5s.brain
icon_color = #DA6B46
base_filter_ipset = --filter-tcp=80,443 --ipset=ipset-claude.txt
base_filter_hostlist = --filter-tcp=80,443 --hostlist=claude.txt
strategy_type = tcp
strip_payload = true
requires_all_ports = false

[other]
full_name = Hostlist (HTTPS)
description = Заблокированные сайты из списка (порты 80, 443)
tooltip = 🌐 Заблокированные сайты из списка (порты 80, 443)\nОбходит блокировку сайтов из файла other.txt через TCP.\nВключает сотни популярных заблокированных сайтов и сервисов.\nМожно редактировать список сайтов во вкладке Hostlist.
color = #66ff66
default_strategy = none
ports = 80, 443
protocol = TCP
order = 33
command_order = 33
needs_new_separator = true
command_group = hostlists
icon_name = fa5b.chrome
icon_color = #2696F1
base_filter_ipset = --filter-tcp=443 --ipset=ipset-censorliber.txt
base_filter_hostlist = --filter-tcp=443 --hostlist-exclude=netrogat.txt --hostlist=other.txt --hostlist=russia-blacklist.txt
strategy_type = tcp
strip_payload = true

[porn_http]
full_name = Porn (HTTP)
description = Порно-сайты через HTTP (порт 80)
tooltip = 🔞 Порно-сайты через HTTP (порт 80)\nОбходит блокировку порно-сайтов работающих по HTTP протоколу.\nМногие порно-сайты используют HTTP вместо HTTPS.\nМожно редактировать список сайтов в ipset-porn.txt.
color = #ff69b4
default_strategy = http_aggressive
ports = 80
protocol = TCP
order = 34
command_order = 1
needs_new_separator = true
command_group = ipsets
icon_name = fa5s.ban
icon_color = #FF69B4
base_filter = --filter-tcp=80,443 --ipset=ipset-porn.txt
strategy_type = http80
strip_payload = true

[tankix_http]
full_name = TankiX (HTTP)
description = TankiX через HTTP (порт 80)
tooltip = TankiX через HTTP (порт 80)\nОбходит блокировку TankiX работающих по HTTP протоколу.\nМногие TankiX используют HTTP вместо HTTPS.\nМожно редактировать список сайтов в ipset-porn.txt.
color = #ff69b4
default_strategy = none
ports = 80
protocol = TCP
order = 35
command_order = 34
needs_new_separator = true
command_group = ipsets
icon_name = fa5s.gamepad
icon_color = #FF69B4
base_filter = --filter-tcp=80,443 --ipset=ipset-tankix.txt
strategy_type = http80
strip_payload = true

[hostlist_80port]
full_name = Hostlist (HTTP)
description = Заблокированные сайты из списка (порт 80)
tooltip = 🌐 Заблокированные сайты из списка (порт 80)\nОбходит блокировку сайтов из файла other.txt через HTTP (порт 80).\nПолезно если провайдер блокирует только HTTP трафик, а HTTPS оставляет открытым.\nМожно редактировать список сайтов во вкладке Hostlist.
color = #00ffcc
default_strategy = none
ports = 80
protocol = TCP
order = 36
command_order = 37
needs_new_separator = true
command_group = hostlists
icon_name = fa5b.chrome
icon_color = #2696F1
base_filter = --filter-tcp=80 --ipset=ipset-all.txt --ipset=ipset-base.txt --ipset=cloudflare-ipset.txt --ipset=ipset-cloudflare1.txt --ipset=ipset-cloudflare.txt
strategy_type = http80
strip_payload = true

[ipset_tcp_cloudflare]
full_name = IPset TCP (CloudFlare)
description = Сервера CloudFlare (все порты)
tooltip = ☁️ Используйте если нужно разблокировать сервера этого ресурса
color = #ffa500
default_strategy = none
ports = all ports
protocol = TCP
order = 37
command_order = 36
needs_new_separator = true
command_group = ipsets
icon_name = fa5b.cloudflare
icon_color = #FFA500
base_filter = --filter-tcp=80,443-65535 --ipset=cloudflare-ipset.txt --ipset=ipset-cloudflare1.txt --ipset=ipset-cloudflare.txt
strategy_type = tcp
requires_all_ports = true

[ipset_zapretkvn]
full_name = ZapretKVN
description = Сервера ZapretKVN (все порты)
tooltip = 🐋 Сервера ZapretKVN (все порты)\nОбходит блокировку сервисов ZapretKVN через TCP.\nРаботает когда провайдер блокирует не домены, а конкретные IP.\nПолезно для сервисов ZapretKVN.\n📝 Стратегии применяются ко ВСЕМУ трафику (без фильтра payload)
color = #6fa8dc
default_strategy = none
ports = all ports
protocol = TCP
order = 38
command_order = 37
needs_new_separator = true
command_group = ipsets
icon_name = fa5b.docker
icon_color = #6fa8dc
base_filter = --ipset=ipset-zapretkvn.txt
strategy_type = tcp
requires_all_ports = true
strip_payload = true

[ipset]
full_name = IPset TCP (Games)
description = Блокировка по IP адресам (все порты)
tooltip = 🔢 Блокировка по IP адресам (все порты)\nОбходит блокировку сервисов по их IP адресам через TCP.\nРаботает когда провайдер блокирует не домены, а конкретные IP.\nПолезно для сервисов с фиксированными IP адресами.
color = #ffa500
default_strategy = none
ports = all ports
protocol = TCP
order = 39
command_order = 38
needs_new_separator = true
command_group = ipsets
icon_name = fa5s.network-wired
icon_color = #FFA500
base_filter = --filter-tcp=80,443-65535 --ipset=russia-youtube-rtmps.txt --ipset=ipset-all.txt --ipset=ipset-base.txt --ipset=ipset-discord.txt --ipset-exclude=ipset-dns.txt
strategy_type = tcp
requires_all_ports = true
strip_payload = true

[ipset_all]
full_name = ALL TCP
description = Позволяет включить Zapret для всех IP-адресов (без ipset или hostlist)
tooltip = 🔢 Блокировка по IP адресам (все порты)\nОбходит блокировку сервисов по их IP адресам через TCP.\nРаботает когда провайдер блокирует не домены, а конкретные IP.\nПолезно для сервисов с фиксированными IP адресами.
color = #ffa500
default_strategy = none
ports = all ports
protocol = TCP
order = 40
command_order = 39
needs_new_separator = true
command_group = ipsets
icon_name = fa5s.network-wired
icon_color = #FFA500
base_filter = --filter-tcp=80,443-65535 --ipset-exclude=ipset-ru.txt
strategy_type = tcp
requires_all_ports = true
strip_payload = true

[ovh_udp]
full_name = OVH UDP
description = OVH UDP (игровые сервера провайдера ОВХ)
tooltip = 🛡 OVH UDP (игровые сервера провайдера ОВХ)\nОбходит блокировку сервисов по их IP адресам через UDP.\nРаботает когда провайдер блокирует не домены, а конкретные IP.\nПолезно для сервисов с фиксированными IP адресами.
color = #e69f08
default_strategy = none
ports = all ports
protocol = UDP
order = 41
command_order = 40
needs_new_separator = true
command_group = ipsets
icon_name = fa5s.gamepad
icon_color = #F1BB25
base_filter = --filter-udp=* --ipset=ipset-ovh.txt
strategy_type = udp
requires_all_ports = true

[ipset_udp]
full_name = IPset UDP (Games)
description = Блокировка по IP адресам (UDP для игр)
tooltip = 🔢 Блокировка по IP адресам (UDP для игр)\nОбходит блокировку сервисов по их IP адресам через UDP.\nРаботает когда провайдер блокирует не домены, а конкретные IP.\nПолезно для сервисов с фиксированными IP адресами.
color = #006eff
default_strategy = none
ports = all ports
protocol = UDP
order = 42
command_order = 41
needs_new_separator = false
command_group = ipsets
icon_name = fa5s.gamepad
icon_color = #D49B00
base_filter = --filter-udp=* --ipset=ipset-all.txt --ipset=ipset-base.txt --ipset=cloudflare-ipset.txt --ipset=ipset-cloudflare1.txt --ipset=ipset-cloudflare.txt --ipset-exclude=ipset-dns.txt
strategy_type = udp
requires_all_ports = true

[ipset_udp_all]
full_name = ALL UDP
description = Позволяет включить Zapret для всех IP-адресов (без ipset или hostlist)
tooltip = 🔢 Блокировка по IP адресам (UDP для игр)\nОбходит блокировку сервисов по их IP адресам через UDP.\nРаботает когда провайдер блокирует не домены, а конкретные IP.\nПолезно для сервисов с фиксированными IP адресами.
color = #006eff
default_strategy = none
ports = all ports
protocol = UDP
order = 43
command_order = 42
needs_new_separator = false
command_group = ipsets
icon_name = fa5s.gamepad
icon_color = #D49B00
base_filter = --filter-udp=80,443-65535 --ipset-exclude=ipset-ru.txt
strategy_type = udp
requires_all_ports = true
"""

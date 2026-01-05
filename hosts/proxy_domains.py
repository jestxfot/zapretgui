# hosts/proxy_domains.py
# Домены разбиты по сервисам для удобного быстрого выбора

# ═══════════════════════════════════════════════════════════════
# СЕРВИСЫ - каждый сервис содержит список своих доменов с IP
# ═══════════════════════════════════════════════════════════════

SERVICES = {
    "Discord TCP": {
        "discord.com": "23.227.38.74",
        "gateway.discord.gg": "23.227.38.74",
        "updates.discord.com": "23.227.38.74",
        "cdn.discordapp.com": "23.227.38.74",
        "status.discord.com": "23.227.38.74",
        "cdn.prod.website-files.com": "23.227.38.74",
    },
    "YouTube TCP": {
        "www.youtube.com": "142.250.117.93",
    },
    "GitHub TCP": {
        "github.com": "140.82.114.3",
        "github.githubassets.com": "185.199.110.154",
        "camo.githubassets.com": "185.199.110.133",
    },
    "Discord Voice": {
        "finland10000.discord.media": "104.25.158.178",
        "finland10001.discord.media": "104.25.158.178",
        "finland10002.discord.media": "104.25.158.178",
        "finland10003.discord.media": "104.25.158.178",
        "finland10004.discord.media": "104.25.158.178",
        "finland10005.discord.media": "104.25.158.178",
        "finland10006.discord.media": "104.25.158.178",
        "finland10007.discord.media": "104.25.158.178",
        "finland10008.discord.media": "104.25.158.178",
        "finland10009.discord.media": "104.25.158.178",
        "finland10010.discord.media": "104.25.158.178",
        "finland10011.discord.media": "104.25.158.178",
        "finland10012.discord.media": "104.25.158.178",
        "finland10013.discord.media": "104.25.158.178",
        "finland10014.discord.media": "104.25.158.178",
        "finland10015.discord.media": "104.25.158.178",
        "finland10016.discord.media": "104.25.158.178",
        "finland10017.discord.media": "104.25.158.178",
        "finland10018.discord.media": "104.25.158.178",
        "finland10019.discord.media": "104.25.158.178",
        "finland10020.discord.media": "104.25.158.178",
        "finland10021.discord.media": "104.25.158.178",
        "finland10022.discord.media": "104.25.158.178",
        "finland10023.discord.media": "104.25.158.178",
        "finland10024.discord.media": "104.25.158.178",
        "finland10025.discord.media": "104.25.158.178",
        "finland10026.discord.media": "104.25.158.178",
        "finland10027.discord.media": "104.25.158.178",
        "finland10028.discord.media": "104.25.158.178",
        "finland10029.discord.media": "104.25.158.178",
        "finland10030.discord.media": "104.25.158.178",
        "finland10031.discord.media": "104.25.158.178",
        "finland10032.discord.media": "104.25.158.178",
        "finland10033.discord.media": "104.25.158.178",
        "finland10034.discord.media": "104.25.158.178",
        "finland10035.discord.media": "104.25.158.178",
        "finland10036.discord.media": "104.25.158.178",
        "finland10037.discord.media": "104.25.158.178",
        "finland10038.discord.media": "104.25.158.178",
        "finland10039.discord.media": "104.25.158.178",
        "finland10040.discord.media": "104.25.158.178",
        "finland10041.discord.media": "104.25.158.178",
        "finland10042.discord.media": "104.25.158.178",
        "finland10043.discord.media": "104.25.158.178",
        "finland10044.discord.media": "104.25.158.178",
        "finland10045.discord.media": "104.25.158.178",
        "finland10046.discord.media": "104.25.158.178",
        "finland10047.discord.media": "104.25.158.178",
        "finland10048.discord.media": "104.25.158.178",
        "finland10049.discord.media": "104.25.158.178",
        "finland10050.discord.media": "104.25.158.178",
        "finland10051.discord.media": "104.25.158.178",
        "finland10052.discord.media": "104.25.158.178",
        "finland10053.discord.media": "104.25.158.178",
        "finland10054.discord.media": "104.25.158.178",
        "finland10055.discord.media": "104.25.158.178",
        "finland10056.discord.media": "104.25.158.178",
        "finland10057.discord.media": "104.25.158.178",
        "finland10058.discord.media": "104.25.158.178",
        "finland10059.discord.media": "104.25.158.178",
        "finland10060.discord.media": "104.25.158.178",
        "finland10061.discord.media": "104.25.158.178",
        "finland10062.discord.media": "104.25.158.178",
        "finland10063.discord.media": "104.25.158.178",
        "finland10064.discord.media": "104.25.158.178",
        "finland10065.discord.media": "104.25.158.178",
        "finland10066.discord.media": "104.25.158.178",
        "finland10067.discord.media": "104.25.158.178",
        "finland10068.discord.media": "104.25.158.178",
        "finland10069.discord.media": "104.25.158.178",
        "finland10070.discord.media": "104.25.158.178",
        "finland10071.discord.media": "104.25.158.178",
        "finland10072.discord.media": "104.25.158.178",
        "finland10073.discord.media": "104.25.158.178",
        "finland10074.discord.media": "104.25.158.178",
        "finland10075.discord.media": "104.25.158.178",
        "finland10076.discord.media": "104.25.158.178",
        "finland10077.discord.media": "104.25.158.178",
        "finland10078.discord.media": "104.25.158.178",
        "finland10079.discord.media": "104.25.158.178",
        "finland10080.discord.media": "104.25.158.178",
        "finland10081.discord.media": "104.25.158.178",
        "finland10082.discord.media": "104.25.158.178",
        "finland10083.discord.media": "104.25.158.178",
        "finland10084.discord.media": "104.25.158.178",
        "finland10085.discord.media": "104.25.158.178",
        "finland10086.discord.media": "104.25.158.178",
        "finland10087.discord.media": "104.25.158.178",
        "finland10088.discord.media": "104.25.158.178",
        "finland10089.discord.media": "104.25.158.178",
        "finland10090.discord.media": "104.25.158.178",
        "finland10091.discord.media": "104.25.158.178",
        "finland10092.discord.media": "104.25.158.178",
        "finland10093.discord.media": "104.25.158.178",
        "finland10094.discord.media": "104.25.158.178",
        "finland10095.discord.media": "104.25.158.178",
        "finland10096.discord.media": "104.25.158.178",
        "finland10097.discord.media": "104.25.158.178",
        "finland10098.discord.media": "104.25.158.178",
        "finland10099.discord.media": "104.25.158.178",
        "finland10100.discord.media": "104.25.158.178",
        "finland10101.discord.media": "104.25.158.178",
        "finland10102.discord.media": "104.25.158.178",
        "finland10103.discord.media": "104.25.158.178",
        "finland10104.discord.media": "104.25.158.178",
        "finland10105.discord.media": "104.25.158.178",
        "finland10106.discord.media": "104.25.158.178",
        "finland10107.discord.media": "104.25.158.178",
        "finland10108.discord.media": "104.25.158.178",
        "finland10109.discord.media": "104.25.158.178",
        "finland10110.discord.media": "104.25.158.178",
        "finland10111.discord.media": "104.25.158.178",
        "finland10112.discord.media": "104.25.158.178",
        "finland10113.discord.media": "104.25.158.178",
        "finland10114.discord.media": "104.25.158.178",
        "finland10115.discord.media": "104.25.158.178",
        "finland10116.discord.media": "104.25.158.178",
        "finland10117.discord.media": "104.25.158.178",
        "finland10118.discord.media": "104.25.158.178",
        "finland10119.discord.media": "104.25.158.178",
        "finland10120.discord.media": "104.25.158.178",
        "finland10121.discord.media": "104.25.158.178",
        "finland10122.discord.media": "104.25.158.178",
        "finland10123.discord.media": "104.25.158.178",
        "finland10124.discord.media": "104.25.158.178",
        "finland10125.discord.media": "104.25.158.178",
        "finland10126.discord.media": "104.25.158.178",
        "finland10127.discord.media": "104.25.158.178",
        "finland10128.discord.media": "104.25.158.178",
        "finland10129.discord.media": "104.25.158.178",
        "finland10130.discord.media": "104.25.158.178",
        "finland10131.discord.media": "104.25.158.178",
        "finland10132.discord.media": "104.25.158.178",
        "finland10133.discord.media": "104.25.158.178",
        "finland10134.discord.media": "104.25.158.178",
        "finland10135.discord.media": "104.25.158.178",
        "finland10136.discord.media": "104.25.158.178",
        "finland10137.discord.media": "104.25.158.178",
        "finland10138.discord.media": "104.25.158.178",
        "finland10139.discord.media": "104.25.158.178",
        "finland10140.discord.media": "104.25.158.178",
        "finland10141.discord.media": "104.25.158.178",
        "finland10142.discord.media": "104.25.158.178",
        "finland10143.discord.media": "104.25.158.178",
        "finland10144.discord.media": "104.25.158.178",
        "finland10145.discord.media": "104.25.158.178",
        "finland10146.discord.media": "104.25.158.178",
        "finland10147.discord.media": "104.25.158.178",
        "finland10148.discord.media": "104.25.158.178",
        "finland10149.discord.media": "104.25.158.178",
        "finland10150.discord.media": "104.25.158.178",
        "finland10151.discord.media": "104.25.158.178",
        "finland10152.discord.media": "104.25.158.178",
        "finland10153.discord.media": "104.25.158.178",
        "finland10154.discord.media": "104.25.158.178",
        "finland10155.discord.media": "104.25.158.178",
        "finland10156.discord.media": "104.25.158.178",
        "finland10157.discord.media": "104.25.158.178",
        "finland10158.discord.media": "104.25.158.178",
        "finland10159.discord.media": "104.25.158.178",
        "finland10160.discord.media": "104.25.158.178",
        "finland10161.discord.media": "104.25.158.178",
        "finland10162.discord.media": "104.25.158.178",
        "finland10163.discord.media": "104.25.158.178",
        "finland10164.discord.media": "104.25.158.178",
        "finland10165.discord.media": "104.25.158.178",
        "finland10166.discord.media": "104.25.158.178",
        "finland10167.discord.media": "104.25.158.178",
        "finland10168.discord.media": "104.25.158.178",
        "finland10169.discord.media": "104.25.158.178",
        "finland10170.discord.media": "104.25.158.178",
        "finland10171.discord.media": "104.25.158.178",
        "finland10172.discord.media": "104.25.158.178",
        "finland10173.discord.media": "104.25.158.178",
        "finland10174.discord.media": "104.25.158.178",
        "finland10175.discord.media": "104.25.158.178",
        "finland10176.discord.media": "104.25.158.178",
        "finland10177.discord.media": "104.25.158.178",
        "finland10178.discord.media": "104.25.158.178",
        "finland10179.discord.media": "104.25.158.178",
        "finland10180.discord.media": "104.25.158.178",
        "finland10181.discord.media": "104.25.158.178",
        "finland10182.discord.media": "104.25.158.178",
        "finland10183.discord.media": "104.25.158.178",
        "finland10184.discord.media": "104.25.158.178",
        "finland10185.discord.media": "104.25.158.178",
        "finland10186.discord.media": "104.25.158.178",
        "finland10187.discord.media": "104.25.158.178",
        "finland10188.discord.media": "104.25.158.178",
        "finland10189.discord.media": "104.25.158.178",
        "finland10190.discord.media": "104.25.158.178",
        "finland10191.discord.media": "104.25.158.178",
        "finland10192.discord.media": "104.25.158.178",
        "finland10193.discord.media": "104.25.158.178",
        "finland10194.discord.media": "104.25.158.178",
        "finland10195.discord.media": "104.25.158.178",
        "finland10196.discord.media": "104.25.158.178",
        "finland10197.discord.media": "104.25.158.178",
        "finland10198.discord.media": "104.25.158.178",
        "finland10199.discord.media": "104.25.158.178"
    },
    "ChatGPT": {
        "chatgpt.com": "82.22.36.11",
        "ab.chatgpt.com": "82.22.36.11",
        "auth.openai.com": "82.22.36.11",
        "auth0.openai.com": "82.22.36.11",
        "platform.openai.com": "82.22.36.11",
        "cdn.oaistatic.com": "82.22.36.11",
        "files.oaiusercontent.com": "82.22.36.11",
        "cdn.auth0.com": "82.22.36.11",
        "tcr9i.chat.openai.com": "82.22.36.11",
        "webrtc.chatgpt.com": "82.22.36.11",
        "android.chat.openai.com": "82.22.36.11",
        "api.openai.com": "82.22.36.11",
        "sora.com": "82.22.36.11",
        "sora.chatgpt.com": "82.22.36.11",
        "videos.openai.com": "82.22.36.11",
        "us.posthog.com": "82.22.36.11",
    },
    
    "Gemini": {
        "gemini.google.com": "82.22.36.11",
        "alkalimakersuite-pa.clients6.google.com": "82.22.36.11",
        "aisandbox-pa.googleapis.com": "82.22.36.11",
        "webchannel-alkalimakersuite-pa.clients6.google.com": "82.22.36.11",
        "proactivebackend-pa.googleapis.com": "82.22.36.11",
        "o.pki.goog": "82.22.36.11",
        "labs.google": "82.22.36.11",
        "notebooklm.google": "82.22.36.11",
        "notebooklm.google.com": "82.22.36.11",
    },
    
    "Claude": {
        "claude.ai": "82.22.36.11",
        "api.claude.ai": "82.22.36.11",
        "claude.com": "82.22.36.11",
        "anthropic.com": "82.22.36.11",
        "www.anthropic.com": "82.22.36.11",
        "api.anthropic.com": "82.22.36.11",
        "console.anthropic.com": "82.22.36.11",
        "a-api.anthropic.com": "82.22.36.11",
        "s-cdn.anthropic.com": "82.22.36.11",
        "nexus-websocket-a.intercom.io": "82.22.36.11",
    },
    
    "Copilot": {
        "copilot.microsoft.com": "82.22.36.11",
        "sydney.bing.com": "82.22.36.11",
        "edgeservices.bing.com": "82.22.36.11",
        "rewards.bing.com": "82.22.36.11",
        "xsts.auth.xboxlive.com": "82.22.36.11",
    },
    
    "Grok": {
        "grok.com": "82.22.36.11",
        "assets.grok.com": "82.22.36.11",
        "accounts.x.ai": "82.22.36.11",
    },
    
    "Instagram": {
        "www.instagram.com": "157.240.225.174",
        "instagram.com": "157.240.225.174",
        "scontent.cdninstagram.com": "157.240.224.63",
        "scontent-hel3-1.cdninstagram.com": "157.240.224.63",
        "static.cdninstagram.com": "31.13.72.53",
        "b.i.instagram.com": "157.240.245.174",
    },
    
    "Facebook": {
        "facebook.com": "31.13.72.36",
        "www.facebook.com": "31.13.72.36",
        "static.xx.fbcdn.net": "31.13.72.12",
        "external-hel3-1.xx.fbcdn.net": "31.13.72.12",
        "scontent-hel3-1.xx.fbcdn.net": "31.13.72.12",
        "z-p42-chat-e2ee-ig.facebook.com": "157.240.245.174",
    },
    
    "Threads": {
        "threads.com": "157.240.224.63",
        "www.threads.com": "157.240.224.63",
    },
    
    "Spotify": {
        "api.spotify.com": "82.22.36.11",
        "xpui.app.spotify.com": "82.22.36.11",
        "appresolve.spotify.com": "82.22.36.11",
        "login5.spotify.com": "82.22.36.11",
        "gew1-spclient.spotify.com": "82.22.36.11",
        "gew1-dealer.spotify.com": "82.22.36.11",
        "spclient.wg.spotify.com": "82.22.36.11",
        "api-partner.spotify.com": "82.22.36.11",
        "aet.spotify.com": "82.22.36.11",
        "www.spotify.com": "82.22.36.11",
        "accounts.spotify.com": "82.22.36.11",
        "spotifycdn.com": "82.22.36.11",
        "open-exp.spotifycdn.com": "82.22.36.11",
        "www-growth.scdn.co": "82.22.36.11",
        "login.app.spotify.com": "82.22.36.11",
        "accounts.scdn.co": "82.22.36.11",
        "ap-gew1.spotify.com": "82.22.36.11",
    },
    
    "Notion": {
        "www.notion.so": "82.22.36.11",
        "notion.so": "82.22.36.11",
        "calendar.notion.so": "82.22.36.11",
    },
    
    "Twitch": {
        "usher.ttvnw.net": "82.22.36.11",
        "gql.twitch.tv": "82.22.36.11",
    },
    
    "DeepL": {
        "deepl.com": "82.22.36.11",
        "www.deepl.com": "82.22.36.11",
        "s.deepl.com": "82.22.36.11",
        "ita-free.www.deepl.com": "82.22.36.11",
        "experimentation.deepl.com": "82.22.36.11",
        "w.deepl.com": "82.22.36.11",
        "login-wall.deepl.com": "82.22.36.11",
        "gtm.deepl.com": "82.22.36.11",
        "checkout.www.deepl.com": "82.22.36.11",
    },
    
    "TikTok": {
        "www.tiktok.com": "82.22.36.11",
        "mcs-sg.tiktok.com": "82.22.36.11",
        "mon.tiktokv.com": "82.22.36.11",
    },
    
    "Netflix": {
        "www.netflix.com": "158.255.0.189",
        "netflix.com": "158.255.0.189",
    },
    
    "Canva": {
        "static.canva.com": "82.22.36.11",
        "content-management-files.canva.com": "82.22.36.11",
        "www.canva.com": "82.22.36.11",
    },
    
    "ProtonMail": {
        "protonmail.com": "3.66.189.153",
        "mail.proton.me": "3.66.189.153",
    },
    
    "ElevenLabs": {
        "elevenlabs.io": "82.22.36.11",
        "api.us.elevenlabs.io": "82.22.36.11",
        "elevenreader.io": "82.22.36.11",
    },
    
    "GitHub Copilot": {
        "api.individual.githubcopilot.com": "82.22.36.11",
        "proxy.individual.githubcopilot.com": "82.22.36.11",
    },
    
    "JetBrains": {
        "datalore.jetbrains.com": "50.7.85.221",
        "plugins.jetbrains.com": "107.150.34.100",
    },
    
    "Codeium": {
        "codeium.com": "82.22.36.11",
        "inference.codeium.com": "82.22.36.11",
    },
    
    "SoundCloud": {
        "soundcloud.com": "18.238.243.27",
        "style.sndcdn.com": "13.224.222.71",
        "a-v2.sndcdn.com": "3.164.206.34",
        "secure.sndcdn.com": "18.165.140.56",
    },
    
    "Manus": {
        "manus.im": "82.22.36.11",
        "api.manus.im": "82.22.36.11",
        "manuscdn.com": "82.22.36.11",
        "files.manuscdn.com": "82.22.36.11",
    },
    
    "Pixabay": {
        "pixabay.com": "82.22.36.11",
        "cdn.pixabay.com": "82.22.36.11",
    },
    
    "RuTracker": {
        "rutracker.org": "172.67.182.196",
        "static.rutracker.cc": "104.21.50.150",
    },
    
    "Rutor": {
        "rutor.info": "172.64.33.155",
        "d.rutor.info": "172.64.33.155",
        "rutor.is": "173.245.59.155",
        "rutor.org": "0.0.0.0",
    },
    
    "Другое": {
        "www.aomeitech.com": "0.0.0.0",
        "www.intel.com": "82.22.36.11",
        "www.dell.com": "82.22.36.11",
        "developer.nvidia.com": "82.22.36.11",
        "truthsocial.com": "204.12.192.221",
        "static-assets-1.truthsocial.com": "204.12.192.221",
        "autodesk.com": "94.131.119.85",
        "accounts.autodesk.com": "94.131.119.85",
        "www.hulu.com": "2.19.183.66",
        "hulu.com": "2.22.31.233",
        "anilib.me": "172.67.192.246",
        "ntc.party": "130.255.77.28",
        "pump.fun": "82.22.36.11",
        "frontend-api-v3.pump.fun": "82.22.36.11",
        "images.pump.fun": "82.22.36.11",
        "swap-api.pump.fun": "82.22.36.11",
        "www.elgato.com": "82.22.36.11",
        "info.dns.malw.link": "104.21.24.110",
        "only-fans.uk": "0.0.0.0",
        "only-fans.me": "0.0.0.0",
        "only-fans.wtf": "0.0.0.0",
    },
}

# ═══════════════════════════════════════════════════════════════
# PROXY_DOMAINS - объединённый словарь для совместимости
# ═══════════════════════════════════════════════════════════════

PROXY_DOMAINS = {}
for service_domains in SERVICES.values():
    PROXY_DOMAINS.update(service_domains)

# ═══════════════════════════════════════════════════════════════
# БЫСТРЫЙ ВЫБОР - ВСЕ сервисы для кнопок быстрого выбора
# Формат: (иконка_qtawesome, название, цвет_иконки)
# ═══════════════════════════════════════════════════════════════

QUICK_SERVICES = [
    # AI сервисы
    ("fa5b.discord", "Discord TCP", "#5865f2"),
    ("fa5b.youtube", "YouTube TCP", "#ff0000"),
    ("fa5b.github", "GitHub TCP", "#181717"),
    ("fa5b.discord", "Discord Voice", "#5865f2"),
    ("mdi.robot", "ChatGPT", "#10a37f"),
    ("mdi.google", "Gemini", "#4285f4"),
    ("fa5s.brain", "Claude", "#cc9b7a"),
    ("fa5b.microsoft", "Copilot", "#00bcf2"),
    ("fa5b.twitter", "Grok", "#1da1f2"),
    # Соцсети
    ("fa5b.instagram", "Instagram", "#e4405f"),
    ("fa5b.facebook-f", "Facebook", "#1877f2"),
    ("mdi.at", "Threads", "#ffffff"),
    ("mdi.music-note", "TikTok", "#ff0050"),
    # Медиа и развлечения
    ("fa5b.spotify", "Spotify", "#1db954"),
    ("fa5s.film", "Netflix", "#e50914"),
    ("fa5b.twitch", "Twitch", "#9146ff"),
    ("fa5b.soundcloud", "SoundCloud", "#ff5500"),
    # Продуктивность
    ("fa5s.sticky-note", "Notion", "#ffffff"),
    ("fa5s.language", "DeepL", "#0f2b46"),
    ("fa5s.palette", "Canva", "#00c4cc"),
    ("fa5s.envelope", "ProtonMail", "#6d4aff"),
    # Разработка
    ("fa5s.microphone-alt", "ElevenLabs", "#ffffff"),
    ("fa5b.github", "GitHub Copilot", "#ffffff"),
    ("fa5s.code", "JetBrains", "#fe315d"),
    ("fa5s.bolt", "Codeium", "#09b6a2"),
    # Торренты
    ("fa5s.magnet", "RuTracker", "#3498db"),
    ("fa5s.magnet", "Rutor", "#e74c3c"),
    # Другое
    ("fa5s.robot", "Manus", "#7c3aed"),
    ("fa5s.images", "Pixabay", "#00ab6c"),
    ("fa5s.box-open", "Другое", "#6c757d"),
]

# ═══════════════════════════════════════════════════════════════
# ПРЕСЕТЫ - готовые наборы сервисов
# ═══════════════════════════════════════════════════════════════

# Пресеты: (иконка_qtawesome, цвет, список_сервисов)
PRESETS = {
    "Минимум": ("fa5s.check-circle", "#60cdff", ["ChatGPT", "Instagram", "Spotify"]),
    "Все AI": ("fa5s.robot", "#60cdff", ["ChatGPT", "Gemini", "Claude", "Copilot", "Grok", "ElevenLabs", "GitHub Copilot", "Codeium"]),
    "Соцсети": ("fa5s.users", "#60cdff", ["Instagram", "Facebook", "Threads", "TikTok"]),
    "Популярное": ("fa5s.star", "#60cdff", ["ChatGPT", "Claude", "Instagram", "Spotify", "Notion", "DeepL"]),
}


def get_service_domains(service_name: str) -> dict:
    """Возвращает домены сервиса"""
    return SERVICES.get(service_name, {})


def get_preset_domains(preset_name: str) -> dict:
    """Возвращает все домены для пресета"""
    domains = {}
    preset_data = PRESETS.get(preset_name)
    if preset_data:
        # Новый формат: (icon, color, services)
        services = preset_data[2] if len(preset_data) >= 3 else []
        for service in services:
            domains.update(get_service_domains(service))
    return domains


def get_all_services() -> list:
    """Возвращает список всех сервисов"""
    return list(SERVICES.keys())

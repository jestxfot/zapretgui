# hosts/proxy_domains.py
# Домены разбиты по сервисам для удобного быстрого выбора

# ═══════════════════════════════════════════════════════════════
# СЕРВИСЫ - каждый сервис содержит список своих доменов с IP
# ═══════════════════════════════════════════════════════════════

SERVICES = {
    "ChatGPT": {
        "chatgpt.com": "109.69.21.35",
        "ab.chatgpt.com": "109.69.21.35",
        "auth.openai.com": "109.69.21.35",
        "auth0.openai.com": "109.69.21.35",
        "platform.openai.com": "109.69.21.35",
        "cdn.oaistatic.com": "109.69.21.35",
        "files.oaiusercontent.com": "109.69.21.35",
        "cdn.auth0.com": "109.69.21.35",
        "tcr9i.chat.openai.com": "109.69.21.35",
        "webrtc.chatgpt.com": "109.69.21.35",
        "android.chat.openai.com": "109.69.21.35",
        "api.openai.com": "109.69.21.35",
        "sora.com": "94.183.233.72",
        "sora.chatgpt.com": "94.183.233.72",
        "videos.openai.com": "94.183.233.72",
        "us.posthog.com": "94.183.233.72",
    },
    
    "Gemini": {
        "gemini.google.com": "109.69.21.35",
        "alkalimakersuite-pa.clients6.google.com": "109.69.21.35",
        "aisandbox-pa.googleapis.com": "109.69.21.35",
        "webchannel-alkalimakersuite-pa.clients6.google.com": "109.69.21.35",
        "proactivebackend-pa.googleapis.com": "109.69.21.35",
        "o.pki.goog": "109.69.21.35",
        "labs.google": "109.69.21.35",
        "notebooklm.google": "109.69.21.35",
        "notebooklm.google.com": "109.69.21.35",
    },
    
    "Claude": {
        "claude.ai": "109.69.21.35",
        "api.claude.ai": "109.69.21.35",
        "anthropic.com": "109.69.21.35",
        "www.anthropic.com": "109.69.21.35",
        "api.anthropic.com": "109.69.21.35",
    },
    
    "Copilot": {
        "copilot.microsoft.com": "109.69.21.35",
        "sydney.bing.com": "109.69.21.35",
        "edgeservices.bing.com": "109.69.21.35",
        "rewards.bing.com": "109.69.21.35",
        "xsts.auth.xboxlive.com": "109.69.21.35",
    },
    
    "Grok": {
        "grok.com": "109.69.21.35",
        "assets.grok.com": "109.69.21.35",
        "accounts.x.ai": "109.69.21.35",
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
        "api.spotify.com": "109.69.21.35",
        "xpui.app.spotify.com": "109.69.21.35",
        "appresolve.spotify.com": "109.69.21.35",
        "login5.spotify.com": "109.69.21.35",
        "gew1-spclient.spotify.com": "109.69.21.35",
        "gew1-dealer.spotify.com": "109.69.21.35",
        "spclient.wg.spotify.com": "109.69.21.35",
        "api-partner.spotify.com": "109.69.21.35",
        "aet.spotify.com": "109.69.21.35",
        "www.spotify.com": "109.69.21.35",
        "accounts.spotify.com": "109.69.21.35",
        "spotifycdn.com": "109.69.21.35",
        "open-exp.spotifycdn.com": "109.69.21.35",
        "www-growth.scdn.co": "109.69.21.35",
        "login.app.spotify.com": "109.69.21.35",
        "accounts.scdn.co": "109.69.21.35",
        "ap-gew1.spotify.com": "109.69.21.35",
    },
    
    "Notion": {
        "www.notion.so": "109.69.21.35",
        "notion.so": "109.69.21.35",
        "calendar.notion.so": "109.69.21.35",
    },
    
    "Twitch": {
        "usher.ttvnw.net": "109.69.21.35",
        "gql.twitch.tv": "109.69.21.35",
    },
    
    "DeepL": {
        "deepl.com": "109.69.21.35",
        "www.deepl.com": "109.69.21.35",
        "s.deepl.com": "109.69.21.35",
        "ita-free.www.deepl.com": "109.69.21.35",
        "experimentation.deepl.com": "109.69.21.35",
        "w.deepl.com": "109.69.21.35",
        "login-wall.deepl.com": "109.69.21.35",
        "gtm.deepl.com": "109.69.21.35",
        "checkout.www.deepl.com": "109.69.21.35",
    },
    
    "TikTok": {
        "www.tiktok.com": "94.183.233.72",
        "mcs-sg.tiktok.com": "94.183.233.72",
        "mon.tiktokv.com": "94.183.233.72",
    },
    
    "Netflix": {
        "www.netflix.com": "158.255.0.189",
        "netflix.com": "158.255.0.189",
    },
    
    "Canva": {
        "static.canva.com": "94.183.233.72",
        "content-management-files.canva.com": "94.183.233.72",
        "www.canva.com": "94.183.233.72",
    },
    
    "ProtonMail": {
        "protonmail.com": "3.66.189.153",
        "mail.proton.me": "3.66.189.153",
    },
    
    "ElevenLabs": {
        "elevenlabs.io": "109.69.21.35",
        "api.us.elevenlabs.io": "109.69.21.35",
        "elevenreader.io": "109.69.21.35",
    },
    
    "GitHub Copilot": {
        "api.individual.githubcopilot.com": "94.183.233.72",
        "proxy.individual.githubcopilot.com": "94.183.233.72",
    },
    
    "JetBrains": {
        "datalore.jetbrains.com": "50.7.85.221",
        "plugins.jetbrains.com": "107.150.34.100",
    },
    
    "Codeium": {
        "codeium.com": "94.183.233.72",
        "inference.codeium.com": "94.183.233.72",
    },
    
    "SoundCloud": {
        "soundcloud.com": "18.238.243.27",
        "style.sndcdn.com": "13.224.222.71",
        "a-v2.sndcdn.com": "3.164.206.34",
        "secure.sndcdn.com": "18.165.140.56",
    },
    
    "Manus": {
        "manus.im": "109.69.21.35",
        "api.manus.im": "94.183.233.72",
        "manuscdn.com": "109.69.21.35",
        "files.manuscdn.com": "109.69.21.35",
    },
    
    "Pixabay": {
        "pixabay.com": "94.183.233.72",
        "cdn.pixabay.com": "94.183.233.72",
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
        "www.intel.com": "109.69.21.35",
        "www.dell.com": "109.69.21.35",
        "developer.nvidia.com": "94.183.233.72",
        "truthsocial.com": "204.12.192.221",
        "static-assets-1.truthsocial.com": "204.12.192.221",
        "autodesk.com": "94.131.119.85",
        "accounts.autodesk.com": "94.131.119.85",
        "www.hulu.com": "2.19.183.66",
        "hulu.com": "2.22.31.233",
        "anilib.me": "172.67.192.246",
        "ntc.party": "130.255.77.28",
        "pump.fun": "94.183.233.72",
        "frontend-api-v3.pump.fun": "94.183.233.72",
        "images.pump.fun": "94.183.233.72",
        "swap-api.pump.fun": "94.183.233.72",
        "www.elgato.com": "94.183.233.72",
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

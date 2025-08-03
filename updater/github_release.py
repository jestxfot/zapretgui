# updater/github_release.py
"""
github_release.py
────────────────────────────────────────────────────────────────
Получение информации о последнем релизе с GitHub для выбранного канала.
"""

from __future__ import annotations
from typing import Optional, List, Dict, Any
from packaging import version
from log import log

GITHUB_API_URL = "https://api.github.com/repos/youtubediscord/zapret/releases"
TIMEOUT = 10  # сек.

def normalize_version(ver_str: str) -> str:
    if ver_str.startswith('v') or ver_str.startswith('V'):
        ver_str = ver_str[1:]
    ver_str = ver_str.strip()
    parts = ver_str.split('.')
    if len(parts) < 2:
        raise ValueError(f"Invalid version format: {ver_str}")
    try:
        for part in parts:
            int(part)
    except ValueError:
        raise ValueError(f"Invalid version format: {ver_str}")
    return ver_str

def compare_versions(v1: str, v2: str) -> int:
    """
    Сравнивает две версии.
    Возвращает: -1 если v1 < v2, 0 если равны, 1 если v1 > v2
    """
    try:
        ver1 = version.parse(v1)
        ver2 = version.parse(v2)
        if ver1 < ver2:
            return -1
        elif ver1 > ver2:
            return 1
        else:
            return 0
    except Exception:
        # Fallback на строковое сравнение
        return -1 if v1 < v2 else (1 if v1 > v2 else 0)

def get_all_releases_with_exe() -> List[Dict[str, Any]]:
    """
    Получает все релизы с .exe файлами
    """
    import requests
    
    releases_with_exe = []
    headers = {"Accept": "application/vnd.github.v3+json"}
    
    page = 1
    while page <= 10:  # Максимум 10 страниц (1000 релизов)
        try:
            params = {"per_page": 100, "page": page}
            resp = requests.get(GITHUB_API_URL, headers=headers, params=params, timeout=TIMEOUT)
            resp.raise_for_status()
            releases = resp.json()
            
            if not releases:
                break
                
            for release in releases:
                # Ищем .exe файл в ассетах
                exe_asset = next((a for a in release.get("assets", []) if a["name"].endswith(".exe")), None)
                if not exe_asset:
                    continue
                    
                try:
                    version_str = normalize_version(release["tag_name"])
                    releases_with_exe.append({
                        "version": version_str,
                        "tag_name": release["tag_name"],
                        "update_url": exe_asset["browser_download_url"],
                        "release_notes": release.get("body", ""),
                        "prerelease": release.get("prerelease", False),
                        "name": release.get("name", ""),
                        "published_at": release.get("published_at", ""),
                        "created_at": release.get("created_at", "")
                    })
                except ValueError as e:
                    log(f"❌ Неверный формат версии {release['tag_name']}: {e}", "🔁 UPDATE")
                    continue
                    
            page += 1
            
        except Exception as e:
            log(f"Ошибка получения страницы {page}: {e}", "🔁 UPDATE")
            break
    
    return releases_with_exe

def get_latest_release(channel: str) -> Optional[dict]:
    """
    Получает информацию о последнем релизе с GitHub.
    Для stable канала использует /releases/latest.
    Для dev канала ищет самую новую версию среди ALL релизов с .exe файлами.
    """
    import requests

    try:
        if channel == "stable":
            # Для stable используем /releases/latest
            headers = {"Accept": "application/vnd.github.v3+json"}
            url = "https://api.github.com/repos/youtubediscord/zapret/releases/latest"
            resp = requests.get(url, headers=headers, timeout=TIMEOUT)
            resp.raise_for_status()
            release = resp.json()
            
            log(f"📋 Получен последний стабильный релиз: {release['tag_name']}", "🔁 UPDATE")
            
            exe_asset = next((a for a in release.get("assets", []) if a["name"].endswith(".exe")), None)
            if not exe_asset:
                log("❌ В стабильном релизе нет .exe файла", "🔁 UPDATE")
                return None
                
            version_str = normalize_version(release["tag_name"])
            return {
                "version": version_str,
                "tag_name": release["tag_name"],
                "update_url": exe_asset["browser_download_url"],
                "release_notes": release.get("body", ""),
                "prerelease": False,
                "name": release.get("name", ""),
                "published_at": release.get("published_at", "")
            }
        else:
            # Для dev канала получаем ВСЕ релизы и ищем самый новый
            log("🔍 Получение всех dev релизов для поиска самого нового...", "🔁 UPDATE")
            
            all_releases = get_all_releases_with_exe()
            if not all_releases:
                log("❌ Не найдено релизов с .exe файлом", "🔁 UPDATE")
                return None
            
            log(f"📦 Найдено {len(all_releases)} релизов с .exe файлами", "🔁 UPDATE")
            
            # Сортируем по версии (от новой к старой)
            def version_key(rel):
                try:
                    return version.parse(rel["version"])
                except:
                    return version.parse("0.0.0")
            
            all_releases.sort(key=version_key, reverse=True)
            
            # Логируем первые 5 релизов для отладки
            log("🔝 Топ релизов по версии:", "🔁 UPDATE")
            for i, rel in enumerate(all_releases[:5]):
                prerelease_mark = " (prerelease)" if rel.get("prerelease") else ""
                log(f"   {i+1}. v{rel['version']}{prerelease_mark} - {rel.get('created_at', 'н/д')}", "🔁 UPDATE")
            
            # Возвращаем самый новый
            latest = all_releases[0]
            log(f"✅ Выбран самый новый dev релиз: {latest['version']} (prerelease: {latest.get('prerelease', False)})", "🔁 UPDATE")
            
            return latest
            
    except Exception as e:
        log(f"Не удалось получить релизы с GitHub: {e}", "🔁❌ ERROR")
        return None
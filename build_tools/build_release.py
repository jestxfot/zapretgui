#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
build_tools/build_release.py  –  интерактивная сборка + публикация
"""

from __future__ import annotations
import ctypes, json, os, re, shutil, subprocess, sys, tempfile, textwrap, urllib.request
from pathlib import Path
from datetime import date
from typing import Sequence

# ────────────────────────────────────────────────────────────────
#  КОНСТАНТЫ
# ────────────────────────────────────────────────────────────────
SSH_HOST   = "root@37.233.85.174"
SSH_KEY    = Path.home() / ".ssh" / "id_ed25519"
REMOTE_DIR = "/var/www/zapret_site/public"
META_URL   = "https://zapretdpi.ru/version.json"
INNO_ISCC  = r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
PY         = sys.executable

# корневая папка (где main.py, zapret.iss …)
def find_project_root(start: Path) -> Path:
    for p in [start, *start.parents]:
        if (p / "main.py").exists() and (p / "config").is_dir():
            return p
    raise FileNotFoundError("main.py not found; поправьте find_project_root()")

ROOT = find_project_root(Path(__file__).resolve())

# ════════════════════════════════════════════════════════════════
#  ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ════════════════════════════════════════════════════════════════
def run(cmd: Sequence[str] | str, check: bool = True, cwd: Path | None = None, capture: bool = False):
    """Единая функция для запуска команд"""
    if isinstance(cmd, (list, tuple)):
        import shlex
        shown = " ".join(shlex.quote(str(c)) for c in cmd)
    else:
        shown = cmd
    print(">", shown)
    
    if capture:
        res = subprocess.run(cmd, shell=isinstance(cmd, str), cwd=cwd,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if check and res.returncode:
            raise subprocess.CalledProcessError(res.returncode, cmd, res.stdout, res.stderr)
        return res.stdout
    else:
        res = subprocess.run(cmd, shell=isinstance(cmd, str), cwd=cwd)
        if check and res.returncode:
            sys.exit(res.returncode)
        return res.returncode


def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def elevate_as_admin():
    ctypes.windll.shell32.ShellExecuteW(None, "runas", PY,
                                        " ".join(map(str, sys.argv)),
                                        str(ROOT), 1)
    sys.exit(0)


def fetch_versions() -> dict[str, str]:
    try:
        with urllib.request.urlopen(META_URL, timeout=10) as resp:
            data = json.load(resp)
        return {
            "stable": data.get("stable", {}).get("version", "—"),
            "test":   data.get("test",   {}).get("version", "—"),
        }
    except Exception:
        return {"stable": "нет данных", "test": "нет данных"}


def suggest_next(ver: str) -> str:
    nums = [int(x) for x in (ver.split(".") + ["0"] * 4)[:4]]
    nums[-1] += 1
    return ".".join(map(str, nums))


# ────────────────────────────────────────────────────────────────
#  ОСТАНАВЛИВАЕМ РАБОТАЮЩИЙ ZAPRET
# ────────────────────────────────────────────────────────────────
def _taskkill(exe: str):
    run(f'taskkill /F /T /IM "{exe}" >nul 2>&1', check=False)

def stop_running_zapret():
    """
    Аккуратно гасит все Zapret.exe:
      • terminate()  – мягко
      • wait 3 с
      • kill()       – если ещё живы
      • затем taskkill /F /T (fallback)
    """
    print("Ищу запущенный Zapret.exe …")

    try:
        import psutil

        targets = []
        for p in psutil.process_iter(["name"]):
            n = (p.info["name"] or "").lower()
            if n in ("zapret.exe"):
                targets.append(p)
                try:
                    print(f"  → terminate PID {p.pid} ({n})")
                    p.terminate()
                except Exception:
                    pass

        if targets:
            psutil.wait_procs(targets, timeout=3)   # ждём, пока завершатся
            # то, что ещё живо → kill
            for p in targets:
                if p.is_running():
                    try:
                        print(f"  → kill PID {p.pid}")
                        p.kill()
                    except Exception:
                        pass

    except ImportError:
        pass  # нет psutil – падаем на taskkill

    # принудительный fallback
    _taskkill("Zapret.exe")


# ────────────────────────────────────────────────────────────────
#  ПАТЧИМ zapret.iss
# ────────────────────────────────────────────────────────────────
def _sub(line: str, repl: str, text: str) -> str:
    """Безопасно заменяет строку  <line>=…  (учитывает пробелы, комментарии)."""
    pattern = rf"(?im)^\s*{line}\s*=.*$"
    if re.search(pattern, text):
        return re.sub(pattern,
                      lambda m: f"{m.group(0).split('=')[0]}= {repl}",
                      text)
    return text.replace("[Setup]", f"[Setup]\n{line}={repl}", 1)

def _ensure_uninstall_delete(text: str, path: str) -> str:
    """
    Вставляет/заменяет блок [UninstallDelete] одной строкой:
      Type: filesandordirs; Name: "<path>"
    Использует lambda-замену, чтобы не было проблем со слэшами.
    """
    block = f"[UninstallDelete]\nType: filesandordirs; Name: \"{path}\""
    pat   = r"(?is)\[UninstallDelete\].*?(?=\n\[|\Z)"
    if re.search(pat, text):
        text = re.sub(pat, lambda _: block, text)   # ← безопасная замена
    else:
        text += "\n" + block
    return text


def prepare_iss(channel: str, version: str) -> Path:
    """Создаёт zapret_<channel>.iss с нужными полями."""
    src = ROOT / "zapret.iss"
    if not src.exists():
        raise FileNotFoundError("zapret.iss not found")

    txt = src.read_text(encoding="utf-8-sig")

    # ── если version пустая, берём текущую из .iss и увеличиваем ──
    if not version.strip():
        import re
        m = re.search(r"^AppVersion\s*=\s*([0-9\.]+)", txt, re.MULTILINE)
        current = m.group(1) if m else "0.0.0.0"
        version = suggest_next(current)        # функция у вас уже есть

    txt = _sub("AppVersion", version, txt)

    base_guid = "5C71C1DC-7627-4E57-9B1A-6B5D1F3A57F0"

    if channel == "test":                                   # DEV
        txt = _sub("AppName",            "Zapret Dev",           txt)
        txt = _sub("OutputBaseFilename", "ZapretSetup_TEST",     txt)
        txt = _sub("AppId",              f"{{{{{base_guid}-TEST}}}}", txt)
        txt = _sub("DefaultGroupName",   "Zapret Dev",           txt)
        txt = txt.replace(r"{commonappdata}\Zapret",
                          r"{commonappdata}\ZapretDev")
        txt = _ensure_uninstall_delete(txt,
                          r"{commonappdata}\ZapretDev")
        txt = _sub("SetupIconFile",      "ZapretDevLogo.ico",    txt)
    else:                                                  # STABLE
        txt = _sub("AppName",            "Zapret",               txt)
        txt = _sub("OutputBaseFilename", "ZapretSetup",          txt)
        txt = _sub("AppId",              f"{{{{{base_guid}}}}}", txt)
        txt = _sub("DefaultGroupName",   "Zapret",               txt)
        txt = _ensure_uninstall_delete(txt,
                          r"{commonappdata}\Zapret")
        txt = _sub("SetupIconFile",      "zapret.ico",           txt)

    # ── OutputDir ────────────────────────────────────────────────
    outdir_line = f'OutputDir="{ROOT}"'
    txt = _sub("OutputDir", outdir_line.split("=", 1)[1].lstrip(), txt)

    # ── сохраняем во временный .iss рядом с проектом ─────────────
    patched = ROOT / f"zapret_{channel}.iss"
    patched.write_text(txt, encoding="utf-8-sig")
    return patched


def write_build_info(channel: str, version: str):
    dst = ROOT / "config" / "build_info.py"
    dst.parent.mkdir(exist_ok=True)
    dst.write_text(f"# AUTOGENERATED\nCHANNEL={channel!r}\nAPP_VERSION={version!r}\n",
                   encoding="utf-8-sig")
    print("✔ build_info.py updated")


def create_spec_file(channel: str):
    """Создает spec файл для PyInstaller"""
    icon_file = 'ZapretDevLogo.ico' if channel == 'test' else 'zapret.ico'
    
    spec_content = f"""# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'win32com', 
        'win32com.client', 
        'pythoncom',
        'win32api',
        'win32con',
        'win32service',
        'win32serviceutil'
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='zapret',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=True,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    uac_admin=True,
    icon='{icon_file}',
    version='version_info.txt',
)"""
    
    spec_path = ROOT / "zapret_build.spec"
    spec_path.write_text(spec_content, encoding='utf-8')
    return spec_path


def patch_version_json(channel: str, version: str, url: str, notes: str):
    """
    Обновляет один узел (stable / test) в version.json.
    ВСЕГДА сохраняет данные других каналов.
    """
    tmp      = Path(tempfile.gettempdir()) / "version.json"
    tmp_new  = tmp.with_suffix(".new")
    bak_name = "version.json.bak"

    # ────────────────────────────────────────────────────────────
    # 1. СНАЧАЛА скачиваем текущий файл с сервера через SCP
    # ────────────────────────────────────────────────────────────
    data = {}
    
    # Скачиваем файл напрямую с сервера
    rc = run(["scp", "-i", str(SSH_KEY), 
              f"{SSH_HOST}:{REMOTE_DIR}/version.json", 
              str(tmp)], check=False)
    
    if rc == 0 and tmp.exists() and tmp.stat().st_size > 0:
        try:
            data = json.loads(tmp.read_text(encoding="utf-8-sig"))
            print("✔ Успешно загружен существующий version.json")
        except json.JSONDecodeError:
            print("[WARN] Ошибка парсинга JSON")
            data = {}
    else:
        print("[WARN] Не удалось скачать version.json с сервера")
        # Пробуем альтернативные методы
        
        # curl
        rc = run(["curl", "--http1.1", "-fsSL", META_URL, "-o", str(tmp)],
                 check=False)
        if rc == 0 and tmp.exists() and tmp.stat().st_size:
            try:
                data = json.loads(tmp.read_text(encoding="utf-8-sig"))
                print("✔ Получен через curl")
            except json.JSONDecodeError:
                pass
        
        # requests
        if not data:
            try:
                import requests
                resp = requests.get(META_URL, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                print("✔ Получен через requests")
            except Exception:
                pass

    if not isinstance(data, dict):
        data = {}

    # ────────────────────────────────────────────────────────────
    # 2. Обновляем ТОЛЬКО нужный канал
    # ────────────────────────────────────────────────────────────
    
    # Важно: обновляем только указанный канал, не трогая остальные!
    data[channel] = {
        "version":       version,
        "update_url":    url,
        "release_notes": notes,
        "date":          date.today().isoformat(),
    }
    
    # Выводим итоговую структуру для проверки
    print(f"\nИтоговая структура JSON:")
    print(json.dumps(data, ensure_ascii=False, indent=2))

    tmp_new.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                       encoding="utf-8-sig")

    # ────────────────────────────────────────────────────────────
    # 3. Резервная копия и атомарная замена на сервере
    # ────────────────────────────────────────────────────────────
    print("\nЗагружаем на сервер...")
    
    # Делаем бэкап
    run(["ssh", "-i", str(SSH_KEY), SSH_HOST,
         f"cp {REMOTE_DIR}/version.json {REMOTE_DIR}/{bak_name} 2>/dev/null || true"])
    
    # Загружаем новый файл
    run(["scp", "-C", "-i", str(SSH_KEY), str(tmp_new),
         f"{SSH_HOST}:{REMOTE_DIR}/version.json.tmp"])
    
    # Атомарная замена
    run(["ssh", "-i", str(SSH_KEY), SSH_HOST,
         f"mv {REMOTE_DIR}/version.json.tmp {REMOTE_DIR}/version.json"])

    print("✔ version.json обновлен (резервная копия: version.json.bak)")
    

# ════════════════════════════════════════════════════════════════
#  ОСНОВНОЙ SCRIPT
# ════════════════════════════════════════════════════════════════
def main() -> None:
    try:
        if not is_admin():
            print("Перезапуск с правами администратора…")
            elevate_as_admin()

        vers = fetch_versions()                 # {"stable": "...", "test": "..."}
        print("\n=== Опубликованные версии ===")
        print(f"  stable : {vers['stable']}")
        print(f"  test   : {vers['test']}\n")

        # ───────── 1. Канал ─────────
        raw_channel = input("Канал публикации [S/t] > ").strip().lower()
        channel = "stable" if raw_channel in ("s", "stable") else "test"

        # ─── 2. номер версии ────────────────────────────────────────
        last_ver = vers[channel] if vers[channel] != "—" else "0.0.0.0"
        auto_next = suggest_next(last_ver)           # +1 к последней цифре
        raw_ver = input(f"Номер версии [{auto_next}] > ").strip()

        VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(?:\.\d+)?$")   # 1.2.3 или 1.2.3.4
        # если пользователь просто нажал Enter → берём auto_next
        version = raw_ver or auto_next

        if not VERSION_RE.fullmatch(version):
            print(f"[ERROR] Неверный формат номера версии: \"{version}\"")
            sys.exit(1)

        # ───────── 3. Release-notes ──
        notes = input("Release-notes (Enter = авто) > ").strip() or f"Zapret {version}"

        fast_mode = (not raw_channel) and (not raw_ver)  # ничего не вводили вручную

        print(f"\nКанал: {channel}   Версия: {version}")
        if not fast_mode:
            if input("Продолжить? [y/N] > ").strip().lower() != "y":
                sys.exit(0)
        
        print("✔ Обновляем build_info.py...")
        write_build_info(channel, version)
        
        print("✔ Останавливаем запущенный Zapret...")
        stop_running_zapret()

        # 3) Создаем spec файл
        print("✔ Создаем spec файл...")
        spec_path = create_spec_file(channel)

        # 4) PyInstaller
        print("✔ Запускаем PyInstaller...")
        work = Path(tempfile.mkdtemp(prefix="pyi_"))
        out = ROOT.parent / "zapret"
        
        try:
            run([
                PY, "-m", "PyInstaller",
                "--workpath", str(work),
                "--distpath", str(out),
                "--clean",
                "--noconfirm",
                str(spec_path)
            ])
        finally:
            # Очищаем временные файлы
            shutil.rmtree(work, ignore_errors=True)
            if spec_path.exists():
                spec_path.unlink()

        # 5) Inno Setup
        print("✔ Запускаем Inno Setup...")
        iss_file = prepare_iss(channel, version)
        run([INNO_ISCC, str(iss_file)])

        # 6) итоговый инсталлятор
        produced = ROOT / f"ZapretSetup{'_TEST' if channel == 'test' else ''}.exe"
        if not produced.exists():
            raise FileNotFoundError(f"{produced} not found – проверьте OutputBaseFilename / OutputDir")
        print(f"✔ Инсталлятор: {produced}")

        print("✔ Загружаем на сервер...")
        run(["scp", "-i", str(SSH_KEY), "-C", str(produced),
             f"{SSH_HOST}:{REMOTE_DIR}"])

        print("✔ Обновляем version.json...")
        patch_version_json(channel, version, f"https://zapretdpi.ru/{produced.name}", notes)
        print("\n✔ Всё готово!")
        
    except KeyboardInterrupt:
        print("\n\nОтменено пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        os.system("pause")


if __name__ == "__main__":
    main()
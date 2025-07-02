# utils/subproc.py
import os, subprocess, sys

# выбираем «родную» кодировку
WIN_OEM = "cp866"
DEFAULT  = "utf-8"

def run_app(cmd: list[str] | str,
        timeout: int = 15,
        **kw):
    """
    Безопасный wrapper вокруг subprocess.run
    – гарантирует корректную кодировку и подавляет UnicodeDecodeError.
    """
    enc = WIN_OEM if os.name == "nt" else DEFAULT

    params = dict(
        capture_output=True,
        text=True,           # ← авто-декодирование в str
        encoding=enc,        # ← ГЛАВНОЕ
        errors="replace",    # ← чтобы даже мусор не уронить поток
        timeout=timeout,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    params.update(kw)        # можно переопределить снаружи

    return subprocess.run(cmd, **params)
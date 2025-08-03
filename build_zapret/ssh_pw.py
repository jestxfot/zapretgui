# build_zapret/ssh_pw.py
"""
ssh_pw.py – компактная обёртка вокруг paramiko
Используется в build_release_gui.py для работы по паролю вместо ключа.
"""

from __future__ import annotations
import paramiko, threading
from pathlib import Path
from typing import Any

# ────────────────────────────────────────────────────────────────
#  НАСТРОЙКИ ПОДКЛЮЧЕНИЯ
# ────────────────────────────────────────────────────────────────
SSH_HOST:     str = "38.244.138.56"   # без user@
SSH_PORT:     int = 22
SSH_USER:     str = "root"
SSH_PASSWORD: str = "m5C5Ze6lWbK#BIwEIV"

REMOTE_DIR = "/home/zapretsite"
META_URL   = "https://nozapret.ru/index.json"

# ────────────────────────────────────────────────────────────────
#  ВНУТРЕННЕЕ ОДИНОЧНОЕ СОЕДИНЕНИЕ
# ────────────────────────────────────────────────────────────────
_lock   = threading.RLock()
_client: paramiko.SSHClient | None = None


def _get_client() -> paramiko.SSHClient:
    """Лениво открывает и кэширует SSH-сеанс."""
    global _client
    with _lock:
        if _client and _client.get_transport() and _client.get_transport().is_active():
            return _client
        
        c = paramiko.SSHClient()
        c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        c.connect(
            hostname=SSH_HOST,
            port=SSH_PORT,
            username=SSH_USER,
            password=SSH_PASSWORD,
            look_for_keys=False,
            allow_agent=False,
            banner_timeout=10,
            auth_timeout=10,
            timeout=10,
        )
        _client = c
        return c


# ────────────────────────────────────────────────────────────────
#  ПОЛЕЗНЫЕ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ────────────────────────────────────────────────────────────────
def ssh_exec(cmd: str) -> tuple[int, str, str]:
    """
    Выполняет команду на сервере.
    Возвращает (ret_code, stdout, stderr)
    """
    cl = _get_client()
    stdin, stdout, stderr = cl.exec_command(cmd)
    ret = stdout.channel.recv_exit_status()
    out = stdout.read().decode(errors='ignore')
    err = stderr.read().decode(errors='ignore')
    return ret, out, err


def sftp_upload(local: str | Path, remote: str):
    cl = _get_client()
    with cl.open_sftp() as sftp:
        sftp.put(str(local), remote)


def sftp_download(remote: str, local: str | Path):
    cl = _get_client()
    with cl.open_sftp() as sftp:
        sftp.get(remote, str(local))

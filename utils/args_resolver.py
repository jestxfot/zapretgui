"""
Общая функция для разрешения путей в аргументах командной строки winws/winws2.

Используется в:
- strategy_menu/strategy_runner.py
- autostart/autostart_direct.py
- ui/pages/strategies_page.py
"""

import os
from typing import List
from log import log


# Префиксы для файлов из папки lists/
LISTS_PREFIXES = [
    "--hostlist=",
    "--ipset=",
    "--hostlist-exclude=",
    "--ipset-exclude=",
]

# Префиксы для файлов из папки bin/
BIN_PREFIXES = [
    "--dpi-desync-fake-tls=",
    "--dpi-desync-fake-syndata=",
    "--dpi-desync-fake-quic=",
    "--dpi-desync-fake-unknown-udp=",
    "--dpi-desync-split-seqovl-pattern=",
    "--dpi-desync-fake-http=",
    "--dpi-desync-fake-unknown=",
    "--dpi-desync-fakedsplit-pattern=",
    "--dpi-desync-fake-discord=",
    "--dpi-desync-fake-stun=",
    "--dpi-desync-fake-dht=",
    "--dpi-desync-fake-wireguard=",
]


def resolve_args_paths(
    args: List[str],
    lists_dir: str,
    bin_dir: str,
    filter_dir: str = None
) -> List[str]:
    """
    Разрешает относительные пути к файлам в аргументах командной строки.

    Args:
        args: Список аргументов командной строки
        lists_dir: Путь к папке lists/ (для --hostlist, --ipset и т.д.)
        bin_dir: Путь к папке bin/ (для --dpi-desync-fake-* файлов)
        filter_dir: Путь к папке windivert.filter/ (для --wf-raw-part, опционально)

    Returns:
        Список аргументов с разрешёнными путями
    """
    resolved_args = []

    for arg in args:
        resolved_arg = _resolve_single_arg(arg, lists_dir, bin_dir, filter_dir)
        resolved_args.append(resolved_arg)

    return resolved_args


def _resolve_single_arg(
    arg: str,
    lists_dir: str,
    bin_dir: str,
    filter_dir: str = None
) -> str:
    """Разрешает путь в одном аргументе"""

    # Обработка --wf-raw-part (для winws2)
    if arg.startswith("--wf-raw-part=") and filter_dir:
        value = arg.split("=", 1)[1]

        if value.startswith("@"):
            filename = value[1:].strip('"')

            if not os.path.isabs(filename):
                full_path = os.path.join(filter_dir, filename)
                return f'--wf-raw-part=@{full_path}'
            else:
                return f'--wf-raw-part=@{filename}'

        return arg

    # Обработка файлов из lists/
    for prefix in LISTS_PREFIXES:
        if arg.startswith(prefix):
            _, filename = arg.split("=", 1)
            filename = filename.strip('"')

            if not os.path.isabs(filename):
                full_path = os.path.join(lists_dir, filename)
                return f'{prefix}{full_path}'
            else:
                return arg

    # Обработка файлов из bin/
    for prefix in BIN_PREFIXES:
        if arg.startswith(prefix):
            _, filename = arg.split("=", 1)

            # Проверяем специальные значения (hex или модификаторы)
            if filename.startswith("0x") or filename.startswith("!") or filename.startswith("^"):
                return arg

            filename = filename.strip('"')

            if not os.path.isabs(filename):
                full_path = os.path.join(bin_dir, filename)
                return f'{prefix}{full_path}'
            else:
                return arg

    # Остальные аргументы без изменений
    return arg

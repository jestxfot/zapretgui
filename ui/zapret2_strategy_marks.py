from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
from typing import Iterable, Optional, Set, Tuple


MarkKey = Tuple[str, str]  # (category_key, strategy_id)


def _get_direct_zapret2_dir() -> Path:
    """
    Storage dir for direct_zapret2 auxiliary data.

    Windows: %APPDATA%/zapret/direct_zapret2
    Fallback: ~/.config/zapret/direct_zapret2
    """
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "zapret" / "direct_zapret2"
    return Path.home() / ".config" / "zapret" / "direct_zapret2"


def _parse_marks_lines(lines: Iterable[str]) -> Set[MarkKey]:
    out: Set[MarkKey] = set()
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "\t" not in line:
            continue
        cat, sid = line.split("\t", 1)
        cat = cat.strip()
        sid = sid.strip()
        if not cat or not sid:
            continue
        out.add((cat, sid))
    return out


def _format_marks_lines(keys: Set[MarkKey]) -> str:
    parts = [f"{cat}\t{sid}" for cat, sid in sorted(keys, key=lambda x: (x[0].lower(), x[1].lower()))]
    return ("\n".join(parts) + "\n") if parts else ""


@dataclass
class DirectZapret2MarksStore:
    """
    Marks for strategies (working / not working / unmarked).

    Stored as two plain text files:
    - work.txt
    - notwork.txt
    Each line: <category_key>\\t<strategy_id>
    """

    work_path: Path
    notwork_path: Path
    _work: Optional[Set[MarkKey]] = None
    _notwork: Optional[Set[MarkKey]] = None

    @classmethod
    def default(cls) -> "DirectZapret2MarksStore":
        base = _get_direct_zapret2_dir()
        return cls(work_path=base / "work.txt", notwork_path=base / "notwork.txt")

    def _ensure_loaded(self) -> None:
        if self._work is not None and self._notwork is not None:
            return
        self._work = set()
        self._notwork = set()

        if self.work_path.exists():
            self._work = _parse_marks_lines(self.work_path.read_text(encoding="utf-8", errors="ignore").splitlines())
        if self.notwork_path.exists():
            self._notwork = _parse_marks_lines(self.notwork_path.read_text(encoding="utf-8", errors="ignore").splitlines())

        # Enforce exclusivity (prefer work if duplicates exist)
        self._notwork.difference_update(self._work)

    def get_mark(self, category_key: str, strategy_id: str) -> Optional[bool]:
        self._ensure_loaded()
        key = (category_key, strategy_id)
        if key in self._work:
            return True
        if key in self._notwork:
            return False
        return None

    def set_mark(self, category_key: str, strategy_id: str, is_working: Optional[bool]) -> None:
        self._ensure_loaded()
        key = (category_key, strategy_id)
        self._work.discard(key)
        self._notwork.discard(key)
        if is_working is True:
            self._work.add(key)
        elif is_working is False:
            self._notwork.add(key)
        self._save()

    def _save(self) -> None:
        base = self.work_path.parent
        base.mkdir(parents=True, exist_ok=True)

        self.work_path.write_text(_format_marks_lines(self._work), encoding="utf-8")
        self.notwork_path.write_text(_format_marks_lines(self._notwork), encoding="utf-8")

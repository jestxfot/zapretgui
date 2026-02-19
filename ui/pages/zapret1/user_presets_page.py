# ui/pages/zapret1/user_presets_page.py
"""Zapret 1: user presets management. Native qfluentwidgets SettingCard-based UI."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QFileSystemWatcher
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QSizePolicy
from PyQt6.QtGui import QColor

from ui.pages.base_page import BasePage
from log import log

try:
    from qfluentwidgets import (
        BodyLabel, CaptionLabel, SubtitleLabel,
        PrimaryToolButton, TransparentToolButton, TransparentPushButton,
        SettingCard, SettingCardGroup,
        MessageBox, InfoBar, MessageBoxBase,
        FluentIcon as FIF,
        RoundMenu, Action,
    )
    _HAS_FLUENT = True
except ImportError:
    from PyQt6.QtWidgets import QLabel as BodyLabel, QLabel as CaptionLabel   # type: ignore
    from PyQt6.QtWidgets import QLabel as SubtitleLabel                        # type: ignore
    PrimaryToolButton = None   # type: ignore
    TransparentToolButton = None  # type: ignore
    TransparentPushButton = None  # type: ignore
    SettingCard = None         # type: ignore
    SettingCardGroup = None    # type: ignore
    MessageBox = None
    InfoBar = None
    MessageBoxBase = object    # type: ignore
    FIF = None                 # type: ignore
    RoundMenu = None           # type: ignore
    Action = None              # type: ignore
    _HAS_FLUENT = False


# ── Preset card ───────────────────────────────────────────────────────────────

class _PresetCard(SettingCard):
    """Single preset row: icon + name [Активен] [•••]"""

    activate_requested = pyqtSignal(str)
    rename_requested   = pyqtSignal(str)
    delete_requested   = pyqtSignal(str)

    def __init__(self, name: str, is_active: bool, parent=None):
        icon = FIF.PIN if is_active else FIF.DOCUMENT
        super().__init__(icon, name, None, parent)
        self._name = name
        self._is_active = is_active

        if is_active:
            self._badge = CaptionLabel("Активен", self)
            self._badge.setTextColor(
                QColor(0, 100, 180),   # light mode
                QColor(96, 205, 255),  # dark mode  (#60cdff)
            )
            self.hBoxLayout.addWidget(self._badge, 0, Qt.AlignmentFlag.AlignVCenter)
            self.hBoxLayout.addSpacing(8)

        self._more_btn = TransparentToolButton(FIF.MORE, self)
        self._more_btn.setFixedSize(32, 32)
        self._more_btn.clicked.connect(self._show_menu)
        self.hBoxLayout.addWidget(self._more_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        self.hBoxLayout.addSpacing(8)

    def _show_menu(self):
        menu = RoundMenu(parent=self)

        rename_act = Action(FIF.EDIT, "Переименовать")
        rename_act.triggered.connect(lambda: self.rename_requested.emit(self._name))
        menu.addAction(rename_act)

        if not self._is_active:
            menu.addSeparator()
            delete_act = Action(FIF.DELETE, "Удалить")
            delete_act.triggered.connect(lambda: self.delete_requested.emit(self._name))
            menu.addAction(delete_act)

        btn_rect = self._more_btn.rect()
        pos = self._more_btn.mapToGlobal(btn_rect.bottomLeft())
        menu.exec(pos)

    def mousePressEvent(self, event):
        if not self._is_active and event.button() == Qt.MouseButton.LeftButton:
            # Don't activate when clicking the more-button itself
            if not self._more_btn.geometry().contains(event.pos()):
                self.activate_requested.emit(self._name)
                return
        super().mousePressEvent(event)


# ── Dialogs ───────────────────────────────────────────────────────────────────

class _CreatePresetDialog(MessageBoxBase):
    def __init__(self, existing_names: list, parent=None):
        if parent and not parent.isWindow():
            parent = parent.window()
        super().__init__(parent)
        self._existing = list(existing_names)

        self.titleLabel = SubtitleLabel("Новый пресет", self.widget)

        try:
            from qfluentwidgets import LineEdit as FLineEdit
            self.name_edit = FLineEdit(self.widget)
        except Exception:
            from PyQt6.QtWidgets import QLineEdit
            self.name_edit = QLineEdit(self.widget)  # type: ignore
        self.name_edit.setPlaceholderText("Например: Мой профиль / Резерв")
        try:
            self.name_edit.setClearButtonEnabled(True)
        except Exception:
            pass

        self.warn_label = CaptionLabel("", self.widget)
        self.warn_label.setTextColor(QColor(207, 16, 16), QColor(255, 28, 32))
        self.warn_label.hide()

        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addWidget(BodyLabel("Название", self.widget))
        self.viewLayout.addWidget(self.name_edit)
        self.viewLayout.addWidget(self.warn_label)
        self.yesButton.setText("Создать")
        self.cancelButton.setText("Отмена")
        self.widget.setMinimumWidth(400)

    def validate(self) -> bool:
        name = self.name_edit.text().strip()
        if not name:
            self.warn_label.setText("Введите название.")
            self.warn_label.show()
            return False
        if name in self._existing:
            self.warn_label.setText(f"Пресет «{name}» уже существует.")
            self.warn_label.show()
            return False
        self.warn_label.hide()
        return True


class _RenamePresetDialog(MessageBoxBase):
    def __init__(self, current_name: str, existing_names: list, parent=None):
        if parent and not parent.isWindow():
            parent = parent.window()
        super().__init__(parent)
        self._current  = str(current_name or "")
        self._existing = [n for n in existing_names if n != self._current]

        self.titleLabel = SubtitleLabel("Переименовать", self.widget)

        try:
            from qfluentwidgets import LineEdit as FLineEdit
            self.name_edit = FLineEdit(self.widget)
        except Exception:
            from PyQt6.QtWidgets import QLineEdit
            self.name_edit = QLineEdit(self.widget)  # type: ignore
        self.name_edit.setText(self._current)
        self.name_edit.selectAll()
        try:
            self.name_edit.setClearButtonEnabled(True)
        except Exception:
            pass

        self.warn_label = CaptionLabel("", self.widget)
        self.warn_label.setTextColor(QColor(207, 16, 16), QColor(255, 28, 32))
        self.warn_label.hide()

        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addWidget(CaptionLabel(f"Текущее имя: {self._current}", self.widget))
        self.viewLayout.addWidget(BodyLabel("Новое имя", self.widget))
        self.viewLayout.addWidget(self.name_edit)
        self.viewLayout.addWidget(self.warn_label)
        self.yesButton.setText("Переименовать")
        self.cancelButton.setText("Отмена")
        self.widget.setMinimumWidth(400)

    def validate(self) -> bool:
        name = self.name_edit.text().strip()
        if not name:
            self.warn_label.setText("Введите название.")
            self.warn_label.show()
            return False
        if name == self._current:
            self.warn_label.hide()
            return True
        if name in self._existing:
            self.warn_label.setText(f"Пресет «{name}» уже существует.")
            self.warn_label.show()
            return False
        self.warn_label.hide()
        return True


# ── Page ──────────────────────────────────────────────────────────────────────

class Zapret1UserPresetsPage(BasePage):
    back_clicked    = pyqtSignal()
    preset_switched = pyqtSignal(str)
    preset_created  = pyqtSignal(str)
    preset_deleted  = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__("Мои пресеты", "", parent)
        self.parent_app = parent

        self._ui_dirty = True
        self._file_watcher: QFileSystemWatcher | None = None
        self._watcher_active = False

        self._reload_timer = QTimer(self)
        self._reload_timer.setSingleShot(True)
        self._reload_timer.timeout.connect(self._reload_from_watcher)

        self._build_ui()

        # Subscribe to preset store signals
        try:
            from preset_zapret1.preset_store import PresetStoreV1
            store = PresetStoreV1.instance()
            store.presets_changed.connect(self._on_store_changed)
            store.preset_switched.connect(self._on_store_switched)
        except Exception:
            pass

    # ── store signals ─────────────────────────────────────────────────────────

    def _on_store_changed(self):
        self._ui_dirty = True
        if self.isVisible():
            self._load_presets()

    def _on_store_switched(self, _name: str):
        self._ui_dirty = True
        if self.isVisible():
            self._load_presets()

    # ── file watcher ──────────────────────────────────────────────────────────

    def _start_watching(self):
        try:
            if self._watcher_active:
                return
            from preset_zapret1.preset_storage import get_presets_dir_v1
            presets_dir = get_presets_dir_v1()
            presets_dir.mkdir(parents=True, exist_ok=True)
            if not self._file_watcher:
                self._file_watcher = QFileSystemWatcher(self)
                self._file_watcher.directoryChanged.connect(self._schedule_reload)
            dir_str = str(presets_dir)
            if dir_str not in self._file_watcher.directories():
                self._file_watcher.addPath(dir_str)
            self._watcher_active = True
        except Exception as e:
            log(f"V1 presets watcher start error: {e}", "DEBUG")

    def _stop_watching(self):
        if not self._watcher_active or not self._file_watcher:
            return
        paths = self._file_watcher.directories()
        if paths:
            self._file_watcher.removePaths(paths)
        self._watcher_active = False

    def _schedule_reload(self, *_):
        self._reload_timer.stop()
        self._reload_timer.start(400)

    def _reload_from_watcher(self):
        if not self.isVisible():
            return
        try:
            from preset_zapret1.preset_store import PresetStoreV1
            PresetStoreV1.instance().refresh()
        except Exception:
            self._load_presets()

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def showEvent(self, event):
        super().showEvent(event)
        self._start_watching()
        if self._ui_dirty:
            self._load_presets()

    def hideEvent(self, event):
        self._reload_timer.stop()
        self._stop_watching()
        super().hideEvent(event)

    # ── build UI ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        # ── header bar ──
        header = QWidget()
        header.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(8)

        if _HAS_FLUENT and TransparentPushButton:
            back_btn = TransparentPushButton()
            back_btn.setIcon(FIF.PAGE_LEFT)
            back_btn.setText("Управление")
            back_btn.clicked.connect(self.back_clicked.emit)
            hl.addWidget(back_btn)

        hl.addStretch()

        if _HAS_FLUENT and PrimaryToolButton:
            self.create_btn = PrimaryToolButton(FIF.ADD)
            self.create_btn.setFixedSize(36, 36)
            self.create_btn.setToolTip("Создать новый пресет")
        else:
            from PyQt6.QtWidgets import QPushButton
            self.create_btn = QPushButton("+")  # type: ignore
        self.create_btn.clicked.connect(self._on_create_clicked)
        hl.addWidget(self.create_btn)

        self.add_widget(header)
        self.add_spacing(12)

        # ── cards container via SettingCardGroup ──
        self._group = SettingCardGroup("Пресеты", self)
        self.add_widget(self._group)

    # ── data ─────────────────────────────────────────────────────────────────

    def _load_presets(self):
        self._ui_dirty = False
        try:
            from preset_zapret1.preset_store import PresetStoreV1
            store  = PresetStoreV1.instance()
            names  = store.get_preset_names()
            active = store.get_active_preset_name() or ""
        except Exception as e:
            log(f"V1 presets load error: {e}", "ERROR")
            return

        # Remove old cards from the group's layout
        layout = self._group.cardLayout
        while layout.count():
            item = layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        if not names:
            placeholder = CaptionLabel("Нет пресетов. Нажмите «+», чтобы создать первый.")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(placeholder)
            self._group.adjustSize()
            return

        for name in names:
            card = _PresetCard(name, name == active, self._group)
            card.activate_requested.connect(self._on_activate)
            card.rename_requested.connect(self._on_rename)
            card.delete_requested.connect(self._on_delete)
            self._group.addSettingCard(card)

    # ── actions ───────────────────────────────────────────────────────────────

    def _on_activate(self, name: str):
        try:
            from preset_zapret1 import PresetManagerV1

            def _reload():
                try:
                    app = self.parent_app
                    if app and hasattr(app, "dpi_controller"):
                        ctrl = app.dpi_controller
                        if ctrl and hasattr(ctrl, "is_running") and ctrl.is_running():
                            ctrl.restart_dpi()
                except Exception:
                    pass

            mgr = PresetManagerV1(on_dpi_reload_needed=_reload)
            if mgr.switch_preset(name, reload_dpi=True):
                log(f"V1 preset activated: '{name}'", "INFO")
                self.preset_switched.emit(name)
                self._load_presets()
            else:
                if InfoBar:
                    InfoBar.warning(title="Ошибка",
                                    content=f"Не удалось активировать «{name}».",
                                    parent=self.window())
        except Exception as e:
            log(f"V1 activate error: {e}", "ERROR")
            if InfoBar:
                InfoBar.error(title="Ошибка", content=str(e), parent=self.window())

    def _on_create_clicked(self):
        try:
            from preset_zapret1.preset_store import PresetStoreV1
            existing = PresetStoreV1.instance().get_preset_names()
        except Exception:
            existing = []

        if not _HAS_FLUENT or MessageBoxBase is object:
            from PyQt6.QtWidgets import QInputDialog
            name, ok = QInputDialog.getText(self, "Создать пресет", "Название:")
            if ok and name.strip():
                self._create_preset(name.strip())
            return

        dlg = _CreatePresetDialog(existing, self.window())
        if dlg.exec():
            name = dlg.name_edit.text().strip()
            if name:
                self._create_preset(name)

    def _create_preset(self, name: str):
        try:
            from preset_zapret1 import PresetManagerV1
            mgr = PresetManagerV1()
            preset = mgr.create_preset(name, from_current=True)
            if preset:
                log(f"V1 preset created: '{name}'", "INFO")
                self.preset_created.emit(name)
                self._load_presets()
                if InfoBar:
                    InfoBar.success(title="Пресет создан",
                                    content=f"«{name}» создан.",
                                    parent=self.window())
            else:
                if InfoBar:
                    InfoBar.error(title="Ошибка",
                                  content=f"Не удалось создать «{name}».",
                                  parent=self.window())
        except Exception as e:
            log(f"V1 create error: {e}", "ERROR")
            if InfoBar:
                InfoBar.error(title="Ошибка", content=str(e), parent=self.window())

    def _on_rename(self, name: str):
        try:
            from preset_zapret1.preset_store import PresetStoreV1
            existing = PresetStoreV1.instance().get_preset_names()
        except Exception:
            existing = []

        if not _HAS_FLUENT or MessageBoxBase is object:
            from PyQt6.QtWidgets import QInputDialog
            new_name, ok = QInputDialog.getText(self, "Переименовать", "Новое имя:", text=name)
            if ok and new_name.strip() and new_name.strip() != name:
                self._rename_preset(name, new_name.strip())
            return

        dlg = _RenamePresetDialog(name, existing, self.window())
        if dlg.exec():
            new_name = dlg.name_edit.text().strip()
            if new_name and new_name != name:
                self._rename_preset(name, new_name)

    def _rename_preset(self, old_name: str, new_name: str):
        try:
            from preset_zapret1 import PresetManagerV1
            mgr = PresetManagerV1()
            if mgr.rename_preset(old_name, new_name):
                log(f"V1 preset renamed: '{old_name}' → '{new_name}'", "INFO")
                self._load_presets()
            else:
                if InfoBar:
                    InfoBar.error(title="Ошибка",
                                  content="Не удалось переименовать пресет.",
                                  parent=self.window())
        except Exception as e:
            log(f"V1 rename error: {e}", "ERROR")
            if InfoBar:
                InfoBar.error(title="Ошибка", content=str(e), parent=self.window())

    def _on_delete(self, name: str):
        if MessageBox:
            box = MessageBox(
                "Удалить пресет",
                f"Вы уверены, что хотите удалить «{name}»?\nЭто действие нельзя отменить.",
                self.window(),
            )
            box.yesButton.setText("Удалить")
            box.cancelButton.setText("Отмена")
            if not box.exec():
                return

        try:
            from preset_zapret1 import PresetManagerV1
            mgr = PresetManagerV1()
            if mgr.delete_preset(name):
                log(f"V1 preset deleted: '{name}'", "INFO")
                self.preset_deleted.emit(name)
                self._load_presets()
                if InfoBar:
                    InfoBar.success(title="Удалено",
                                    content=f"«{name}» удалён.",
                                    parent=self.window())
            else:
                if InfoBar:
                    InfoBar.warning(title="Ошибка",
                                    content=f"Не удалось удалить «{name}».",
                                    parent=self.window())
        except Exception as e:
            log(f"V1 delete error: {e}", "ERROR")
            if InfoBar:
                InfoBar.error(title="Ошибка", content=str(e), parent=self.window())

    def update_current_strategy(self, name: str):
        pass

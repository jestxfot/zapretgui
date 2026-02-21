# ui/pages/zapret1/user_presets_page.py
"""Zapret 1 user presets page (robust fallback implementation)."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QFileSystemWatcher
from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QSizePolicy,
    QLabel,
    QPushButton,
    QScrollArea,
    QInputDialog,
    QMessageBox,
)

from ui.pages.base_page import BasePage
from log import log

try:
    from qfluentwidgets import CaptionLabel, BodyLabel
except Exception:
    CaptionLabel = QLabel  # type: ignore
    BodyLabel = QLabel  # type: ignore


class _PresetRow(QWidget):
    """Single row in presets list."""

    activate_requested = pyqtSignal(str)
    rename_requested = pyqtSignal(str)
    reset_requested = pyqtSignal(str)
    delete_requested = pyqtSignal(str)

    def __init__(self, name: str, is_active: bool, parent=None):
        super().__init__(parent)
        self._name = str(name or "")
        self._is_active = bool(is_active)

        self.setObjectName("v1PresetRow")
        self.setStyleSheet(
            """
            QWidget#v1PresetRow {
                border: 1px solid rgba(127, 127, 127, 0.35);
                border-radius: 8px;
                background: transparent;
            }
            """
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)

        name_lbl = BodyLabel(self._name)
        name_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(name_lbl, 1)

        if self._is_active:
            active_lbl = CaptionLabel("Активен")
            active_lbl.setStyleSheet("color: #60cdff;")
            layout.addWidget(active_lbl)

        self._activate_btn = QPushButton("Активировать")
        self._activate_btn.clicked.connect(lambda: self.activate_requested.emit(self._name))
        self._activate_btn.setVisible(not self._is_active)
        layout.addWidget(self._activate_btn)

        self._rename_btn = QPushButton("Переим.")
        self._rename_btn.clicked.connect(lambda: self.rename_requested.emit(self._name))
        layout.addWidget(self._rename_btn)

        self._reset_btn = QPushButton("Сброс")
        self._reset_btn.clicked.connect(lambda: self.reset_requested.emit(self._name))
        layout.addWidget(self._reset_btn)

        self._delete_btn = QPushButton("Удалить")
        self._delete_btn.clicked.connect(lambda: self.delete_requested.emit(self._name))
        self._delete_btn.setEnabled(not self._is_active)
        layout.addWidget(self._delete_btn)


class Zapret1UserPresetsPage(BasePage):
    back_clicked = pyqtSignal()
    preset_switched = pyqtSignal(str)
    preset_created = pyqtSignal(str)
    preset_deleted = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__("Мои пресеты", "", parent)
        self.parent_app = parent

        self._ui_dirty = True
        self._bulk_reset_running = False
        self._file_watcher: QFileSystemWatcher | None = None
        self._watcher_active = False

        self._reload_timer = QTimer(self)
        self._reload_timer.setSingleShot(True)
        self._reload_timer.timeout.connect(self._reload_from_watcher)

        self._build_ui()

        try:
            from preset_zapret1.preset_store import PresetStoreV1

            store = PresetStoreV1.instance()
            store.presets_changed.connect(self._on_store_changed)
            store.preset_switched.connect(self._on_store_switched)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Signals from store
    # ------------------------------------------------------------------

    def _on_store_changed(self):
        self._ui_dirty = True
        if self._bulk_reset_running:
            return
        if self.isVisible():
            self._load_presets()

    def _on_store_switched(self, _name: str):
        self._ui_dirty = True
        if self._bulk_reset_running:
            return
        if self.isVisible():
            self._load_presets()

    # ------------------------------------------------------------------
    # File watcher
    # ------------------------------------------------------------------

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

            path = str(presets_dir)
            if path not in self._file_watcher.directories():
                self._file_watcher.addPath(path)

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

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def showEvent(self, event):
        super().showEvent(event)
        self._start_watching()

        try:
            from preset_zapret1 import ensure_default_preset_exists_v1
            from preset_zapret1.preset_store import PresetStoreV1

            store = PresetStoreV1.instance()
            if not store.get_preset_names() and ensure_default_preset_exists_v1():
                store.refresh()
        except Exception:
            pass

        if self._ui_dirty:
            self._load_presets()

    def hideEvent(self, event):
        self._reload_timer.stop()
        self._stop_watching()
        super().hideEvent(event)

    # ------------------------------------------------------------------
    # UI build
    # ------------------------------------------------------------------

    def _build_ui(self):
        header = QWidget()
        header.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(8)

        back_btn = QPushButton("← Управление")
        back_btn.clicked.connect(self.back_clicked.emit)
        hl.addWidget(back_btn)

        hl.addStretch()

        self.reset_all_btn = QPushButton("Сбросить все")
        self.reset_all_btn.clicked.connect(self._on_reset_all)
        hl.addWidget(self.reset_all_btn)

        self.create_btn = QPushButton("+")
        self.create_btn.setFixedSize(36, 36)
        self.create_btn.clicked.connect(self._on_create_clicked)
        hl.addWidget(self.create_btn)

        self.add_widget(header)
        self.add_spacing(8)

        self._empty_hint = CaptionLabel("")
        self._empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_hint.hide()
        self.add_widget(self._empty_hint)

        self._scroll = QScrollArea(self)
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        self._rows_host = QWidget()
        self._rows_layout = QVBoxLayout(self._rows_host)
        self._rows_layout.setContentsMargins(0, 0, 0, 0)
        self._rows_layout.setSpacing(8)
        self._rows_layout.addStretch(1)

        self._scroll.setWidget(self._rows_host)
        self.add_widget(self._scroll, 1)

    # ------------------------------------------------------------------
    # Data render
    # ------------------------------------------------------------------

    def _clear_rows(self):
        while self._rows_layout.count() > 1:
            item = self._rows_layout.takeAt(0)
            w = item.widget() if item else None
            if w is not None:
                w.setParent(None)
                w.deleteLater()

    def _load_presets(self):
        self._ui_dirty = False

        names: list[str] = []
        active = ""

        self._empty_hint.hide()
        self._clear_rows()

        try:
            from preset_zapret1.preset_store import PresetStoreV1

            store = PresetStoreV1.instance()
            names = store.get_preset_names()
            active = store.get_active_preset_name() or ""
        except Exception as e:
            log(f"V1 presets store load error: {e}", "ERROR")

        if not names:
            try:
                from preset_zapret1.preset_storage import list_presets_v1, get_active_preset_name_v1

                names = list_presets_v1()
                active = active or (get_active_preset_name_v1() or "")
                if names:
                    log("V1 presets page: using filesystem fallback list", "WARNING")
            except Exception as e:
                log(f"V1 presets filesystem fallback error: {e}", "ERROR")

        if not names:
            self._empty_hint.setText("Нет пресетов. Нажмите «+», чтобы создать первый.")
            self._empty_hint.show()
            return

        added = 0
        for name in names:
            try:
                row = _PresetRow(name, name == active, self._rows_host)
                row.activate_requested.connect(self._on_activate)
                row.rename_requested.connect(self._on_rename)
                row.reset_requested.connect(self._on_reset)
                row.delete_requested.connect(self._on_delete)
                self._rows_layout.insertWidget(self._rows_layout.count() - 1, row)
                added += 1
            except Exception as e:
                log(f"V1 presets row build error for '{name}': {e}", "ERROR")

        if added == 0:
            self._empty_hint.setText("Не удалось отрисовать пресеты (ошибка UI).")
            self._empty_hint.show()
        else:
            log(f"V1 presets page rendered rows: {added}", "DEBUG")

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

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
                self.preset_switched.emit(name)
                self._load_presets()
                return
            QMessageBox.warning(self, "Ошибка", f"Не удалось активировать '{name}'.")
        except Exception as e:
            log(f"V1 activate error: {e}", "ERROR")
            QMessageBox.critical(self, "Ошибка", str(e))

    def _on_create_clicked(self):
        name, ok = QInputDialog.getText(self, "Создать пресет", "Название:")
        if ok and name.strip():
            self._create_preset(name.strip())

    def _create_preset(self, name: str):
        try:
            from preset_zapret1 import PresetManagerV1

            mgr = PresetManagerV1()
            preset = mgr.create_preset(name, from_current=True)
            if preset:
                self.preset_created.emit(name)
                self._load_presets()
            else:
                QMessageBox.warning(self, "Ошибка", f"Не удалось создать '{name}'.")
        except Exception as e:
            log(f"V1 create error: {e}", "ERROR")
            QMessageBox.critical(self, "Ошибка", str(e))

    def _on_rename(self, name: str):
        new_name, ok = QInputDialog.getText(self, "Переименовать", "Новое имя:", text=name)
        if ok and new_name.strip() and new_name.strip() != name:
            self._rename_preset(name, new_name.strip())

    def _rename_preset(self, old_name: str, new_name: str):
        try:
            from preset_zapret1 import PresetManagerV1

            mgr = PresetManagerV1()
            if mgr.rename_preset(old_name, new_name):
                self._load_presets()
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось переименовать пресет.")
        except Exception as e:
            log(f"V1 rename error: {e}", "ERROR")
            QMessageBox.critical(self, "Ошибка", str(e))

    def _on_reset(self, name: str):
        box = QMessageBox(self)
        box.setWindowTitle("Сбросить пресет")
        box.setText(
            f"Сбросить '{name}' к шаблону из presets_v1_template?\n\n"
            "Шаблон будет применен принудительно."
        )
        box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        box.setDefaultButton(QMessageBox.StandardButton.No)
        if box.exec() != QMessageBox.StandardButton.Yes:
            return

        try:
            from preset_zapret1 import PresetManagerV1

            mgr = PresetManagerV1()
            if mgr.reset_preset_to_default_template(name):
                self.preset_switched.emit(name)
                self._load_presets()
            else:
                QMessageBox.warning(self, "Ошибка", f"Не удалось сбросить '{name}'.")
        except Exception as e:
            log(f"V1 reset error: {e}", "ERROR")
            QMessageBox.critical(self, "Ошибка", str(e))

    def _on_reset_all(self):
        box = QMessageBox(self)
        box.setWindowTitle("Сбросить все пресеты")
        box.setText(
            "Сбросить ВСЕ пресеты к шаблонам из presets_v1_template?\n\n"
            "Активный пресет будет повторно применен в preset-zapret1.txt."
        )
        box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        box.setDefaultButton(QMessageBox.StandardButton.No)
        if box.exec() != QMessageBox.StandardButton.Yes:
            return

        self._bulk_reset_running = True
        try:
            from preset_zapret1 import PresetManagerV1

            mgr = PresetManagerV1()
            success_count, total_count, failed = mgr.reset_all_presets_to_default_templates()

            self._load_presets()
            self._show_reset_all_result(success_count, total_count)

            if failed:
                QMessageBox.warning(
                    self,
                    "Частично выполнено",
                    f"Сброшено {success_count} из {total_count}.",
                )
            else:
                QMessageBox.information(
                    self,
                    "Готово",
                    f"Сброшено {success_count} из {total_count}.",
                )
        except Exception as e:
            log(f"V1 bulk reset error: {e}", "ERROR")
            QMessageBox.critical(self, "Ошибка", str(e))
        finally:
            self._bulk_reset_running = False

    def _show_reset_all_result(self, success_count: int, total_count: int):
        ok = int(success_count or 0)
        total = int(total_count or 0)
        self.reset_all_btn.setText(f"{ok}/{total}")
        QTimer.singleShot(2500, self._restore_reset_all_button_label)

    def _restore_reset_all_button_label(self):
        self.reset_all_btn.setText("Сбросить все")

    def _on_delete(self, name: str):
        box = QMessageBox(self)
        box.setWindowTitle("Удалить пресет")
        box.setText(f"Вы уверены, что хотите удалить '{name}'?\nЭто действие нельзя отменить.")
        box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        box.setDefaultButton(QMessageBox.StandardButton.No)
        if box.exec() != QMessageBox.StandardButton.Yes:
            return

        try:
            from preset_zapret1 import PresetManagerV1

            mgr = PresetManagerV1()
            if mgr.delete_preset(name):
                self.preset_deleted.emit(name)
                self._load_presets()
            else:
                QMessageBox.warning(self, "Ошибка", f"Не удалось удалить '{name}'.")
        except Exception as e:
            log(f"V1 delete error: {e}", "ERROR")
            QMessageBox.critical(self, "Ошибка", str(e))

    def update_current_strategy(self, name: str):
        _ = name

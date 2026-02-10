# ui/pages/control_page.py
"""Страница управления - запуск/остановка DPI"""

import os

from PyQt6.QtCore import Qt, QSize, QObject, pyqtSignal, QThread
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QSizePolicy, QMessageBox
import qtawesome as qta

from .base_page import BasePage
from ui.sidebar import SettingsCard, SettingsRow, ActionButton, StatusIndicator, PulsingDot
from ui.pages.strategies_page_base import ResetActionButton


# Стиль для индикатора загрузки (бегающая полоска)
PROGRESS_STYLE = """
QProgressBar {
    background-color: rgba(255, 255, 255, 0.05);
    border: none;
    border-radius: 2px;
    height: 4px;
    text-align: center;
}
QProgressBar::chunk {
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 transparent,
        stop:0.3 #60cdff,
        stop:0.5 #60cdff,
        stop:0.7 #60cdff,
        stop:1 transparent
    );
    border-radius: 2px;
}
"""


class _CertificateInstallWorker(QObject):
    finished = pyqtSignal(bool, str)  # success, message

    def run(self) -> None:
        try:
            from startup.certificate_installer import reset_certificate_declined_flag, auto_install_certificate

            # Если ранее была выставлена блокировка автоустановки, ручная установка должна работать.
            reset_certificate_declined_flag()
            success, message = auto_install_certificate(silent=True)
            self.finished.emit(bool(success), str(message))
        except Exception as e:
            self.finished.emit(False, str(e))


class BigActionButton(ActionButton):
    """Большая кнопка действия"""
    
    def __init__(self, text: str, icon_name: str = None, accent: bool = False, parent=None):
        super().__init__(text, icon_name, accent, parent)
        self.setFixedHeight(48)
        self.setIconSize(QSize(20, 20))
        
    def _update_style(self):
        if self.accent:
            # Акцентная кнопка - голубая
            if self._hovered:
                bg = "rgba(96, 205, 255, 0.9)"
            else:
                bg = "#60cdff"
            text_color = "#000000"
        else:
            # Обычная кнопка - нейтральная
            if self._hovered:
                bg = "rgba(255, 255, 255, 0.15)"
            else:
                bg = "rgba(255, 255, 255, 0.08)"
            text_color = "#ffffff"
            
        self.setStyleSheet(f"""
            QPushButton {{
                background: {bg};
                border: none;
                border-radius: 6px;
                color: {text_color};
                padding: 0 24px;
                font-size: 14px;
                font-weight: 600;
                font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
            }}
        """)


class StopButton(BigActionButton):
    """Кнопка остановки (нейтральная)"""
    
    def _update_style(self):
        # Нейтральная серая кнопка
        if self._hovered:
            bg = "rgba(255, 255, 255, 0.15)"
        else:
            bg = "rgba(255, 255, 255, 0.08)"
            
        self.setStyleSheet(f"""
            QPushButton {{
                background: {bg};
                border: none;
                border-radius: 6px;
                color: #ffffff;
                padding: 0 24px;
                font-size: 14px;
                font-weight: 600;
                font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
            }}
        """)


class ControlPage(BasePage):
    """Страница управления DPI"""
    
    def __init__(self, parent=None):
        super().__init__("Управление и настройки Zapret 2", "Здесь Вы можете управлять основным ядром программы winws2.exe. Вы можете быстро выбрать из готовых пресетов-конфигов (ранее bat файлы). Если требуется более детальная настройка для каждой категории - перейдите в прямой запуск.", parent)
        
        self._build_ui()
        self._update_stop_winws_button_text()
        
    def _build_ui(self):
        # Статус работы
        self.add_section_title("Статус работы")
        
        status_card = SettingsCard()
        
        status_layout = QHBoxLayout()
        status_layout.setSpacing(16)
        
        # Пульсирующая точка статуса
        self.status_dot = PulsingDot()
        status_layout.addWidget(self.status_dot)
        
        # Текст статуса
        status_text_layout = QVBoxLayout()
        status_text_layout.setSpacing(2)
        
        self.status_title = QLabel("Проверка...")
        self.status_title.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 15px;
                font-weight: 600;
            }
        """)
        status_text_layout.addWidget(self.status_title)
        
        self.status_desc = QLabel("Определение состояния процесса")
        self.status_desc.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.6);
                font-size: 12px;
            }
        """)
        status_text_layout.addWidget(self.status_desc)
        
        status_layout.addLayout(status_text_layout, 1)
        status_card.add_layout(status_layout)
        self.add_widget(status_card)
        
        self.add_spacing(16)
        
        # Управление
        self.add_section_title("Управление Zapret")
        
        control_card = SettingsCard()

        # Индикатор загрузки (бегающая полоска) - показываем рядом с кнопками управления
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet(PROGRESS_STYLE)
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(0)  # Indeterminate mode
        self.progress_bar.setVisible(False)
        control_card.add_widget(self.progress_bar)

        # Метка статуса загрузки
        self.loading_label = QLabel("")
        self.loading_label.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.6);
                font-size: 12px;
                padding-top: 4px;
            }
        """)
        self.loading_label.setVisible(False)
        control_card.add_widget(self.loading_label)
        
        # Кнопки управления
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(12)
        
        self.start_btn = BigActionButton("Запустить Zapret", "fa5s.play", accent=True)
        buttons_layout.addWidget(self.start_btn)
        
        # Кнопка остановки только winws.exe / winws2.exe (в зависимости от режима)
        self.stop_winws_btn = StopButton("Остановить только winws.exe", "fa5s.stop")
        self.stop_winws_btn.setVisible(False)
        buttons_layout.addWidget(self.stop_winws_btn)
        
        # Кнопка полного выхода (остановка + закрытие программы)
        self.stop_and_exit_btn = StopButton("Остановить и закрыть программу", "fa5s.power-off")
        self.stop_and_exit_btn.setVisible(False)
        buttons_layout.addWidget(self.stop_and_exit_btn)
        
        buttons_layout.addStretch()
        control_card.add_layout(buttons_layout)
        
        self.add_widget(control_card)
        
        self.add_spacing(16)
        
        # Текущая стратегия
        self.add_section_title("Текущая стратегия")
        
        strategy_card = SettingsCard()
        
        strategy_layout = QHBoxLayout()
        strategy_layout.setSpacing(12)
        
        self.strategy_icon = QLabel()
        try:
            from ui.fluent_icons import fluent_pixmap
            self.strategy_icon.setPixmap(fluent_pixmap('fa5s.cog', 20))
        except:
            self.strategy_icon.setPixmap(qta.icon('fa5s.cog', color='#60cdff').pixmap(20, 20))
        self.strategy_icon.setFixedSize(24, 24)
        strategy_layout.addWidget(self.strategy_icon)
        
        strategy_text_layout = QVBoxLayout()
        strategy_text_layout.setSpacing(2)
        
        self.strategy_label = QLabel("Не выбрана")
        self.strategy_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 14px;
                font-weight: 500;
            }
        """)
        self.strategy_label.setWordWrap(True)
        self.strategy_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        strategy_text_layout.addWidget(self.strategy_label)
        
        self.strategy_desc = QLabel("Выберите стратегию в разделе «Стратегии»")
        self.strategy_desc.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.5);
                font-size: 11px;
            }
        """)
        strategy_text_layout.addWidget(self.strategy_desc)
        
        strategy_layout.addLayout(strategy_text_layout, 1)
        strategy_card.add_layout(strategy_layout)
        
        self.add_widget(strategy_card)
        
        self.add_spacing(16)

        # Настройки программы (бывшие пункты Alt-меню "Настройки")
        self.add_section_title("Настройки программы")

        program_settings_card = SettingsCard()

        try:
            from ui.pages.dpi_settings_page import Win11ToggleSwitch
        except Exception:
            Win11ToggleSwitch = None  # type: ignore[assignment]

        # Автозагрузка DPI
        auto_row = SettingsRow(
            "fa5s.bolt",
            "Автозагрузка DPI",
            "Запускать Zapret автоматически при старте программы",
        )
        self.auto_dpi_toggle = Win11ToggleSwitch() if Win11ToggleSwitch else ActionButton("Вкл/Выкл")
        self.auto_dpi_toggle.setProperty("noDrag", True)
        if hasattr(self.auto_dpi_toggle, "toggled"):
            self.auto_dpi_toggle.toggled.connect(self._on_auto_dpi_toggled)
        auto_row.set_control(self.auto_dpi_toggle)
        program_settings_card.add_widget(auto_row)

        # Windows Defender
        defender_row = SettingsRow(
            "fa5s.shield-alt",
            "Отключить Windows Defender",
            "Требуются права администратора",
        )
        self.defender_toggle = Win11ToggleSwitch() if Win11ToggleSwitch else ActionButton("Вкл/Выкл")
        self.defender_toggle.setProperty("noDrag", True)
        if hasattr(self.defender_toggle, "toggled"):
            self.defender_toggle.toggled.connect(self._on_defender_toggled)
        defender_row.set_control(self.defender_toggle)
        program_settings_card.add_widget(defender_row)

        # MAX blocker
        max_row = SettingsRow(
            "fa5s.ban",
            "Блокировать установку MAX",
            "Блокирует запуск/установку MAX и домены в hosts",
        )
        self.max_block_toggle = Win11ToggleSwitch() if Win11ToggleSwitch else ActionButton("Вкл/Выкл")
        self.max_block_toggle.setProperty("noDrag", True)
        if hasattr(self.max_block_toggle, "toggled"):
            self.max_block_toggle.toggled.connect(self._on_max_blocker_toggled)
        max_row.set_control(self.max_block_toggle)
        program_settings_card.add_widget(max_row)

        # Сброс программы
        reset_row = SettingsRow(
            "fa5s.undo",
            "Сбросить программу",
            "Очистить кэш проверок запуска (без удаления пресетов/настроек)",
        )
        self.reset_program_btn = ResetActionButton("Сбросить", confirm_text="Сбросить?")
        self.reset_program_btn.setProperty("noDrag", True)
        self.reset_program_btn.reset_confirmed.connect(self._on_reset_program_clicked)
        reset_row.set_control(self.reset_program_btn)
        program_settings_card.add_widget(reset_row)

        # Установка сертификата (необязательно)
        cert_row = SettingsRow(
            "fa5s.certificate",
            "Установить сертификат",
            "Необязательно. Добавляет сертификат установщика Zapret GUI в исключения антивируса (может помочь против блокировок Defender. НЕ действует на Касперский!)",
        )
        self.install_cert_btn = ActionButton("Установить")
        self.install_cert_btn.setProperty("noDrag", True)
        self.install_cert_btn.clicked.connect(self._on_install_certificate_clicked)
        cert_row.set_control(self.install_cert_btn)
        program_settings_card.add_widget(cert_row)

        self.add_widget(program_settings_card)

        self.add_spacing(16)
        
        # Дополнительные действия
        self.add_section_title("Дополнительно")
        
        extra_card = SettingsCard()
        
        extra_layout = QHBoxLayout()
        extra_layout.setSpacing(8)
        
        self.test_btn = ActionButton("Тест соединения", "fa5s.wifi")
        extra_layout.addWidget(self.test_btn)
        
        self.folder_btn = ActionButton("Открыть папку", "fa5s.folder-open")
        extra_layout.addWidget(self.folder_btn)
        
        extra_layout.addStretch()
        extra_card.add_layout(extra_layout)
        
        self.add_widget(extra_card)

        # Первичная синхронизация состояния тогглов с текущими настройками
        self._sync_program_settings()

        self._cert_install_thread = None
        self._cert_install_worker = None

    def _on_install_certificate_clicked(self) -> None:
        try:
            from startup.certificate_installer import is_certificate_installed
        except Exception as e:
            QMessageBox.critical(self, "Сертификат", f"Не удалось загрузить установщик сертификата:\n\n{e}")
            return

        thumbprint = "F507DDA6CB772F4332ECC2C5686623F39D9DA450"
        if is_certificate_installed(thumbprint):
            QMessageBox.information(self, "Сертификат", "Сертификат уже установлен.")
            return

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Установка сертификата")
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setText("Установить корневой сертификат Zapret Developer?")
        msg_box.setInformativeText(
            "Это необязательно. После установки Windows будет доверять сертификатам, "
            "выпущенным этим центром сертификации, для текущего пользователя.\n\n"
            "Продолжить?"
        )
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)
        if msg_box.exec() != QMessageBox.StandardButton.Yes:
            return

        if self._cert_install_thread is not None:
            return

        old_text = self.install_cert_btn.text()
        self.install_cert_btn.setEnabled(False)
        self.install_cert_btn.setText("Установка...")
        self._set_status("Установка сертификата...")

        self._cert_install_thread = QThread()
        self._cert_install_worker = _CertificateInstallWorker()
        self._cert_install_worker.moveToThread(self._cert_install_thread)

        self._cert_install_thread.started.connect(self._cert_install_worker.run)

        def _finish(success: bool, message: str) -> None:
            try:
                self.install_cert_btn.setEnabled(True)
                self.install_cert_btn.setText(old_text)

                if success:
                    self._set_status("Сертификат установлен")
                    QMessageBox.information(self, "Сертификат", message or "Сертификат установлен")
                else:
                    self._set_status("Не удалось установить сертификат")
                    QMessageBox.critical(self, "Сертификат", message or "Не удалось установить сертификат")
            finally:
                try:
                    self._cert_install_thread.quit()
                    self._cert_install_thread.wait(3000)
                except Exception:
                    pass
                try:
                    self._cert_install_worker.deleteLater()
                except Exception:
                    pass
                try:
                    self._cert_install_thread.deleteLater()
                except Exception:
                    pass
                self._cert_install_thread = None
                self._cert_install_worker = None

        self._cert_install_worker.finished.connect(_finish)
        self._cert_install_thread.start()

    def showEvent(self, event):
        super().showEvent(event)
        # Обновляем состояние тогглов при каждом показе страницы
        try:
            self._sync_program_settings()
        except Exception:
            pass

    def _set_toggle_checked(self, toggle, checked: bool) -> None:
        """Устанавливает состояние Win11ToggleSwitch без побочных эффектов анимации/сигналов."""
        try:
            toggle.blockSignals(True)
        except Exception:
            pass

        try:
            if hasattr(toggle, "setChecked"):
                toggle.setChecked(bool(checked))
        except Exception:
            pass

        # Win11ToggleSwitch: обновляем позицию круга без анимации (как в Win11ToggleRow)
        try:
            toggle._circle_position = (toggle.width() - 18) if checked else 4.0  # type: ignore[attr-defined]
            toggle.update()
        except Exception:
            pass

        try:
            toggle.blockSignals(False)
        except Exception:
            pass

    def _sync_program_settings(self) -> None:
        """Синхронизирует UI с текущими настройками (реестр/система)."""
        # Автозагрузка DPI
        try:
            from config import get_dpi_autostart
            self._set_toggle_checked(self.auto_dpi_toggle, bool(get_dpi_autostart()))
        except Exception:
            pass

        # Windows Defender (реальное состояние системы)
        try:
            from altmenu.defender_manager import WindowsDefenderManager
            self._set_toggle_checked(self.defender_toggle, bool(WindowsDefenderManager().is_defender_disabled()))
        except Exception:
            pass

        # MAX blocker (состояние из реестра GUI)
        try:
            from altmenu.max_blocker import is_max_blocked
            self._set_toggle_checked(self.max_block_toggle, bool(is_max_blocked()))
        except Exception:
            pass

    def _set_status(self, msg: str) -> None:
        try:
            if hasattr(self.parent_app, "set_status"):
                self.parent_app.set_status(msg)
        except Exception:
            pass

    def _on_auto_dpi_toggled(self, enabled: bool) -> None:
        try:
            from config import set_dpi_autostart
            set_dpi_autostart(bool(enabled))

            msg = (
                "DPI будет включаться автоматически при старте программы"
                if enabled
                else "Автозагрузка DPI отключена"
            )
            self._set_status(msg)
            QMessageBox.information(self, "Автозагрузка DPI", msg)
        finally:
            self._sync_program_settings()

    def _on_defender_toggled(self, disable: bool) -> None:
        import ctypes

        # Требуются права администратора
        if not ctypes.windll.shell32.IsUserAnAdmin():
            QMessageBox.critical(
                self,
                "Требуются права администратора",
                "Для управления Windows Defender требуются права администратора.\n\n"
                "Перезапустите программу от имени администратора.",
            )
            self._set_toggle_checked(self.defender_toggle, not disable)
            return

        try:
            from altmenu.defender_manager import WindowsDefenderManager, set_defender_disabled

            manager = WindowsDefenderManager(status_callback=self._set_status)

            if disable:
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Отключение Windows Defender")
                msg_box.setIcon(QMessageBox.Icon.Warning)
                msg_box.setText("Вы действительно хотите отключить Windows Defender?\n\n")
                msg_box.setInformativeText(
                    "Отключение Windows Defender:\n"
                    "• Отключит защиту в реальном времени\n"
                    "• Отключит облачную защиту\n"
                    "• Отключит автоматическую отправку образцов\n"
                    "• Может потребовать перезагрузки для полного применения\n\n"
                )
                msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                msg_box.setDefaultButton(QMessageBox.StandardButton.No)

                if msg_box.exec() != QMessageBox.StandardButton.Yes:
                    self._set_toggle_checked(self.defender_toggle, False)
                    return

                self._set_status("Отключение Windows Defender...")
                success, count = manager.disable_defender()

                if success:
                    set_defender_disabled(True)
                    QMessageBox.information(
                        self,
                        "Windows Defender отключен",
                        "Windows Defender успешно отключен.\n"
                        f"Применено {count} настроек.\n\n"
                        "Для полного применения изменений может потребоваться перезагрузка.",
                    )
                else:
                    QMessageBox.critical(
                        self,
                        "Ошибка",
                        "Не удалось отключить Windows Defender.\n"
                        "Возможно, некоторые настройки заблокированы системой.",
                    )
                    self._set_toggle_checked(self.defender_toggle, False)
            else:
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Включение Windows Defender")
                msg_box.setIcon(QMessageBox.Icon.Question)
                msg_box.setText(
                    "Включить Windows Defender обратно?\n\n"
                    "Это восстановит защиту вашего компьютера."
                )
                msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                msg_box.setDefaultButton(QMessageBox.StandardButton.Yes)

                if msg_box.exec() != QMessageBox.StandardButton.Yes:
                    self._set_toggle_checked(self.defender_toggle, True)
                    return

                self._set_status("Включение Windows Defender...")
                success, count = manager.enable_defender()

                if success:
                    set_defender_disabled(False)
                    QMessageBox.information(
                        self,
                        "Windows Defender включен",
                        "Windows Defender успешно включен.\n"
                        f"Выполнено {count} операций.\n\n"
                        "Защита вашего компьютера восстановлена.",
                    )
                else:
                    QMessageBox.warning(
                        self,
                        "Частичный успех",
                        "Windows Defender включен частично.\n"
                        "Для полного восстановления может потребоваться перезагрузка.",
                    )

            self._set_status("Готово")

        except Exception as e:
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Произошла ошибка при изменении настроек Windows Defender:\n{e}",
            )
        finally:
            self._sync_program_settings()

    def _on_max_blocker_toggled(self, enable: bool) -> None:
        try:
            from altmenu.max_blocker import MaxBlockerManager

            manager = MaxBlockerManager(status_callback=self._set_status)

            if enable:
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Блокировка MAX")
                msg_box.setIcon(QMessageBox.Icon.Information)
                msg_box.setText("Включить блокировку установки и работы программы MAX?\n\nЭто действие:")
                msg_box.setInformativeText(
                    "• Заблокирует запуск max.exe, max.msi и других файлов MAX\n"
                    "• Создаст файлы-блокировки в папках установки\n"
                    "• Добавит правила блокировки в Windows Firewall (при наличии прав)\n"
                    "• Заблокирует домены MAX в файле hosts\n\n"
                    "В итоге даже если мессенджер Max поставиться будет тёмный экран, в результате чего он будет выглядеть так, будто не может подключиться к своим серверам."
                )
                msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                msg_box.setDefaultButton(QMessageBox.StandardButton.Yes)

                if msg_box.exec() != QMessageBox.StandardButton.Yes:
                    self._set_toggle_checked(self.max_block_toggle, False)
                    return

                success, message = manager.enable_blocking()

                if success:
                    QMessageBox.information(self, "Блокировка включена", message)
                else:
                    QMessageBox.warning(
                        self,
                        "Ошибка",
                        f"Не удалось полностью включить блокировку:\n{message}",
                    )
                    self._set_toggle_checked(self.max_block_toggle, False)
            else:
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Отключение блокировки MAX")
                msg_box.setIcon(QMessageBox.Icon.Question)
                msg_box.setText(
                    "Отключить блокировку программы MAX?\n\n"
                    "Это удалит все созданные блокировки и правила."
                )
                msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                msg_box.setDefaultButton(QMessageBox.StandardButton.No)

                if msg_box.exec() != QMessageBox.StandardButton.Yes:
                    self._set_toggle_checked(self.max_block_toggle, True)
                    return

                success, message = manager.disable_blocking()
                if success:
                    QMessageBox.information(self, "Блокировка отключена", message)
                else:
                    QMessageBox.warning(
                        self,
                        "Ошибка",
                        f"Не удалось полностью отключить блокировку:\n{message}",
                    )

            self._set_status("Готово")

        except Exception as e:
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Ошибка при переключении блокировки MAX:\n{e}",
            )
        finally:
            self._sync_program_settings()

    def _on_reset_program_clicked(self) -> None:
        from startup.check_cache import startup_cache
        from log import log

        try:
            startup_cache.invalidate_cache()
            log("Кэш проверок запуска очищен пользователем", "INFO")
            self._set_status("Кэш проверок запуска очищен")
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось очистить кэш: {e}")
            log(f"Ошибка очистки кэша: {e}", "❌ ERROR")
        finally:
            self._sync_program_settings()

    def _update_stop_winws_button_text(self):
        """Обновляет подпись кнопки остановки (winws.exe vs winws2.exe) по текущему режиму."""
        try:
            from strategy_menu import get_strategy_launch_method
            from config import get_winws_exe_for_method

            method = get_strategy_launch_method()
            exe_name = os.path.basename(get_winws_exe_for_method(method)) or "winws.exe"
            self.stop_winws_btn.setText(f"Остановить только {exe_name}")
        except Exception:
            # Fallback на старую подпись (не ломаем UI из-за циклических импортов/ошибок реестра)
            self.stop_winws_btn.setText("Остановить только winws.exe")
        
    def set_loading(self, loading: bool, text: str = ""):
        """Показывает/скрывает индикатор загрузки и блокирует кнопки"""
        self.progress_bar.setVisible(loading)
        self.loading_label.setVisible(loading and bool(text))
        self.loading_label.setText(text)
        
        # Блокируем/разблокируем кнопки
        self.start_btn.setEnabled(not loading)
        self.stop_winws_btn.setEnabled(not loading)
        self.stop_and_exit_btn.setEnabled(not loading)
        
        # Обновляем стиль заблокированных кнопок
        if loading:
            disabled_style = """
                QPushButton {
                    background: rgba(255, 255, 255, 0.03);
                    border: none;
                    border-radius: 6px;
                    color: rgba(255, 255, 255, 0.3);
                    padding: 0 24px;
                    font-size: 14px;
                    font-weight: 600;
                    font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
                }
            """
            self.start_btn.setStyleSheet(disabled_style)
            self.stop_winws_btn.setStyleSheet(disabled_style)
            self.stop_and_exit_btn.setStyleSheet(disabled_style)
        else:
            # Восстанавливаем стили
            self.start_btn._update_style()
            self.stop_winws_btn._update_style()
            self.stop_and_exit_btn._update_style()
        
    def update_status(self, is_running: bool):
        """Обновляет отображение статуса"""
        if is_running:
            self.status_title.setText("Zapret работает")
            self.status_desc.setText("Обход блокировок активен")
            self.status_dot.set_color('#6ccb5f')
            self.status_dot.start_pulse()
            self.start_btn.setVisible(False)
            self._update_stop_winws_button_text()
            self.stop_winws_btn.setVisible(True)
            self.stop_and_exit_btn.setVisible(True)
        else:
            self.status_title.setText("Zapret остановлен")
            self.status_desc.setText("Нажмите «Запустить» для активации")
            self.status_dot.set_color('#ff6b6b')
            self.status_dot.stop_pulse()
            self.start_btn.setVisible(True)
            self.stop_winws_btn.setVisible(False)
            self.stop_and_exit_btn.setVisible(False)
            
    def update_strategy(self, name: str):
        """Обновляет отображение текущей стратегии"""
        self._update_stop_winws_button_text()
        # Direct modes: show summary of active categories (top-2 + +N ещё).
        try:
            from strategy_menu import get_strategy_launch_method

            method = get_strategy_launch_method()
            if method in ("direct_zapret2", "direct_zapret2_orchestra", "direct_zapret1"):
                from strategy_menu import get_direct_strategy_selections
                from strategy_menu.strategies_registry import registry

                selections = get_direct_strategy_selections() or {}
                active_names: list[str] = []
                for cat_key in registry.get_all_category_keys_by_command_order():
                    sid = selections.get(cat_key, "none") or "none"
                    if sid == "none":
                        continue
                    info = registry.get_category_info(cat_key)
                    active_names.append(getattr(info, "full_name", None) or cat_key)

                if not active_names:
                    name = "Не выбрана"
                    self.strategy_label.setToolTip("")
                else:
                    if len(active_names) <= 2:
                        name = " • ".join(active_names)
                    else:
                        name = " • ".join(active_names[:2]) + f" +{len(active_names) - 2} ещё"
                    self.strategy_label.setToolTip("\n".join(active_names))
        except Exception:
            pass

        if name and name != "Автостарт DPI отключен":
            self.strategy_label.setText(name)
            self.strategy_desc.setText("Активная стратегия обхода")
        else:
            self.strategy_label.setText("Не выбрана")
            self.strategy_desc.setText("Выберите стратегию в разделе «Стратегии»")

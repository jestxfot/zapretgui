# altmenu/app_menubar.py

from PyQt6.QtWidgets import (QMenuBar, QWidget, QMessageBox,
                            QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QTextEdit, QLineEdit, QPushButton, QDialogButtonBox)
from PyQt6.QtGui     import QAction
from PyQt6.QtCore    import Qt, QThread, QSettings
import webbrowser

from config import APP_VERSION  # build_info moved to config/__init__.py
from config.urls import INFO_URL, ANDROID_URL
from .about_dialog import AboutDialog

from utils import run_hidden
from log import log, global_logger

class LogReportDialog(QDialog):
    """Диалог для ввода описания проблемы и контактов при отправке лога"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Отправка лога в техподдержку")
        self.setModal(True)
        self.setMinimumWidth(500)
        
        # Основной layout
        layout = QVBoxLayout()
        
        # Заголовок
        header_label = QLabel(
            "<h3>Отправка лога файла</h3>"
            "<p>Опишите проблему и оставьте контакты для обратной связи (необязательно):</p>"
        )
        header_label.setWordWrap(True)
        layout.addWidget(header_label)
        
        # Поле для описания проблемы
        problem_label = QLabel("Описание проблемы:")
        layout.addWidget(problem_label)
        
        self.problem_text = QTextEdit()
        self.problem_text.setPlaceholderText(
            "Опишите, что не работает или какая ошибка возникает.\n"
            "Например: Discord не открывается, показывает белый экран..."
        )
        self.problem_text.setMaximumHeight(150)
        layout.addWidget(self.problem_text)
        
        # Поле для Telegram контакта
        tg_label = QLabel("Telegram для связи (необязательно):")
        layout.addWidget(tg_label)
        
        self.tg_contact = QLineEdit()
        self.tg_contact.setPlaceholderText("@username или ссылка на профиль")
        layout.addWidget(self.tg_contact)
        
        # Информация
        info_label = QLabel(
            "<p style='color: gray; font-size: 10pt;'>"
            "💡 Ваши данные будут отправлены только в канал техподдержки<br>"
            "📋 Лог файл поможет разработчикам найти и исправить проблему"
            "</p>"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Кнопки
        button_box = QDialogButtonBox()
        
        send_button = button_box.addButton("Отправить", QDialogButtonBox.ButtonRole.AcceptRole)
        send_button.setDefault(True)
        
        cancel_button = button_box.addButton("Отмена", QDialogButtonBox.ButtonRole.RejectRole)
        
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def get_report_data(self):
        """Возвращает введенные данные"""
        return {
            'problem': self.problem_text.toPlainText().strip(),
            'telegram': self.tg_contact.text().strip()
        }


class AppMenuBar(QMenuBar):
    """
    Верхняя строка меню («Alt-меню»).
    """

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._pw = parent
        self._settings = QSettings("ZapretGUI", "Zapret") # для сохранения настроек
        self._set_status = getattr(parent, "set_status", lambda *_: None)

        """
        # === ХОСТЛИСТЫ ===
        hostlists_menu = self.addMenu("&Хостлисты")
        
        update_exclusions_action = QAction("Обновить исключения с сервера", self)
        update_exclusions_action.triggered.connect(self._update_exclusions)
        hostlists_menu.addAction(update_exclusions_action)
        
        exclude_sites_action = QAction("Добавить свой домен в исключения", self)
        exclude_sites_action.triggered.connect(self._exclude_custom_sites)
        hostlists_menu.addAction(exclude_sites_action)
        
        hostlists_menu.addSeparator()
        
        update_custom_sites_action = QAction("Обновить кастомные сайты с сервера", self)
        update_custom_sites_action.triggered.connect(self._update_custom_sites)
        hostlists_menu.addAction(update_custom_sites_action)
        
        add_custom_sites_action = QAction("Добавить свой домен в кастомные сайты", self)
        add_custom_sites_action.triggered.connect(self._add_custom_sites)
        hostlists_menu.addAction(add_custom_sites_action)
        
        hostlists_menu.addSeparator()
        """

        # -------- 2. «Справка» ---------------------------------------------
        help_menu = self.addMenu("&Справка")

        act_help = QAction("❓ Что это такое? (Руководство)", self)
        act_help.triggered.connect(self.open_info)
        help_menu.addAction(act_help)

        act_support = QAction("💬 Поддержка (запросить помощь)", self)
        act_support.triggered.connect(self.open_support)
        help_menu.addAction(act_support)

        act_support = QAction("🤖 На андроид (ByeByeDPI)", self)
        act_support.triggered.connect(self.show_byedpi_info)
        help_menu.addAction(act_support)

        act_about = QAction("ℹ О программе…", self)
        act_about.triggered.connect(lambda: AboutDialog(parent).exec())
        help_menu.addAction(act_about)

    def show_byedpi_info(self):
        """Открывает инструкцию для Android (ByeByeDPI)."""
        try:
            webbrowser.open(ANDROID_URL)
            self._set_status("Открываю инструкцию для Android...")
        except Exception as e:
            err = f"Ошибка при открытии инструкции для Android: {e}"
            self._set_status(err)
            QMessageBox.warning(self._pw, "Ошибка", err)

    def create_premium_menu(self):
        """Создает меню Premium функций"""
        premium_menu = self.addMenu("💎 Premium")
        
        # Управление подпиской
        subscription_action = premium_menu.addAction("📋 Управление подпиской")
        subscription_action.triggered.connect(self._pw.show_subscription_dialog)
        
        premium_menu.addSeparator()
        
        # Информация о сервере
        server_info_action = premium_menu.addAction("⚙️ Статус сервера")
        server_info_action.triggered.connect(self._pw.get_boosty_server_info)

        # Переключение сервера
        server_toggle_action = premium_menu.addAction("🔄 Переключить сервер")
        server_toggle_action.triggered.connect(self._pw.toggle_boosty_server)

        premium_menu.addSeparator()
        
        telegram_action = premium_menu.addAction("🌐 Открыть Telegram")
        from config.telegram_links import open_telegram_link
        telegram_action.triggered.connect(lambda: open_telegram_link("zapretvpns_bot"))
        
        return premium_menu

    # ==================================================================
    #  Справка
    # ==================================================================
    def open_info(self):
        try:
            import webbrowser
            webbrowser.open(INFO_URL)
            self._set_status("Открываю руководство…")
        except Exception as e:
            err = f"Ошибка при открытии руководства: {e}"
            self._set_status(err)
            QMessageBox.warning(self._pw, "Ошибка", err)

    def open_support(self):
        try:
            from config.telegram_links import open_telegram_link
            open_telegram_link("zaprethelp")
            self._set_status("Открываю поддержку...")
        except Exception as e:
            err = f"Ошибка при открытии поддержки: {e}"
            self._set_status(err)
            QMessageBox.warning(self._pw, "Ошибка", err)

    def show_logs(self):
        """
        Переключается на вкладку Логи в основном интерфейсе.
        """
        try:
            from ui.page_names import PageName, SectionName

            # Находим главное окно и переключаемся на страницу логов
            main_window = self._pw

            # Проверяем наличие show_page метода для переключения
            if main_window and hasattr(main_window, 'show_page'):
                main_window.show_page(PageName.LOGS)
                # Также обновляем sidebar
                if hasattr(main_window, 'side_nav'):
                    main_window.side_nav.set_section_by_name(SectionName.LOGS, emit_signal=False)
                log("Переключение на страницу логов", "DEBUG")
                return

            # Fallback: если не нашли - открываем папку с логами
            import subprocess
            from config import LOGS_FOLDER
            subprocess.run(['explorer', LOGS_FOLDER], check=False)

        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self._pw or self,
                                "Ошибка",
                                f"Не удалось открыть логи:\n{e}")

    def send_log_to_tg_with_report(self):
        """Показывает диалог для описания проблемы, затем отправляет лог"""
        import time
        now = time.time()
        interval = 1 * 60  # 1 минута

        # Проверяем интервал
        last = self._settings.value("last_full_log_send", 0.0, type=float)
        
        if now - last < interval:
            remaining = int((interval - (now - last)) // 60) + 1
            QMessageBox.information(self._pw, "Отправка логов",
                f"Лог отправлялся недавно.\n"
                f"Следующая отправка возможна через {remaining} мин.")
            return

        # Проверяем доступность бота/Telegram API и показываем реальную причину
        from tgram.tg_log_bot import get_bot_connection_info

        bot_ok, bot_error, bot_kind = get_bot_connection_info()
        if not bot_ok:
            details = (bot_error or "Неизвестная ошибка").strip()
            if len(details) > 250:
                details = details[:250] + "…"
            msg_box = QMessageBox(self._pw)
            msg_box.setWindowTitle("Бот не настроен" if bot_kind == "config" else "Telegram недоступен")
            msg_box.setIcon(QMessageBox.Icon.Warning)
            hint = (
                "Проверьте настройки бота или обратитесь к разработчику."
                if bot_kind == "config"
                else "Если Telegram заблокирован — включите VPN/DPI bypass и повторите.\n"
                     "Если ошибка повторяется — обратитесь к разработчику."
            )
            msg_box.setText(
                "Не удалось подключиться к боту для отправки логов.\n\n"
                f"Причина: {details}\n\n"
                f"{hint}"
            )
            msg_box.exec()
            return

        # Показываем диалог для ввода описания проблемы
        report_dialog = LogReportDialog(self._pw)
        if report_dialog.exec() != QDialog.DialogCode.Accepted:
            return  # Пользователь отменил отправку
        
        report_data = report_dialog.get_report_data()

        # Запоминаем время отправки
        self._settings.setValue("last_full_log_send", now)

        # Подготовка к отправке
        from tgram.tg_log_full import TgSendWorker
        from tgram.tg_log_delta import get_client_id
        import os

        # Используем текущий лог файл
        from log import global_logger
        LOG_PATH = global_logger.log_file if hasattr(global_logger, 'log_file') else None
        
        if not LOG_PATH or not os.path.exists(LOG_PATH):
            QMessageBox.warning(self._pw, "Ошибка", "Файл лога не найден")
            return
        
        # Формируем подпись с информацией о файле и проблеме
        import platform
        log_filename = os.path.basename(LOG_PATH)
        
        caption = f"📋 Ручная отправка лога\n"
        caption += f"📁 Файл: {log_filename}\n"
        caption += f"Zapret2 v{APP_VERSION}\n"
        caption += f"ID: {get_client_id()}\n"
        caption += f"Host: {platform.node()}\n"
        caption += f"Time: {time.strftime('%d.%m.%Y %H:%M:%S')}\n"
        
        # Добавляем описание проблемы и контакты, если они указаны
        if report_data['problem']:
            caption += f"\n🔴 Проблема:\n{report_data['problem']}\n"
        
        if report_data['telegram']:
            caption += f"\n📱 Telegram: {report_data['telegram']}\n"

        action = self.sender()
        if action:
            action.setEnabled(False)

        wnd = self._pw
        if hasattr(wnd, "set_status"):
            wnd.set_status("Отправка лога...")

        # Создаем воркер с флагом use_log_bot=True
        thr = QThread(self)
        worker = TgSendWorker(LOG_PATH, caption, use_log_bot=True)
        worker.moveToThread(thr)
        thr.started.connect(worker.run)

        def _on_done(ok: bool, extra_wait: float, error_msg: str = ""):
            if ok:
                if hasattr(wnd, "set_status"):
                    wnd.set_status("Лог отправлен")
            else:
                if extra_wait > 0:
                    QMessageBox.warning(wnd, "Слишком часто",
                        f"Слишком частые запросы.\n"
                        f"Повторите через {int(extra_wait/60)} минут.")
                else:
                    QMessageBox.warning(wnd, "Ошибка",
                        f"Не удалось отправить лог.\n\n"
                        f"Причина: {error_msg or 'Неизвестная ошибка'}\n\n"
                        f"Попробуйте позже или обратитесь в поддержку.")
                
                if hasattr(wnd, "set_status"):
                    wnd.set_status("Ошибка отправки лога")
            
            # Очистка
            worker.deleteLater()
            thr.quit()
            thr.wait()
            if action:
                action.setEnabled(True)

        worker.finished.connect(_on_done)

        # Сохраняем ссылку на поток
        self._log_send_thread = thr
        thr.start()

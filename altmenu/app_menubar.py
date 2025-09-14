# altmenu/app_menubar.py

from PyQt6.QtWidgets import QMenuBar, QWidget, QMessageBox, QApplication
from PyQt6.QtGui     import QKeySequence, QAction
from PyQt6.QtCore    import Qt, QThread, QSettings
import webbrowser

from config import APP_VERSION, get_dpi_autostart, set_dpi_autostart # build_info moved to config/__init__.py
from config.urls import INFO_URL
from .about_dialog import AboutDialog
from .defender_manager import WindowsDefenderManager
from .max_blocker import MaxBlockerManager

from utils import run_hidden
from log import log, LogViewerDialog, global_logger

from startup import get_remove_windows_terminal, set_remove_windows_terminal

class AppMenuBar(QMenuBar):
    """
    Верхняя строка меню («Alt-меню»).
    """

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._pw = parent
        self._settings = QSettings("ZapretGUI", "Zapret") # для сохранения настроек
        self._set_status = getattr(parent, "set_status", lambda *_: None)

        # -------- 1. Настройки -------------------------------------------------
        file_menu = self.addMenu("&Настройки")

        # Чек-бокс Автозагрузка DPI»
        self.auto_dpi_act = QAction("Автозагрузка DPI", self, checkable=True)
        self.auto_dpi_act.setChecked(get_dpi_autostart())
        self.auto_dpi_act.toggled.connect(self.toggle_dpi_autostart)
        file_menu.addAction(self.auto_dpi_act)

        self.force_dns_act = QAction("Принудительный DNS 9.9.9.9", self, checkable=True)
        self.force_dns_act.setChecked(self._get_force_dns_enabled())
        self.force_dns_act.toggled.connect(self.toggle_force_dns)
        file_menu.addAction(self.force_dns_act)

        self.clear_cache = file_menu.addAction("Сбросить программу")
        self.clear_cache.triggered.connect(self.clear_startup_cache)

        file_menu.addSeparator()

        # Windows Defender
        file_menu.addSeparator()
        self.defender_act = QAction("Отключить Windows Defender", self, checkable=True)
        self.defender_act.setChecked(self._get_defender_disabled())
        self.defender_act.toggled.connect(self.toggle_windows_defender)
        file_menu.addAction(self.defender_act)

        self.remove_wt_act = QAction("Удалять Windows Terminal", self, checkable=True)
        self.remove_wt_act.setChecked(get_remove_windows_terminal())
        self.remove_wt_act.toggled.connect(self.toggle_remove_windows_terminal)
        file_menu.addAction(self.remove_wt_act)

        # Блокировка MAX
        self.block_max_act = QAction("Блокировать установку MAX", self, checkable=True)
        self.block_max_act.setChecked(self._get_max_blocked())
        self.block_max_act.toggled.connect(self.toggle_max_blocker)
        file_menu.addAction(self.block_max_act)

        file_menu.addSeparator()

        act_exit = QAction("Скрыть GUI в трей", self, shortcut=QKeySequence("Ctrl+Q"))
        act_exit.triggered.connect(parent.close)
        file_menu.addAction(act_exit)

        full_exit_act = QAction("Полностью выйти", self, shortcut=QKeySequence("Ctrl+Shift+Q"))
        full_exit_act.triggered.connect(self.full_exit)
        file_menu.addAction(full_exit_act)

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

        # -------- 2. «Телеметрия / Настройки» ------------------------------
        telemetry_menu = self.addMenu("&Телеметрия")

        # 2 Показ журнала
        act_logs = QAction("Показать лог-файл", self)
        act_logs.triggered.connect(self.show_logs)
        telemetry_menu.addAction(act_logs)

        act_logs = QAction("Отправить лог файл", self)
        act_logs.triggered.connect(self.send_log_to_tg)
        telemetry_menu.addAction(act_logs)

        # -------- 3. «Справка» ---------------------------------------------
        help_menu = self.addMenu("&Справка")

        act_help = QAction("❓ Что это такое? (Руководство)", self)
        act_help.triggered.connect(self.open_info)
        help_menu.addAction(act_help)

        act_support = QAction("💬 Поддержка (запросить помощь)", self)
        act_support.triggered.connect(self.open_support)
        help_menu.addAction(act_support)

        act_about = QAction("ℹ О программе…", self)
        act_about.triggered.connect(lambda: AboutDialog(parent).exec())
        help_menu.addAction(act_about)

        # -------- 4. «Андроид» ---------------------------------------------
        android_menu = self.addMenu("&Андроид")

        act_byedpi_info = QAction("О ByeDPIAndroid", self)
        act_byedpi_info.triggered.connect(self.show_byedpi_info)
        android_menu.addAction(act_byedpi_info)

        act_byedpi_github = QAction("GitHub проекта", self)
        act_byedpi_github.triggered.connect(self.open_byedpi_github)
        android_menu.addAction(act_byedpi_github)

        act_byedpi_telegram = QAction("Telegram группа", self)
        act_byedpi_telegram.triggered.connect(self.open_byedpi_telegram)
        android_menu.addAction(act_byedpi_telegram)
        

    def _get_force_dns_enabled(self) -> bool:
        """Получает текущее состояние принудительного DNS"""
        try:
            from dns import DNSForceManager
            manager = DNSForceManager()
            return manager.is_force_dns_enabled()
        except Exception as e:
            log(f"Ошибка при проверке состояния Force DNS: {e}", "❌ ERROR")
            return False

    def toggle_force_dns(self, enabled: bool):
        """
        Включает/выключает принудительную установку DNS 9.9.9.9
        """

        from dns import DNSForceManager
        
        try:
            manager = DNSForceManager(status_callback=self._set_status)
            
            if enabled:
                # Показываем предупреждение перед включением
                msg_box = QMessageBox(self._pw)
                msg_box.setWindowTitle("Принудительный DNS")
                msg_box.setIcon(QMessageBox.Icon.Warning)
                msg_box.setText(
                    "Включить принудительную установку DNS 9.9.9.9?\n\n"
                    "Это действие изменит DNS-серверы на всех активных "
                    "сетевых адаптерах (Ethernet и Wi-Fi)."
                )
                msg_box.setInformativeText(
                    "DNS-сервер 9.9.9.9 (Quad9) обеспечивает:\n"
                    "• Защиту от вредоносных сайтов\n"
                    "• Конфиденциальность запросов\n"
                    "• Обход некоторых блокировок\n\n"
                    "Текущие настройки DNS будут сохранены для восстановления."
                )
                msg_box.setStandardButtons(
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                msg_box.setDefaultButton(QMessageBox.StandardButton.No)
                
                if msg_box.exec() != QMessageBox.StandardButton.Yes:
                    # Пользователь отменил - откатываем галочку
                    self.force_dns_act.blockSignals(True)
                    self.force_dns_act.setChecked(False)
                    self.force_dns_act.blockSignals(False)
                    return
                
                # Создаем резервную копию текущих DNS
                self._set_status("Создание резервной копии DNS...")
                manager.backup_current_dns()
                
                # Включаем опцию в реестре
                manager.set_force_dns_enabled(True)
                
                # Применяем DNS
                self._set_status("Применение DNS 9.9.9.9...")
                success, total = manager.force_dns_on_all_adapters()
                
                if success > 0:
                    QMessageBox.information(
                        self._pw, 
                        "DNS установлен",
                        f"DNS 9.9.9.9 успешно установлен на {success} из {total} адаптеров.\n\n"
                        "Изменения вступят в силу немедленно."
                    )
                    log(f"Принудительный DNS включен: {success}/{total} адаптеров", "INFO")
                else:
                    QMessageBox.warning(
                        self._pw,
                        "Ошибка",
                        "Не удалось установить DNS ни на одном адаптере.\n"
                        "Возможно, требуются права администратора."
                    )
                    # Откатываем настройку
                    manager.set_force_dns_enabled(False)
                    self.force_dns_act.blockSignals(True)
                    self.force_dns_act.setChecked(False)
                    self.force_dns_act.blockSignals(False)
                    
            else:
                # Отключение принудительного DNS
                msg_box = QMessageBox(self._pw)
                msg_box.setWindowTitle("Отключение принудительного DNS")
                msg_box.setIcon(QMessageBox.Icon.Question)
                msg_box.setText("Как отключить принудительный DNS?")
                
                restore_btn = msg_box.addButton("Восстановить из резервной копии", QMessageBox.ButtonRole.AcceptRole)
                auto_btn = msg_box.addButton("Переключить на автоматический", QMessageBox.ButtonRole.AcceptRole)
                cancel_btn = msg_box.addButton("Отмена", QMessageBox.ButtonRole.RejectRole)
                
                msg_box.setDefaultButton(restore_btn)
                msg_box.exec()
                
                clicked_btn = msg_box.clickedButton()
                
                if clicked_btn == cancel_btn:
                    # Отмена - возвращаем галочку
                    self.force_dns_act.blockSignals(True)
                    self.force_dns_act.setChecked(True)
                    self.force_dns_act.blockSignals(False)
                    return
                
                # Отключаем опцию в реестре
                manager.set_force_dns_enabled(False)
                
                if clicked_btn == restore_btn:
                    # Восстанавливаем из резервной копии
                    self._set_status("Восстановление DNS из резервной копии...")
                    if manager.restore_dns_from_backup():
                        QMessageBox.information(
                            self._pw,
                            "DNS восстановлен",
                            "DNS-настройки успешно восстановлены из резервной копии."
                        )
                        log("DNS восстановлен из резервной копии", "INFO")
                    else:
                        QMessageBox.warning(
                            self._pw,
                            "Ошибка",
                            "Не удалось восстановить DNS из резервной копии.\n"
                            "Настройки будут сброшены на автоматические."
                        )
                        # Fallback - сбрасываем на автоматические
                        self._reset_all_dns_to_auto(manager)
                        
                elif clicked_btn == auto_btn:
                    # Сбрасываем на автоматическое получение
                    self._reset_all_dns_to_auto(manager)
                    
            self._set_status("Готово")
            
        except Exception as e:
            log(f"Ошибка при переключении Force DNS: {e}", "❌ ERROR")
            QMessageBox.critical(
                self._pw,
                "Ошибка",
                f"Произошла ошибка при изменении настроек DNS:\n{e}"
            )
            # В случае ошибки откатываем галочку
            self.force_dns_act.blockSignals(True)
            self.force_dns_act.setChecked(not enabled)
            self.force_dns_act.blockSignals(False)

    def _reset_all_dns_to_auto(self, manager):
        """Сбрасывает DNS на всех адаптерах на автоматическое получение"""
        self._set_status("Сброс DNS на автоматическое получение...")
        adapters = manager.get_network_adapters()
        success_count = 0
        
        for adapter in adapters:
            if manager.reset_dns_to_auto(adapter):
                success_count += 1
        
        if success_count > 0:
            QMessageBox.information(
                self._pw,
                "DNS сброшен",
                f"DNS сброшен на автоматическое получение на {success_count} из {len(adapters)} адаптеров."
            )
            log(f"DNS сброшен на авто: {success_count}/{len(adapters)} адаптеров", "INFO")
        else:
            QMessageBox.warning(
                self._pw,
                "Ошибка",
                "Не удалось сбросить DNS ни на одном адаптере."
            )

    def clear_startup_cache(self):
        """Очищает кэш проверок запуска"""
        from startup.check_cache import startup_cache
        try:
            startup_cache.invalidate_cache()
            QMessageBox.information(self._pw, "Настройки программы сброшены", 
                                  "Кэш проверок запуска и настройки программы успешно очищены.\n"
                                  "При следующем запуске все проверки будут выполнены заново.")
            log("Кэш проверок запуска очищен пользователем", "INFO")
        except Exception as e:
            QMessageBox.warning(self._pw, "Ошибка", 
                              f"Не удалось очистить кэш: {e}")
            log(f"Ошибка очистки кэша: {e}", "❌ ERROR")

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
        telegram_action.triggered.connect(lambda: webbrowser.open("https://t.me/zapretvpns_bot"))
        
        return premium_menu

    # ==================================================================
    #  Обработчики чек-боксов
    # ==================================================================
    def toggle_remove_windows_terminal(self, enabled: bool):
        """
        Включает / выключает удаление Windows Terminal при запуске программы.
        """
        set_remove_windows_terminal(enabled)

        msg = ("Windows Terminal будет удаляться при запуске программы"
               if enabled
               else "Удаление Windows Terminal отключено")
        self._set_status(msg)
        
        if not enabled:
            # При отключении показываем предупреждение
            warning_msg = (
                "Внимание! Windows Terminal может мешать работе программы.\n\n"
                "Если у вас возникнут проблемы с работой DPI-обхода, "
                "рекомендуется включить эту опцию обратно."
            )
            QMessageBox.warning(self._pw, "Предупреждение", warning_msg)
        else:
            QMessageBox.information(self._pw, "Удаление Windows Terminal", msg)

    def toggle_dpi_autostart(self, enabled: bool):
        set_dpi_autostart(enabled)

        msg = ("DPI будет включаться автоматически при старте программы"
               if enabled
               else "Автозагрузка DPI отключена")
        self._set_status(msg)
        QMessageBox.information(self._pw, "Автозагрузка DPI", msg)

    # ==================================================================
    #  Полный выход (убираем трей +, при желании, останавливаем DPI)
    # ==================================================================

    def full_exit(self):
        # -----------------------------------------------------------------
        # 1. Диалог на русском, но с англ. подсказками в тексте
        # -----------------------------------------------------------------
        box = QMessageBox(self._pw)
        box.setWindowTitle("Выход")
        box.setIcon(QMessageBox.Icon.Question)

        # сам текст оставляем без изменений
        box.setText(
            "Остановить DPI-службу перед выходом?\n"
            "Да – остановить DPI и выйти\n"
            "Нет  – выйти, не останавливая DPI\n"
            "Отмена – остаться в программе"
        )

        # добавляем три стандартные кнопки
        box.setStandardButtons(
            QMessageBox.StandardButton.Yes |
            QMessageBox.StandardButton.No  |
            QMessageBox.StandardButton.Cancel
        )
        box.setDefaultButton(QMessageBox.StandardButton.Cancel)

        # ─── Русифицируем подписи ────────────────────────────────────────
        box.button(QMessageBox.StandardButton.Yes).setText("Да")
        box.button(QMessageBox.StandardButton.No).setText("Нет")
        box.button(QMessageBox.StandardButton.Cancel).setText("Отмена")

        # показываем диалог
        resp = box.exec()

        if resp == QMessageBox.StandardButton.Cancel:
            return                      # пользователь передумал

        stop_dpi_required = resp == QMessageBox.StandardButton.Yes

        # -----------------------------------------------------------------
        # 2. Дальше логика выхода (как раньше)
        # -----------------------------------------------------------------
        if stop_dpi_required:
            try:
                from dpi.stop import stop_dpi
                stop_dpi(self._pw)
            except Exception as e:
                QMessageBox.warning(
                    self._pw, "Ошибка DPI",
                    f"Не удалось остановить DPI:\n{e}"
                )

        if hasattr(self._pw, "process_monitor") and self._pw.process_monitor:
            self._pw.process_monitor.stop()

        if hasattr(self._pw, "tray_manager"):
            self._pw.tray_manager.tray_icon.hide()

        self._pw._allow_close = True
        QApplication.quit()

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
            import webbrowser
            webbrowser.open("https://t.me/zaprethelp")
            self._set_status("Открываю поддержку...")
        except Exception as e:
            err = f"Ошибка при открытии поддержки: {e}"
            self._set_status(err)
            QMessageBox.warning(self._pw, "Ошибка", err)

    def show_logs(self):
        """
        Открывает окно просмотра логов без блокировки остального GUI.
        Держим ссылку на объект, чтобы его не удалил сборщик мусора.
        """
        try:
            # если окно уже открыто ‑ просто поднимаем его
            if getattr(self, "_log_dlg", None) and self._log_dlg.isVisible():
                self._log_dlg.raise_()
                self._log_dlg.activateWindow()
                return

            self._log_dlg = LogViewerDialog(
                parent   = self._pw or self,
                log_file = global_logger.log_file,
            )
            self._log_dlg.show()                   # <<- вместо exec()

        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self._pw or self,
                                "Ошибка",
                                f"Не удалось открыть журнал:\n{e}")

    def send_log_to_tg(self):
        """Отправляет полный лог через отдельного бота для логов."""
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

        # Проверяем настройки бота
        from tgram.tg_log_bot import check_bot_connection
        
        if not check_bot_connection():
            msg_box = QMessageBox(self._pw)
            msg_box.setWindowTitle("Бот не настроен")
            msg_box.setIcon(QMessageBox.Icon.Warning)
            msg_box.setText(
                "Бот для отправки логов не настроен или недоступен.\n\n"
                "Для настройки:\n"
                "1. Создайте бота через @BotFather в Telegram\n"
                "2. Получите токен бота\n"
                "3. Создайте канал/чат для логов\n"
                "4. Добавьте бота в канал как администратора\n"
                "5. Обновите настройки в файле tg_log_bot.py"
            )
            msg_box.exec()
            return

        # Запоминаем время отправки
        self._settings.setValue("last_full_log_send", now)

        # Подготовка к отправке
        from tgram.tg_log_full import TgSendWorker
        from tgram.tg_log_delta import get_client_id
        import os

        # ИЗМЕНЕНО: используем текущий лог файл
        from log import global_logger
        LOG_PATH = global_logger.log_file if hasattr(global_logger, 'log_file') else None
        
        if not LOG_PATH or not os.path.exists(LOG_PATH):
            QMessageBox.warning(self._pw, "Ошибка", "Файл лога не найден")
            return
        
        # Формируем подпись с информацией о файле
        import platform
        log_filename = os.path.basename(LOG_PATH)
        caption = (
            f"📋 Ручная отправка лога\n"
            f"📁 Файл: {log_filename}\n"  # Добавляем имя файла
            f"Zapret v{APP_VERSION}\n"
            f"ID: {get_client_id()}\n"
            f"Host: {platform.node()}\n"
            f"Time: {time.strftime('%d.%m.%Y %H:%M:%S')}"
        )

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
                QMessageBox.information(wnd, "Успешно", 
                    "Лог успешно отправлен в канал поддержки.\n"
                    "Спасибо за помощь в улучшении программы!")
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

    # ==================================================================
    #  Андроид
    # ==================================================================
    def show_byedpi_info(self):
        """Показывает информацию о ByeDPIAndroid"""
        info_text = """
        <h2>ByeDPIAndroid</h2>
        
        <p><b>ByeDPIAndroid</b> — это мобильная версия DPI-обхода для устройств Android, 
        аналогичная Zapret GUI для Windows.</p>
        
        <h3>Особенности:</h3>
        <ul>
        <li>🔧 Простая настройка и использование</li>
        <li>🛡️ Обход блокировок сайтов на Android</li>
        <li>⚡ Работа без root-доступа</li>
        <li>🔄 Регулярные обновления</li>
        <li>💬 Активная поддержка сообщества</li>
        </ul>
        
        <h3>Ссылки:</h3>
        <p>📱 <a href="https://github.com/romanvht/ByeDPIAndroid">GitHub проекта</a></p>
        <p>💬 <a href="https://t.me/byebyedpi_group">Telegram группа</a></p>
        
        <p><i>ByeDPIAndroid разрабатывается независимо от Zapret GUI, 
        но использует схожие принципы работы.</i></p>
        """
        
        msg_box = QMessageBox(self._pw)
        msg_box.setWindowTitle("ByeDPIAndroid")
        msg_box.setTextFormat(Qt.TextFormat.RichText)  # Исправлено: используем Qt.TextFormat
        msg_box.setText(info_text)
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.exec()

    def open_byedpi_github(self):
        """Открывает GitHub проекта ByeDPIAndroid"""
        try:
            webbrowser.open("https://github.com/romanvht/ByeDPIAndroid")
            self._set_status("Открываю GitHub ByeDPIAndroid...")
        except Exception as e:
            err = f"Ошибка при открытии GitHub: {e}"
            self._set_status(err)
            QMessageBox.warning(self._pw, "Ошибка", err)

    def open_byedpi_telegram(self):
        """Открывает Telegram группу ByeDPIAndroid"""
        try:
            webbrowser.open("https://t.me/byebyedpi_group")
            self._set_status("Открываю Telegram группу ByeDPIAndroid...")
        except Exception as e:
            err = f"Ошибка при открытии Telegram: {e}"
            self._set_status(err)
            QMessageBox.warning(self._pw, "Ошибка", err)

    def _get_defender_disabled(self) -> bool:
        """Проверяет, отключен ли Windows Defender"""
        try:
            manager = WindowsDefenderManager()
            return manager.is_defender_disabled()
        except Exception as e:
            log(f"Ошибка при проверке состояния Windows Defender: {e}", "❌ ERROR")
            return False

    def toggle_windows_defender(self, disable: bool):
        """Включает/выключает Windows Defender"""
        import ctypes
        
        # Проверяем права администратора
        if not ctypes.windll.shell32.IsUserAnAdmin():
            QMessageBox.critical(
                self._pw,
                "Требуются права администратора",
                "Для управления Windows Defender требуются права администратора.\n\n"
                "Перезапустите программу от имени администратора."
            )
            # Откатываем галочку
            self.defender_act.blockSignals(True)
            self.defender_act.setChecked(not disable)
            self.defender_act.blockSignals(False)
            return
        
        try:
            manager = WindowsDefenderManager(status_callback=self._set_status)
            
            if disable:
                # Показываем предупреждение перед отключением
                msg_box = QMessageBox(self._pw)
                msg_box.setWindowTitle("Отключение Windows Defender")
                msg_box.setIcon(QMessageBox.Icon.Warning)
                msg_box.setText(
                    "Вы действительно хотите отключить Windows Defender?\n\n"
                )
                msg_box.setInformativeText(
                    "Отключение Windows Defender:\n"
                    "• Отключит защиту в реальном времени\n"
                    "• Отключит облачную защиту\n"
                    "• Отключит автоматическую отправку образцов\n"
                    "• Может потребовать перезагрузки для полного применения\n\n"
                )
                msg_box.setStandardButtons(
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                msg_box.setDefaultButton(QMessageBox.StandardButton.No)
                
                if msg_box.exec() != QMessageBox.StandardButton.Yes:
                    # Пользователь отменил - откатываем галочку
                    self.defender_act.blockSignals(True)
                    self.defender_act.setChecked(False)
                    self.defender_act.blockSignals(False)
                    return
                
                # Отключаем Defender
                self._set_status("Отключение Windows Defender...")
                success, count = manager.disable_defender()
                
                if success:
                    # Сохраняем настройку
                    from .defender_manager import set_defender_disabled
                    set_defender_disabled(True)
                    
                    QMessageBox.information(
                        self._pw,
                        "Windows Defender отключен",
                        f"Windows Defender успешно отключен.\n"
                        f"Применено {count} настроек.\n\n"
                        "Для полного применения изменений может потребоваться перезагрузка."
                    )
                    log(f"Windows Defender отключен пользователем", "⚠️ WARNING")
                else:
                    QMessageBox.critical(
                        self._pw,
                        "Ошибка",
                        "Не удалось отключить Windows Defender.\n"
                        "Возможно, некоторые настройки заблокированы системой."
                    )
                    # Откатываем настройку
                    self.defender_act.blockSignals(True)
                    self.defender_act.setChecked(False)
                    self.defender_act.blockSignals(False)
                    
            else:
                # Включение Windows Defender
                msg_box = QMessageBox(self._pw)
                msg_box.setWindowTitle("Включение Windows Defender")
                msg_box.setIcon(QMessageBox.Icon.Question)
                msg_box.setText(
                    "Включить Windows Defender обратно?\n\n"
                    "Это восстановит защиту вашего компьютера."
                )
                msg_box.setStandardButtons(
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                msg_box.setDefaultButton(QMessageBox.StandardButton.Yes)
                
                if msg_box.exec() != QMessageBox.StandardButton.Yes:
                    # Пользователь отменил - возвращаем галочку
                    self.defender_act.blockSignals(True)
                    self.defender_act.setChecked(True)
                    self.defender_act.blockSignals(False)
                    return
                
                # Включаем Defender
                self._set_status("Включение Windows Defender...")
                success, count = manager.enable_defender()
                
                if success:
                    # Сохраняем настройку
                    from .defender_manager import set_defender_disabled
                    set_defender_disabled(False)
                    
                    QMessageBox.information(
                        self._pw,
                        "Windows Defender включен",
                        f"Windows Defender успешно включен.\n"
                        f"Выполнено {count} операций.\n\n"
                        "Защита вашего компьютера восстановлена."
                    )
                    log("Windows Defender включен пользователем", "✅ INFO")
                else:
                    QMessageBox.warning(
                        self._pw,
                        "Частичный успех",
                        "Windows Defender включен частично.\n"
                        "Для полного восстановления может потребоваться перезагрузка."
                    )
                    
            self._set_status("Готово")
            
        except Exception as e:
            log(f"Ошибка при переключении Windows Defender: {e}", "❌ ERROR")
            QMessageBox.critical(
                self._pw,
                "Ошибка",
                f"Произошла ошибка при изменении настроек Windows Defender:\n{e}"
            )
            # В случае ошибки откатываем галочку
            self.defender_act.blockSignals(True)
            self.defender_act.setChecked(not disable)
            self.defender_act.blockSignals(False)

    def _get_max_blocked(self) -> bool:
        """Проверяет, включена ли блокировка MAX"""
        try:
            from .max_blocker import is_max_blocked
            return is_max_blocked()
        except Exception as e:
            log(f"Ошибка при проверке блокировки MAX: {e}", "❌ ERROR")
            return False

    def toggle_max_blocker(self, enable: bool):
        """Включает/выключает блокировку программы MAX"""
        try:
            manager = MaxBlockerManager(status_callback=self._set_status)
            
            if enable:
                # Показываем предупреждение перед включением
                msg_box = QMessageBox(self._pw)
                msg_box.setWindowTitle("Блокировка MAX")
                msg_box.setIcon(QMessageBox.Icon.Information)
                msg_box.setText(
                    "Включить блокировку установки и работы программы MAX?\n\n"
                    "Это действие:"
                )
                msg_box.setInformativeText(
                    "• Заблокирует запуск max.exe, max.msi и других файлов MAX\n"
                    "• Создаст файлы-блокировки в папках установки\n"
                    "• Добавит правила блокировки в Windows Firewall (при наличии прав)\n"
                    "• Заблокирует домены MAX в файле hosts\n\n"
                    "В итоге даже если мессенджер Max поставиться будет тёмный экран, в результате чего он будет выглядеть так, будто не может подключиться к своим серверам."
                )
                msg_box.setStandardButtons(
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                msg_box.setDefaultButton(QMessageBox.StandardButton.Yes)
                
                if msg_box.exec() != QMessageBox.StandardButton.Yes:
                    # Пользователь отменил - откатываем галочку
                    self.block_max_act.blockSignals(True)
                    self.block_max_act.setChecked(False)
                    self.block_max_act.blockSignals(False)
                    return
                
                # Включаем блокировку
                success, message = manager.enable_blocking()
                
                if success:
                    QMessageBox.information(
                        self._pw,
                        "Блокировка включена",
                        message
                    )
                    log("Блокировка MAX включена пользователем", "🛡️ INFO")
                else:
                    QMessageBox.warning(
                        self._pw,
                        "Ошибка",
                        f"Не удалось полностью включить блокировку:\n{message}"
                    )
                    # Откатываем галочку
                    self.block_max_act.blockSignals(True)
                    self.block_max_act.setChecked(False)
                    self.block_max_act.blockSignals(False)
                    
            else:
                # Отключение блокировки
                msg_box = QMessageBox(self._pw)
                msg_box.setWindowTitle("Отключение блокировки MAX")
                msg_box.setIcon(QMessageBox.Icon.Question)
                msg_box.setText(
                    "Отключить блокировку программы MAX?\n\n"
                    "Это удалит все созданные блокировки и правила."
                )
                msg_box.setStandardButtons(
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                msg_box.setDefaultButton(QMessageBox.StandardButton.No)
                
                if msg_box.exec() != QMessageBox.StandardButton.Yes:
                    # Пользователь отменил - возвращаем галочку
                    self.block_max_act.blockSignals(True)
                    self.block_max_act.setChecked(True)
                    self.block_max_act.blockSignals(False)
                    return
                
                # Отключаем блокировку
                success, message = manager.disable_blocking()
                
                if success:
                    QMessageBox.information(
                        self._pw,
                        "Блокировка отключена",
                        message
                    )
                    log("Блокировка MAX отключена пользователем", "✅ INFO")
                else:
                    QMessageBox.warning(
                        self._pw,
                        "Ошибка",
                        f"Не удалось полностью отключить блокировку:\n{message}"
                    )
                    
            self._set_status("Готово")
            
        except Exception as e:
            log(f"Ошибка при переключении блокировки MAX: {e}", "❌ ERROR")
            QMessageBox.critical(
                self._pw,
                "Ошибка",
                f"Произошла ошибка при изменении блокировки MAX:\n{e}"
            )
            # В случае ошибки откатываем галочку
            self.block_max_act.blockSignals(True)
            self.block_max_act.setChecked(not enable)
            self.block_max_act.blockSignals(False)
# app_menubar.py

from PyQt6.QtWidgets import QMenuBar, QWidget, QMessageBox, QApplication
from PyQt6.QtGui     import QKeySequence, QAction
from PyQt6.QtCore    import Qt, QThread, QSettings
import webbrowser

from config import APP_VERSION # build_info moved to config/__init__.py
from config.urls import INFO_URL
from .about_dialog import AboutDialog
from config import get_auto_download_enabled, set_auto_download_enabled

# ─── работа с реестром ──────────────────────────
from config import (
    get_dpi_autostart,  set_dpi_autostart,
    get_strategy_autoload, set_strategy_autoload,
    get_remove_windows_terminal, set_remove_windows_terminal
)


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

        auto_download_action = file_menu.addAction("Автозагрузка при старте")
        auto_download_action.setCheckable(True)
        auto_download_action.setChecked(get_auto_download_enabled())
        auto_download_action.triggered.connect(self.toggle_auto_download)

        # Чек-бокс «Автозапуск DPI»
        self.auto_dpi_act = QAction("Автозапуск DPI", self, checkable=True)
        self.auto_dpi_act.setChecked(get_dpi_autostart())
        self.auto_dpi_act.toggled.connect(self.toggle_dpi_autostart)
        file_menu.addAction(self.auto_dpi_act)

        # 2Чек-бокс «Автозагрузка стратегий» (раз уж из трея убран)
        self.auto_strat_act = QAction("Автозагрузка стратегий", self, checkable=True)
        self.auto_strat_act.setChecked(get_strategy_autoload())
        self.auto_strat_act.toggled.connect(self.toggle_strategy_autoload)
        file_menu.addAction(self.auto_strat_act)

        # Чек-бокс «Удалять Windows Terminal»
        self.remove_wt_act = QAction("Удалять Windows Terminal", self, checkable=True)
        self.remove_wt_act.setChecked(get_remove_windows_terminal())
        self.remove_wt_act.toggled.connect(self.toggle_remove_windows_terminal)
        file_menu.addAction(self.remove_wt_act)

        file_menu.addSeparator()

        act_exit = QAction("Скрыть GUI в трей", self, shortcut=QKeySequence("Ctrl+Q"))
        act_exit.triggered.connect(parent.close)
        file_menu.addAction(act_exit)

        full_exit_act = QAction("Полностью выйти", self, shortcut=QKeySequence("Ctrl+Shift+Q"))
        full_exit_act.triggered.connect(self.full_exit)
        file_menu.addAction(full_exit_act)

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

        # -------- 2. «Телеметрия / Настройки» ------------------------------
        telemetry_menu = self.addMenu("&Телеметрия")

        # 2 Показ журнала
        act_logs = QAction("Показать лог-файл", self)
        act_logs.triggered.connect(self.show_logs)
        telemetry_menu.addAction(act_logs)

        act_logs = QAction("Отправить лог файл", self)
        act_logs.triggered.connect(self.send_log_to_tg)
        telemetry_menu.addAction(act_logs)

        # 2 «О программе…»
        act_about = QAction("О программе…", self)
        act_about.triggered.connect(lambda: AboutDialog(parent).exec())
        telemetry_menu.addAction(act_about)

        # -------- 3. «Справка» ---------------------------------------------
        help_menu = self.addMenu("&Справка")

        act_help = QAction("Что это такое? (Руководство)", self)
        act_help.triggered.connect(self.open_info)

        # Добавляем пункт очистки кэша в меню "Справка"
        clear_cache_action = help_menu.addAction("Очистить кэш проверок")
        clear_cache_action.triggered.connect(self.clear_startup_cache)

        help_menu.addAction(act_help)

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

    def toggle_auto_download(self, checked):
        """Переключает автозагрузку при старте"""
        from log import log
        try:
            set_auto_download_enabled(checked)
            
            status_text = "включена" if checked else "отключена"
            QMessageBox.information(self._pw, "Автозагрузка", 
                                  f"Автозагрузка при старте {status_text}.\n"
                                  f"Изменения вступят в силу при следующем запуске программы.")
            log(f"Пользователь {'включил' if checked else 'отключил'} автозагрузку", "INFO")
            
        except Exception as e:
            QMessageBox.warning(self._pw, "Ошибка", 
                              f"Не удалось изменить настройку автозагрузки: {e}")
            log(f"Ошибка изменения автозагрузки: {e}", "ERROR")

    def clear_startup_cache(self):
        """Очищает кэш проверок запуска"""
        from startup.check_cache import startup_cache
        from log import log
        try:
            startup_cache.invalidate_cache()
            QMessageBox.information(self._pw, "Кэш очищен", 
                                  "Кэш проверок запуска успешно очищен.\n"
                                  "При следующем запуске все проверки будут выполнены заново.")
            log("Кэш проверок запуска очищен пользователем", "INFO")
        except Exception as e:
            QMessageBox.warning(self._pw, "Ошибка", 
                              f"Не удалось очистить кэш: {e}")
            log(f"Ошибка очистки кэша: {e}", "ERROR")

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
        
        # Ссылка на Boosty
        boosty_action = premium_menu.addAction("🌐 Открыть Boosty")
        boosty_action.triggered.connect(lambda: webbrowser.open("https://boosty.to/censorliber"))
        
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
        """
        Включает / выключает автозапуск DPI и показывает диалог-уведомление.
        """
        set_dpi_autostart(enabled)

        msg = ("DPI будет запускаться автоматически при старте программы"
               if enabled
               else "Автоматический запуск DPI отключён")
        self._set_status(msg)
        QMessageBox.information(self._pw, "Автозапуск DPI", msg)

    def toggle_strategy_autoload(self, enabled: bool):
        """
        Повторяет логику, которая раньше была в трее: при отключении
        спрашивает подтверждение.
        """
        if not enabled:
            warn = (
                "<b>Вы действительно хотите ОТКЛЮЧИТЬ автозагрузку "
                "стратегий?</b><br><br>"
                "⚠️  Это <span style='color:red;font-weight:bold;'>сломает</span> "
                "быстрое и удобное обновление стратегий без переустановки "
                "всей программы!"
            )
            resp = QMessageBox.question(
                self._pw,
                "Отключить автозагрузку стратегий?",
                warn,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if resp != QMessageBox.StandardButton.Yes:
                # пользователь передумал – откатываем галку
                self.auto_strat_act.blockSignals(True)
                self.auto_strat_act.setChecked(True)
                self.auto_strat_act.blockSignals(False)
                return

        # сохраняем выбор
        set_strategy_autoload(enabled)
        msg = ("Стратегии будут скачиваться автоматически"
               if enabled
               else "Автозагрузка стратегий отключена")
        self._set_status(msg)
        QMessageBox.information(self._pw, "Автозагрузка стратегий", msg)

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

    # === ОБРАБОТЧИКИ ДЛЯ ХОСТЛИСТОВ ===
    def _update_exclusions(self):
        """Обновляет список исключений"""
        from log import log
        from updater import update_netrogat_list
        try:
            if hasattr(self._pw, 'hosts_manager'):
                self._pw.set_status("Обновление списка исключений...")
                update_netrogat_list(parent=self._pw, status_callback=self._pw.set_status)
                self._pw.set_status("Готово")
            else:
                QMessageBox.warning(self, "Ошибка", "Менеджер хостов не инициализирован")
        except Exception as e:
            log(f"Ошибка при обновлении исключений: {e}", level="ERROR")
            QMessageBox.critical(self, "Ошибка", f"Не удалось обновить исключения: {e}")

    def _update_custom_sites(self):
        """Обновляет список пользовательских сайтов"""
        from log import log
        from updater import update_other_list
        try:
            if hasattr(self._pw, 'hosts_manager'):
                self._pw.set_status("Обновление списка своих сайтов...")
                update_other_list(parent=self._pw, status_callback=self._pw.set_status)
                self._pw.set_status("Готово")
            else:
                QMessageBox.warning(self, "Ошибка", "Менеджер хостов не инициализирован")
        except Exception as e:
            log(f"Ошибка при обновлении своих сайтов: {e}", level="ERROR")
            QMessageBox.critical(self, "Ошибка", f"Не удалось обновить свои сайты: {e}")

    def _exclude_custom_sites(self):
        """Открывает файл для исключения пользовательских сайтов"""
        from log import log
        try:
            import subprocess
            import os
            from config import NETROGAT2_PATH

            if not os.path.exists(NETROGAT2_PATH):
                with open(NETROGAT2_PATH, 'w', encoding='utf-8') as f:
                    f.write("# Добавьте сюда свои домены, по одному на ОДНУ строку БЕЗ WWW И HTTP ИЛИ HTTPS! Пример: vk.com\n")

            # Пробуем разные редакторы по полным путям
            editors = [
                r'C:\Windows\System32\notepad.exe',                    # Стандартный блокнот
                r'C:\Windows\notepad.exe',                             # Альтернативный путь
                r'C:\Program Files\Notepad++\notepad++.exe',           # Notepad++
                r'C:\Program Files (x86)\Notepad++\notepad++.exe',     # Notepad++ x86
                r'C:\Program Files\VsCodium\VsCodium.exe',            # VsCodium
                r'C:\Users\{}\AppData\Local\Programs\Microsoft VS Code\Code.exe'.format(os.getenv('USERNAME', '')),  # VS Code
                r'C:\Program Files\Microsoft VS Code\Code.exe',  # VS Code (другой путь)
                r'C:\Windows\System32\write.exe',                      # WordPad
            ]
            
            success = False
            for editor in editors:
                if os.path.exists(editor):
                    try:
                        subprocess.Popen(f'"{editor}" "{NETROGAT2_PATH}"', shell=True)
                        editor_name = os.path.basename(editor)
                        self._pw.set_status(f"Открыт файл исключений в {editor_name}")
                        success = True
                        break
                    except (FileNotFoundError, OSError):
                        continue
            
            if not success:
                # Если ни один редактор не найден - открываем через ассоциацию Windows
                try:
                    self._pw.set_status("Открыт файл исключений в системном редакторе")
                except Exception as fallback_error:
                    # Последний вариант - показываем путь к файлу
                    QMessageBox.information(
                        self, 
                        "Мы не нашли никакой редактор :(",
                        f"Откройте файл вручную:\n{NETROGAT2_PATH}\n\n"
                        "Добавьте туда домены, по одному на строку."
                    )
                    self._pw.set_status("Создан файл исключений")

        except Exception as e:
            log(f"Ошибка при открытии файла исключений: {e}", level="ERROR")
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть файл: {e}")

    def _add_custom_sites(self):
        """Открывает файл для добавления пользовательских сайтов"""
        from log import log
        try:
            import subprocess
            import os
            from config import OTHER2_PATH

            if not os.path.exists(OTHER2_PATH):
                with open(OTHER2_PATH, 'w', encoding='utf-8') as f:
                    f.write("# Добавьте сюда свои домены, по одному на ОДНУ строку БЕЗ WWW И HTTP ИЛИ HTTPS! Пример: vk.com\n")

            # Пробуем разные редакторы по полным путям
            editors = [
                r'C:\Windows\System32\notepad.exe',                    # Стандартный блокнот
                r'C:\Windows\notepad.exe',                             # Альтернативный путь
                r'C:\Program Files\Notepad++\notepad++.exe',           # Notepad++
                r'C:\Program Files (x86)\Notepad++\notepad++.exe',     # Notepad++ x86
                r'C:\Users\{}\AppData\Local\Programs\Microsoft VS Code\Code.exe'.format(os.getenv('USERNAME', '')),  # VS Code
                r'C:\Program Files\Microsoft VS Code\Code.exe',  # VS Code (другой путь)
                r'C:\Windows\System32\write.exe',                      # WordPad
            ]
            
            success = False
            for editor in editors:
                if os.path.exists(editor):
                    try:
                        subprocess.Popen(f'"{editor}" "{OTHER2_PATH}"', shell=True)
                        editor_name = os.path.basename(editor)
                        self._pw.set_status(f"Открыт файл кастомных сайтов в {editor_name}")
                        success = True
                        break
                    except (FileNotFoundError, OSError):
                        continue
            
            if not success:
                # Если ни один редактор не найден - открываем через ассоциацию Windows
                try:
                    self._pw.set_status("Открыт файл кастомных сайтов в системном редакторе")
                except Exception as fallback_error:
                    # Последний вариант - показываем путь к файлу
                    QMessageBox.information(
                        self, 
                        "Мы не нашли никакой редактор :(",
                        f"Откройте файл вручную:\n{OTHER2_PATH}\n\n"
                        "Добавьте туда домены, по одному на строку."
                    )
                    self._pw.set_status("Создан файл кастомных сайтов")

        except Exception as e:
            log(f"Ошибка при открытии файла кастомных сайтов: {e}", level="ERROR")
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть файл: {e}")

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

    def show_logs(self):
        """
        Открывает окно просмотра логов без блокировки остального GUI.
        Держим ссылку на объект, чтобы его не удалил сборщик мусора.
        """
        try:
            from log import LogViewerDialog, global_logger
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
        """Асинхронно отправляет полный лог, но не чаще раза в 10 минут даже после перезапуска."""
        import time
        now = time.time()
        interval = 10 * 60  # 10 минут

        # читаем из настроек (реестра)
        last = self._settings.value("last_full_log_send", 0.0, type=float)

        if now - last < interval:
            remaining = int((interval - (now - last)) // 60) + 1
            QMessageBox.information(self._pw, "Отправка логов",
                f"Лог отправлялся недавно.\n"
                f"Следующая отправка возможна через {remaining} мин.")
            return

        # запоминаем текущее время
        self._settings.setValue("last_full_log_send", now)

        # Обычный асинхронный код отправки…
        from tgram.tg_log_full  import TgSendWorker
        from tgram.tg_log_delta import get_client_id

        LOG_PATH = "zapret_log.txt"
        caption  = f"Zapret log (ID: {get_client_id()}, v{APP_VERSION})"

        action = self.sender()                # QAction, вызвавший слот
        if action:
            action.setEnabled(False)

        wnd = self._pw             # объект LupiDPIApp

        if hasattr(wnd, "set_status"):
            wnd.set_status("Отправка полного лога…")

        # поток + воркер
        thr    = QThread(self)
        worker = TgSendWorker(LOG_PATH, caption)
        worker.moveToThread(thr)
        thr.started.connect(worker.run)

        def _on_done(ok: bool, extra_wait: float):
            if ok:
                QMessageBox.information(wnd, "Отправка", "Лог успешно отправлен.")
                if hasattr(wnd, "set_status"):
                    wnd.set_status("Полный лог отправлен в Telegram")
            else:
                QMessageBox.warning(wnd, "Отправка",
                    "Не удалось отправить лог (flood-wait).\n"
                    "Повторите позже.")
                if hasattr(wnd, "set_status"):
                    wnd.set_status("Не удалось отправить лог")
            # чистим
            worker.deleteLater()
            thr.quit(); thr.wait()
            if action:
                action.setEnabled(True)

        worker.finished.connect(_on_done)

        # чтобы поток и воркер не были собраны GC
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
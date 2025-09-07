# hosts/hosts_ui.py - ИСПРАВЛЕННАЯ ВЕРСИЯ
import os
from pathlib import Path
from PyQt6.QtWidgets import QMenu, QMessageBox, QDialog
from PyQt6.QtCore import QThread, QObject, pyqtSignal, QTimer
from log import log

class HostsUIManager:
    """Менеджер UI для работы с hosts файлом"""
    
    def __init__(self, parent, hosts_manager, status_callback=None):
        self.parent = parent
        self.hosts_manager = hosts_manager
        self.status_callback = status_callback or (lambda msg: None)
        
        # Ссылки на потоки для очистки
        self._hosts_operation_thread = None
        self._hosts_operation_worker = None
        self._adobe_thread = None
        self._adobe_worker = None

    def check_hosts_entries_status(self) -> bool:
        """Проверяет, активированы ли записи в hosts файле"""
        try:
            if self.hosts_manager:
                is_active = self.hosts_manager.is_proxy_domains_active()
                log(f"Статус proxy доменов в hosts: {is_active}", "DEBUG")
                return is_active
            else:
                log("hosts_manager не инициализирован", "⚠ WARNING")
                return False
        except Exception as e:
            log(f"Ошибка при проверке статуса hosts записей: {e}", "❌ ERROR")
            return False

    def cleanup(self):
        """Очистка ресурсов при закрытии приложения"""
        try:
            # Очистка потока hosts операций
            if self._hosts_operation_thread and self._hosts_operation_thread.isRunning():
                self._hosts_operation_thread.quit()
                self._hosts_operation_thread.wait(1000)
            
            if self._hosts_operation_worker:
                self._hosts_operation_worker.deleteLater()
            
            # Очистка потока Adobe операций
            if self._adobe_thread and self._adobe_thread.isRunning():
                self._adobe_thread.quit()
                self._adobe_thread.wait(1000)
            
            if self._adobe_worker:
                self._adobe_worker.deleteLater()
                
        except Exception as e:
            log(f"Ошибка при очистке HostsUIManager: {e}", "DEBUG")
    
    def toggle_proxy_domains(self, proxy_button):
        """Переключает состояние разблокировки: добавляет или удаляет записи из hosts"""
        try:
            if not self.hosts_manager:
                self.status_callback("Ошибка: менеджер hosts не инициализирован")
                return
            
            # Проверяем текущее состояние proxy и adobe
            is_proxy_active = self.hosts_manager.is_proxy_domains_active()
            is_adobe_active = self.hosts_manager.is_adobe_domains_active()
            
            # Создаем меню
            menu = QMenu(self.parent)
            
            # РАЗДЕЛ PROXY
            menu.addSection("🌐 Разблокировка сервисов")
            
            if is_proxy_active:
                disable_all_action = menu.addAction("Отключить всю разблокировку")
                select_domains_action = menu.addAction("Выбрать домены для отключения")
            else:
                enable_all_action = menu.addAction("Включить всю разблокировку")
                select_domains_action = menu.addAction("Выбрать домены для включения")
            
            menu.addSeparator()
            
            # РАЗДЕЛ ADOBE
            menu.addSection("🔒 Adobe")
            
            if is_adobe_active:
                adobe_disable_action = menu.addAction("🔓 Отключить блокировку Adobe")
            else:
                adobe_enable_action = menu.addAction("🔒 Включить блокировку Adobe")
            
            adobe_info_action = menu.addAction("ℹ️ О блокировке Adobe")
            
            menu.addSeparator()
            
            # ОБЩИЕ ДЕЙСТВИЯ
            open_hosts_action = menu.addAction("📝 Открыть файл hosts")
            
            # Показываем меню
            button_pos = proxy_button.mapToGlobal(proxy_button.rect().bottomLeft())
            action = menu.exec(button_pos)
            
            # Обрабатываем выбранное действие
            if action:
                action_text = action.text()
                
                # Общие действия
                if action_text == "📝 Открыть файл hosts":
                    self.open_hosts_file()
                
                # Proxy действия
                elif action_text == "Отключить всю разблокировку":
                    self.handle_proxy_disable_all_async(proxy_button)
                elif action_text == "Включить всю разблокировку":  
                    self.handle_proxy_enable_all_async(proxy_button)
                elif "Выбрать домены" in action_text:
                    self.handle_proxy_select_domains_async(proxy_button)
                
                # Adobe действия
                elif action_text == "🔓 Отключить блокировку Adobe":
                    self.handle_adobe_disable_async(proxy_button)
                elif action_text == "🔒 Включить блокировку Adobe":
                    self.handle_adobe_enable_async(proxy_button)
                elif action_text == "ℹ️ О блокировке Adobe":
                    self.show_adobe_info()
                    
        except Exception as e:
            log(f"❌ Ошибка в toggle_proxy_domains: {e}", "ERROR")
            import traceback
            log(traceback.format_exc(), "ERROR")

    def show_adobe_info(self):
        """Показывает информацию о блокировке Adobe"""
        try:
            # Импортируем здесь, чтобы избежать циклических импортов
            from .adobe_domains import ADOBE_DOMAINS
            
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setWindowTitle("Блокировка активации Adobe")
            msg.setText("Блокировка серверов активации Adobe")
            msg.setInformativeText(
                "Эта функция блокирует доступ к серверам активации Adobe, "
                "добавляя записи в файл hosts.\n\n"
                "⚠️ Внимание:\n"
                "• Используйте только для личного тестирования\n"
                "• Может нарушить работу некоторых функций Adobe\n"
                "• Требуется перезапуск приложений Adobe после изменений\n\n"
                f"Будет заблокировано {len(ADOBE_DOMAINS)} доменов Adobe."
            )
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg.exec()
        except Exception as e:
            log(f"❌ Ошибка в show_adobe_info: {e}", "ERROR")
            QMessageBox.critical(self.parent, "Ошибка", f"Не удалось показать информацию: {str(e)}")

    def handle_adobe_disable_async(self, proxy_button):
        """Асинхронно отключает блокировку Adobe"""
        try:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Question)
            msg.setWindowTitle("Отключение блокировки Adobe")
            msg.setText("Отключить блокировку активации Adobe?")
            msg.setInformativeText(
                "Это действие удалит записи блокировки Adobe из файла hosts.\n\n"
                "После этого приложения Adobe смогут связаться с серверами активации."
            )
            msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            
            if msg.exec() == QMessageBox.StandardButton.Yes:
                self.perform_adobe_operation_async('remove', proxy_button)
            else:
                self.status_callback("Операция отменена.")
        except Exception as e:
            log(f"❌ Ошибка в handle_adobe_disable_async: {e}", "ERROR")

    def handle_adobe_enable_async(self, proxy_button):
        """Асинхронно включает блокировку Adobe"""
        try:
            # Импортируем здесь
            from .adobe_domains import ADOBE_DOMAINS
            
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setWindowTitle("Блокировка активации Adobe")
            msg.setText("Включить блокировку серверов активации Adobe?")
            msg.setInformativeText(
                f"Будет добавлено {len(ADOBE_DOMAINS)} записей в файл hosts для блокировки:\n"
                "• Серверов активации\n"
                "• Серверов валидации лицензий\n"
                "• DNS серверов Adobe\n\n"
                "⚠️ ВАЖНО: После применения необходимо полностью закрыть все приложения Adobe!"
            )
            msg.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
            
            if msg.exec() == QMessageBox.StandardButton.Ok:
                self.perform_adobe_operation_async('add', proxy_button)
            else:
                self.status_callback("Операция отменена.")
        except Exception as e:
            log(f"❌ Ошибка в handle_adobe_enable_async: {e}", "ERROR")

    def perform_adobe_operation_async(self, operation, proxy_button):
        """Выполняет операцию с Adobe доменами асинхронно"""
        log(f"🔵 perform_adobe_operation_async начат: operation={operation}", "DEBUG")
        
        try:
            # Показываем индикатор загрузки
            if hasattr(self.parent, 'set_proxy_button_loading'):
                self.parent.set_proxy_button_loading(True, "Обработка Adobe...")
            
            proxy_button.setEnabled(False)
            
            # Создаем воркер
            worker = AdobeWorker(self.hosts_manager, operation)
            thread = QThread()
            
            # Перемещаем воркер в поток
            worker.moveToThread(thread)
            
            # Подключаем сигналы
            thread.started.connect(worker.run)
            worker.progress.connect(self.status_callback)
            worker.finished.connect(
                lambda success, msg: self.on_adobe_operation_complete(success, msg, proxy_button)
            )
            
            # Очистка после завершения
            worker.finished.connect(thread.quit)
            worker.finished.connect(worker.deleteLater)
            thread.finished.connect(thread.deleteLater)
            
            # Сохраняем ссылки
            self._adobe_thread = thread
            self._adobe_worker = worker
            
            # Запускаем поток
            thread.start()
            log("🔵 Adobe поток запущен", "DEBUG")
            
        except Exception as e:
            log(f"❌ Ошибка в perform_adobe_operation_async: {e}", "ERROR")
            import traceback
            log(traceback.format_exc(), "ERROR")
            
            # Восстанавливаем состояние кнопки при ошибке
            proxy_button.setEnabled(True)
            if hasattr(self.parent, 'set_proxy_button_loading'):
                self.parent.set_proxy_button_loading(False)
            
            QMessageBox.critical(self.parent, "Ошибка", f"Не удалось выполнить операцию: {str(e)}")

    def on_adobe_operation_complete(self, success, message, proxy_button):
        """Обработчик завершения операции с Adobe"""
        try:
            log(f"🟢 on_adobe_operation_complete: success={success}, message={message}", "DEBUG")
            
            # Убираем индикатор загрузки
            if hasattr(self.parent, 'set_proxy_button_loading'):
                self.parent.set_proxy_button_loading(False)
            
            # Разблокируем кнопку
            proxy_button.setEnabled(True)
            
            # Показываем результат
            self.status_callback(message)
            
            # Обновляем состояние кнопки proxy
            if hasattr(self.parent, 'ui_manager'):
                QTimer.singleShot(100, self.parent.ui_manager.update_proxy_button_state)
            elif hasattr(self.parent, 'update_proxy_button_state'):
                QTimer.singleShot(100, self.parent.update_proxy_button_state)
            
            # Показываем уведомление
            if success:
                if hasattr(self.parent, 'tray_manager') and self.parent.tray_manager:
                    try:
                        self.parent.tray_manager.show_notification(
                            "Adobe блокировка",
                            message
                        )
                    except:
                        pass
            else:
                QMessageBox.warning(self.parent, "Внимание", message)
                
        except Exception as e:
            log(f"❌ Ошибка в on_adobe_operation_complete: {e}", "ERROR")
            import traceback
            log(traceback.format_exc(), "ERROR")

    # ... остальные методы остаются без изменений ...

    def handle_proxy_disable_all_async(self, proxy_button):
        """Асинхронно обрабатывает отключение всей разблокировки"""
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Question)
        msg.setWindowTitle("Отключение разблокировки")
        msg.setText("Отключить разблокировку сервисов через hosts-файл?")
        msg.setInformativeText(
            "Это действие удалит добавленные ранее записи из файла hosts.\n\n"
            "Для применения изменений ОБЯЗАТЕЛЬНО СЛЕДУЕТ закрыть и открыть веб-браузер и/или приложение Spotify!"
        )
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if msg.exec() == QMessageBox.StandardButton.Yes:
            self.perform_hosts_operation_async('remove', proxy_button)
        else:
            self.status_callback("Операция отменена.")

    def handle_proxy_enable_all_async(self, proxy_button):
        """Асинхронно обрабатывает включение всей разблокировки"""
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle("Разблокировка через hosts-файл")
        msg.setText("Установка соединения к proxy-серверу через файл hosts")
        msg.setInformativeText(
            "Добавление этих сайтов в обычные списки Zapret не поможет их разблокировать, "
            "так как доступ к ним заблокирован для территории РФ со стороны самих сервисов "
            "(без участия Роскомнадзора).\n\n"
            "Для применения изменений ОБЯЗАТЕЛЬНО СЛЕДУЕТ закрыть и открыть веб-браузер "
            "(не только сайт, а всю программу) и/или приложение Spotify!"
        )
        msg.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
        
        if msg.exec() == QMessageBox.StandardButton.Ok:
            self.perform_hosts_operation_async('add', proxy_button)
        else:
            self.status_callback("Операция отменена.")

    def handle_proxy_select_domains_async(self, proxy_button):
        """Асинхронно обрабатывает выбор доменов для разблокировки"""
        log("🔵 handle_proxy_select_domains_async начат", "DEBUG")
        
        from .menu import HostsSelectorDialog
        from .proxy_domains import PROXY_DOMAINS
        
        # Получаем текущие активные домены
        current_active = self.hosts_manager.get_active_domains()
        log(f"Найдено активных доменов: {len(current_active)}", "DEBUG")
        
        # Показываем диалог выбора
        dialog = HostsSelectorDialog(self.parent, current_active)
        
        result = dialog.exec()
        log(f"Диалог закрыт с результатом: {result}", "DEBUG")
        
        if result == QDialog.DialogCode.Accepted:
            selected_domains = dialog.get_selected_domains()
            log(f"Выбрано доменов: {len(selected_domains)}", "DEBUG")
            self.perform_hosts_operation_async('select', proxy_button, selected_domains)
        else:
            log("Диалог отменен", "DEBUG")

    def perform_hosts_operation_async(self, operation, proxy_button, domains=None):
        """Выполняет операцию с hosts файлом асинхронно"""
        log(f"🔵 perform_hosts_operation_async начат: operation={operation}", "DEBUG")
        
        try:
            # Показываем индикатор загрузки
            if hasattr(self.parent, 'set_proxy_button_loading'):
                self.parent.set_proxy_button_loading(True, "Обработка...")
            
            proxy_button.setEnabled(False)
            
            # Создаем воркер
            worker = HostsWorker(self.hosts_manager, operation, domains)
            thread = QThread()
            
            # Перемещаем воркер в поток
            worker.moveToThread(thread)
            
            # Подключаем сигналы
            thread.started.connect(worker.run)
            worker.progress.connect(self.status_callback)
            worker.finished.connect(
                lambda success, msg: self.on_hosts_operation_complete(success, msg, proxy_button)
            )
            
            # Очистка после завершения
            worker.finished.connect(thread.quit)
            worker.finished.connect(worker.deleteLater)
            thread.finished.connect(thread.deleteLater)
            
            # Сохраняем ссылки
            self._hosts_operation_thread = thread
            self._hosts_operation_worker = worker
            
            # Запускаем поток
            thread.start()
            log("🔵 Hosts поток запущен", "DEBUG")
            
        except Exception as e:
            log(f"❌ Ошибка в perform_hosts_operation_async: {e}", "ERROR")
            import traceback
            log(traceback.format_exc(), "ERROR")
            
            # Восстанавливаем состояние кнопки при ошибке
            proxy_button.setEnabled(True)
            if hasattr(self.parent, 'set_proxy_button_loading'):
                self.parent.set_proxy_button_loading(False)
            
            QMessageBox.critical(self.parent, "Ошибка", f"Не удалось выполнить операцию: {str(e)}")

    def on_hosts_operation_complete(self, success, message, proxy_button):
        """Обработчик завершения асинхронной операции с hosts"""
        log(f"🟢 on_hosts_operation_complete вызван: success={success}, message={message}", "DEBUG")
        
        try:
            # Убираем индикатор загрузки
            if hasattr(self.parent, 'set_proxy_button_loading'):
                self.parent.set_proxy_button_loading(False)
            
            # Разблокируем кнопку
            proxy_button.setEnabled(True)
            
            # Показываем результат
            self.status_callback(message)
            
            # Обновляем состояние кнопки
            if hasattr(self.parent, 'ui_manager'):
                QTimer.singleShot(100, self.parent.ui_manager.update_proxy_button_state)
            elif hasattr(self.parent, 'update_proxy_button_state'):
                QTimer.singleShot(100, self.parent.update_proxy_button_state)
            
            # Показываем уведомление
            if success:
                if hasattr(self.parent, 'tray_manager') and self.parent.tray_manager:
                    try:
                        self.parent.tray_manager.show_notification(
                            "Операция завершена",
                            message
                        )
                    except:
                        pass
            else:
                QMessageBox.warning(self.parent, "Внимание", message)
                
            log("🟢 on_hosts_operation_complete завершен", "DEBUG")
            
        except Exception as e:
            log(f"❌ Ошибка в on_hosts_operation_complete: {e}", "ERROR")
            import traceback
            log(traceback.format_exc(), "ERROR")

    def cleanup_hosts_thread(self):
        """Отложенная очистка потока и воркера"""
        try:
            log("🔵 Выполняем отложенную очистку потока", "DEBUG")
            
            if hasattr(self, '_hosts_operation_worker') and self._hosts_operation_worker:
                self._hosts_operation_worker.deleteLater()
                self._hosts_operation_worker = None
                
            if hasattr(self, '_hosts_operation_thread') and self._hosts_operation_thread:
                if self._hosts_operation_thread.isRunning():
                    self._hosts_operation_thread.quit()
                    self._hosts_operation_thread.wait(1000)
                self._hosts_operation_thread.deleteLater()
                self._hosts_operation_thread = None
                
            log("🔵 Очистка потока завершена", "DEBUG")
            
        except Exception as e:
            log(f"Ошибка при очистке потока: {e}", "DEBUG")

    def open_hosts_file(self):
        """Открывает файл hosts в текстовом редакторе с правами администратора"""
        try:
            hosts_path = r"C:\Windows\System32\drivers\etc\hosts"
            
            if not os.path.exists(hosts_path):
                QMessageBox.warning(self.parent, "Файл не найден", 
                                f"Файл hosts не найден по пути:\n{hosts_path}")
                return
            
            editors = [
                r'C:\Program Files\Notepad++\notepad++.exe',
                r'C:\Program Files (x86)\Notepad++\notepad++.exe',
                r'C:\Windows\System32\notepad.exe',
            ]
            
            opened = False
            
            for editor in editors:
                if os.path.exists(editor):
                    try:
                        import ctypes
                        ctypes.windll.shell32.ShellExecuteW(
                            None, 
                            "runas",
                            editor, 
                            hosts_path,
                            None, 
                            1
                        )
                        
                        editor_name = os.path.basename(editor)
                        self.status_callback(f"Файл hosts открыт в {editor_name}")
                        log(f"Файл hosts успешно открыт в {editor_name}")
                        opened = True
                        break
                        
                    except Exception as e:
                        log(f"Не удалось открыть в {editor}: {e}")
                        continue
            
            if not opened:
                try:
                    os.startfile(hosts_path)
                    self.status_callback("Файл hosts открыт")
                    log("Файл hosts открыт через системную ассоциацию")
                except Exception as e:
                    QMessageBox.critical(self.parent, "Ошибка", 
                                        "Не удалось открыть файл hosts")
                    log(f"Не удалось открыть файл hosts: {e}")
                    
        except Exception as e:
            error_msg = f"Ошибка при открытии файла hosts: {str(e)}"
            log(error_msg, level="❌ ERROR")
            self.status_callback(error_msg)


# Классы воркеров вынесены за пределы класса HostsUIManager
class AdobeWorker(QObject):
    """Воркер для асинхронных операций с Adobe доменами"""
    finished = pyqtSignal(bool, str)
    progress = pyqtSignal(str)
    
    def __init__(self, hosts_manager, operation):
        super().__init__()
        self.hosts_manager = hosts_manager
        self.operation = operation
        log(f"🔵 AdobeWorker создан: operation={operation}", "DEBUG")
    
    def run(self):
        """Выполняет операцию"""
        log(f"🔵 AdobeWorker.run() начат: operation={self.operation}", "DEBUG")
        try:
            success = False
            message = ""
            
            if self.operation == 'add':
                self.progress.emit("Добавление доменов Adobe в hosts...")
                log("🔵 Вызываем add_adobe_domains()", "DEBUG")
                success = self.hosts_manager.add_adobe_domains()
                log(f"🔵 add_adobe_domains завершен: success={success}", "DEBUG")
                if success:
                    message = "Блокировка Adobe активирована. Перезапустите приложения Adobe."
                else:
                    message = "Не удалось активировать блокировку Adobe."
            
            elif self.operation == 'remove':
                self.progress.emit("Удаление доменов Adobe из hosts...")
                log("🔵 Вызываем remove_adobe_domains()", "DEBUG")
                success = self.hosts_manager.remove_adobe_domains()
                log(f"🔵 remove_adobe_domains завершен: success={success}", "DEBUG")
                if success:
                    message = "Блокировка Adobe отключена."
                else:
                    message = "Не удалось отключить блокировку Adobe."
            
            log(f"🔵 AdobeWorker.run() завершается, испускаем сигнал finished", "DEBUG")
            self.finished.emit(success, message)
            log(f"🔵 Сигнал finished испущен", "DEBUG")
            
        except Exception as e:
            log(f"❌ Исключение в AdobeWorker.run(): {e}", "ERROR")
            import traceback
            log(traceback.format_exc(), "ERROR")
            self.finished.emit(False, f"Ошибка: {str(e)}")


class HostsWorker(QObject):
    """Воркер для асинхронных операций с hosts файлом"""
    finished = pyqtSignal(bool, str)
    progress = pyqtSignal(str)
    
    def __init__(self, hosts_manager, operation, domains=None):
        super().__init__()
        self.hosts_manager = hosts_manager
        self.operation = operation
        self.domains = domains
        log(f"🔵 HostsWorker создан: operation={operation}", "DEBUG")
    
    def run(self):
        """Выполняет операцию"""
        log(f"🔵 HostsWorker.run() начат: operation={self.operation}", "DEBUG")
        try:
            success = False
            message = ""
            
            if self.operation == 'add':
                self.progress.emit("Добавление доменов в hosts...")
                success = self.hosts_manager.add_proxy_domains()
                if success:
                    message = "Разблокировка включена. Перезапустите браузер."
                else:
                    message = "Не удалось включить разблокировку."
                    
            elif self.operation == 'remove':
                self.progress.emit("Удаление доменов из hosts...")
                success = self.hosts_manager.remove_proxy_domains()
                if success:
                    message = "Разблокировка отключена. Перезапустите браузер."
                else:
                    message = "Не удалось отключить разблокировку."
                    
            elif self.operation == 'select' and self.domains:
                self.progress.emit(f"Применение {len(self.domains)} доменов...")
                success = self.hosts_manager.apply_selected_domains(self.domains)
                if success:
                    message = f"Применено {len(self.domains)} доменов. Перезапустите браузер."
                else:
                    message = "Не удалось применить выбранные домены."
            
            self.finished.emit(success, message)
            
        except Exception as e:
            log(f"❌ Исключение в HostsWorker.run(): {e}", "ERROR")
            import traceback
            log(traceback.format_exc(), "ERROR")
            self.finished.emit(False, f"Ошибка: {str(e)}")
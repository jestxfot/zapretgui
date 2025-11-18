# hosts/hosts_ui.py - Обновленная версия без выпадающего меню
import os
from pathlib import Path
from PyQt6.QtWidgets import QMessageBox, QDialog
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
        """Открывает диалог выбора доменов для разблокировки"""
        try:
            if not self.hosts_manager:
                self.status_callback("Ошибка: менеджер hosts не инициализирован")
                return
            
            # Сразу открываем диалог выбора доменов
            self.open_domains_selector_dialog(proxy_button)
                    
        except Exception as e:
            log(f"❌ Ошибка в toggle_proxy_domains: {e}", "ERROR")
            import traceback
            log(traceback.format_exc(), "ERROR")

    def open_domains_selector_dialog(self, proxy_button):
        """Открывает диалог выбора доменов"""
        log("🔵 Открытие диалога выбора доменов", "DEBUG")
        
        from .menu import HostsSelectorDialog
        from .proxy_domains import PROXY_DOMAINS
        
        # Получаем текущие активные домены
        current_active = self.hosts_manager.get_active_domains()
        log(f"Найдено активных доменов: {len(current_active)}", "DEBUG")
        
        # Показываем диалог выбора
        dialog = HostsSelectorDialog(self.parent, current_active)
        
        # Устанавливаем состояние Adobe, если метод существует
        if hasattr(dialog, 'add_adobe_section'):
            dialog.add_adobe_section(
                self.hosts_manager.is_adobe_domains_active(),
                self.handle_adobe_toggle
            )
        else:
            # Альтернативный способ - напрямую устанавливаем callback
            dialog.adobe_callback = self.handle_adobe_toggle
            dialog.is_adobe_active = self.hosts_manager.is_adobe_domains_active()
            
            # Обновляем кнопку Adobe если она существует
            if hasattr(dialog, 'adobe_btn'):
                if dialog.is_adobe_active:
                    dialog.adobe_btn.setText("🔓 Отключить")
                else:
                    dialog.adobe_btn.setText("🔒 Включить")
        
        result = dialog.exec()
        log(f"Диалог закрыт с результатом: {result}", "DEBUG")
        
        if result == QDialog.DialogCode.Accepted:
            selected_domains = dialog.get_selected_domains()
            log(f"Выбрано доменов: {len(selected_domains)}", "DEBUG")
            
            # Применяем выбранные домены
            self.perform_hosts_operation_async('select', proxy_button, selected_domains)
        else:
            log("Диалог отменен", "DEBUG")

    def handle_adobe_toggle(self, enable):
        """Обработчик переключения Adobe блокировки"""
        if enable:
            self.handle_adobe_enable_async(None)
        else:
            self.handle_adobe_disable_async(None)

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
            
            if proxy_button:
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
            if proxy_button:
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
            if proxy_button:
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
                # Показываем информационное сообщение
                QMessageBox.information(
                    self.parent, 
                    "Успешно",
                    message + "\n\nДля применения изменений обязательно перезапустите браузер!"
                )
                
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


# Классы воркеров
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
            
            if self.operation == 'select' and self.domains is not None:
                if len(self.domains) == 0:
                    # ✅ Если не выбрано ни одного домена - ПОЛНОСТЬЮ очищаем hosts
                    self.progress.emit("Полная очистка hosts файла...")
                    success = self.hosts_manager.clear_hosts_file()  # ← ВОТ ЭТОТ ВЫЗОВ
                    if success:
                        message = "Файл hosts полностью очищен (восстановлено базовое содержимое Windows)."
                    else:
                        message = "Не удалось очистить hosts файл."
                else:
                    # Применяем выбранные домены
                    self.progress.emit(f"Применение {len(self.domains)} доменов...")
                    success = self.hosts_manager.apply_selected_domains(self.domains)
                    if success:
                        message = f"Применено {len(self.domains)} доменов."
                    else:
                        message = "Не удалось применить выбранные домены."
            
            self.finished.emit(success, message)
            
        except Exception as e:
            log(f"❌ Исключение в HostsWorker.run(): {e}", "ERROR")
            import traceback
            log(traceback.format_exc(), "ERROR")
            self.finished.emit(False, f"Ошибка: {str(e)}")
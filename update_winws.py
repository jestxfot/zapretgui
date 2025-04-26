import os
import shutil
import subprocess
import sys
from PyQt5.QtWidgets import QMessageBox
from main import get_last_strategy


def update_winws_exe(app_instance):
    """Обновляет файл winws.exe до последней версии с GitHub"""
    try:
        # Проверяем наличие модуля requests
        try:
            import requests
        except ImportError:
            app_instance.set_status("Установка зависимостей...")
            subprocess.run([sys.executable, "-m", "pip", "install", "requests"], 
                        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            import requests
        
        # Импортируем необходимые константы
        from config import BIN_FOLDER
        from downloader import DOWNLOAD_URLS
        
        # URL для загрузки файла
        download_url = "https://github.com/bol-van/zapret-win-bundle/raw/refs/heads/master/zapret-winws/winws.exe"
        
        # Проверяем запущен ли Zapret и останавливаем его
        process_running = app_instance.dpi_starter.check_process_running()
        service_running = app_instance.service_manager.check_service_exists()
        
        # Если запущена служба, показываем предупреждение и выходим
        if service_running:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("Служба активна")
            msg.setText("Невозможно обновить winws.exe, пока запущена служба Zapret.")
            msg.setInformativeText("Пожалуйста, сначала отключите автозапуск, затем повторите попытку обновления.")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec_()
            return
            
        # Устанавливаем флаги для предотвращения ложных ошибок
        app_instance.manually_stopped = True
        app_instance.process_restarting = True
        
        # Если процесс запущен, останавливаем его
        if process_running and not service_running:
            app_instance.set_status("Останавливаем Zapret для обновления...")
            app_instance.dpi_starter.stop_dpi()
            
        # Загружаем файл с отображением прогресса
        app_instance.set_status("Загрузка новой версии winws.exe...")
        
        # Создаем временный файл для загрузки
        temp_file = os.path.join(BIN_FOLDER, "winws_new.exe")
        target_file = os.path.join(BIN_FOLDER, "winws.exe")
        
        # Загружаем файл
        response = requests.get(download_url, stream=True)
        total_size = int(response.headers.get('content-length', 0))
        
        if response.status_code == 200:
            with open(temp_file, 'wb') as f:
                downloaded = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        # Обновляем статус каждые 10%
                        percent = int(downloaded / total_size * 100)
                        if percent % 10 == 0:
                            app_instance.set_status(f"Загрузка: {percent}%")
            
            # Проверяем, что временный файл успешно создан
            if not os.path.exists(temp_file):
                app_instance.set_status("Ошибка: загруженный файл не создан")
                return
            
            # Заменяем старый файл новым
            app_instance.set_status("Заменяем файл winws.exe...")
            try:
                # Создаем резервную копию
                if os.path.exists(target_file):
                    backup_file = os.path.join(BIN_FOLDER, "winws_backup.exe")
                    shutil.copy2(target_file, backup_file)
                
                # Заменяем файл
                shutil.move(temp_file, target_file)
                
                app_instance.set_status("Файл winws.exe успешно обновлен")

                # Перезапускаем Zapret, если он был запущен ранее
                if process_running and not service_running:
                    app_instance.set_status("Перезапуск Zapret с обновленной версией...")
                    
                    # Получаем текущую стратегию из метки или атрибута
                    selected_mode = None
                    if hasattr(app_instance, 'current_strategy_name') and app_instance.current_strategy_name:
                        selected_mode = app_instance.current_strategy_name
                    else:
                        selected_mode = app_instance.current_strategy_label.text()
                        if selected_mode == "Не выбрана":
                            selected_mode = get_last_strategy()
                    
                    # Запускаем DPI с выбранной стратегией
                    success = app_instance.start_dpi(selected_mode=selected_mode)
                    if success:    
                        app_instance.update_ui(running=True)
                        QMessageBox.information(app_instance, "Обновление завершено", 
                                            "Файл winws.exe успешно обновлен и Zapret перезапущен.")
                    else:
                        app_instance.check_process_status()
                        QMessageBox.warning(app_instance, "Внимание", 
                                        "Файл winws.exe обновлен, но перезапуск Zapret не удался. "
                                        "Попробуйте запустить его вручную.")
                else:
                    QMessageBox.information(app_instance, "Обновление завершено", 
                                        "Файл winws.exe успешно обновлен.")
            except Exception as e:
                app_instance.set_status(f"Ошибка при замене файла: {str(e)}")
                QMessageBox.critical(app_instance, "Ошибка обновления", 
                                f"Не удалось заменить файл winws.exe:\n{str(e)}")
        else:
            app_instance.set_status(f"Ошибка загрузки файла: {response.status_code}")
            QMessageBox.critical(app_instance, "Ошибка загрузки", 
                            f"Не удалось загрузить файл winws.exe. Код ответа: {response.status_code}")
    except Exception as e:
        error_msg = f"Ошибка при обновлении winws.exe: {str(e)}"
        print(error_msg)
        app_instance.set_status(error_msg)
        QMessageBox.critical(app_instance, "Ошибка", error_msg)
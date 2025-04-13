import os
import sys
import subprocess
from PyQt5.QtWidgets import QMessageBox
from urls import VERSION_URL, UPDATER_BAT_URL, EXE_UPDATE_URL
from config import APP_VERSION
from log import log

def check_for_update(parent, status_callback=None):
    """Проверяет наличие обновлений и запускает процесс обновления через BAT-файл"""
    try:
        # Удобная функция для обновления статуса
        def set_status(message):
            if status_callback:
                status_callback(message)
            else:
                log(message, level="UPDATE")

        # Проверяем наличие модуля requests
        try:
            import requests
            from packaging import version
        except ImportError:
            set_status("Установка зависимостей для проверки обновлений...")
            subprocess.run([sys.executable, "-m", "pip", "install", "requests packaging"], 
                        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            import requests
            from packaging import version
            
        # URL для проверки обновлений
        version_url = VERSION_URL
        
        log(f"Проверка наличия обновлений по адресу: {version_url}", level="UPDATE")
        response = requests.get(version_url, timeout=5)
        if response.status_code == 200:
            info = response.json()
            latest_version = info.get("version")
            release_notes = info.get("release_notes", "Нет информации об изменениях")
            
            # URL для скачивания BAT-файла обновления
            bat_url = info.get("updater_bat_url", UPDATER_BAT_URL)
            
            # Сравниваем версии
            if version.parse(latest_version) > version.parse(APP_VERSION):
                # Нашли обновление
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Information)
                msg.setWindowTitle("Доступно обновление")
                msg.setText(f"Доступна новая версия: {latest_version}\nТекущая версия: {APP_VERSION}")
                
                # Добавляем информацию о выпуске
                msg.setInformativeText(f"Список изменений:\n{release_notes}\n\nХотите обновиться сейчас?")
                
                msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                if msg.exec_() == QMessageBox.Yes:
                    log(f"Пользователь согласился на обновление до версии {latest_version}", level="UPDATE")
                    
                    # Получаем путь к текущему исполняемому файлу
                    exe_path = os.path.abspath(sys.executable)
                    
                    # Если это не скомпилированное приложение, updater не сможет заменить .py файл
                    if not getattr(sys, 'frozen', False):
                        QMessageBox.warning(parent, "Обновление невозможно", 
                                        "Автоматическое обновление возможно только для скомпилированных (.exe) версий программы.")
                        return
                    
                    # Скачиваем BAT-файл обновления
                    try:
                        # Создаем временный файл для скрипта обновления
                        updater_bat = os.path.join(os.path.dirname(exe_path), "update_zapret.bat")

                        log(f"Скачивание BAT-файла обновления с {bat_url}", level="UPDATE")
                        bat_response = requests.get(bat_url)
                        bat_content = bat_response.text

                        # Заменяем переменные в BAT-файле
                        bat_content = bat_content.replace("{EXE_PATH}", exe_path)
                        bat_content = bat_content.replace("{EXE_DIR}", os.path.dirname(exe_path))
                        bat_content = bat_content.replace("{EXE_NAME}", os.path.basename(exe_path))
                        bat_content = bat_content.replace("{CURRENT_VERSION}", APP_VERSION)
                        bat_content = bat_content.replace("{NEW_VERSION}", latest_version)

                        # Сохраняем BAT-файл
                        with open(updater_bat, 'w', encoding='utf-8') as f:
                            f.write(bat_content)
                        
                        log(f"Запуск BAT-файла обновления: {updater_bat}", level="UPDATE")
                        # Изменим способ запуска BAT-файла, чтобы показать консоль
                        subprocess.Popen(f'cmd /c start cmd /k "{updater_bat}"', shell=True)
                        
                        # Завершаем текущий процесс после небольшой задержки
                        set_status("Запущен процесс обновления. Приложение будет перезапущено.")

                        from PyQt5.QtCore import QTimer
                        QTimer.singleShot(2000, lambda: sys.exit(0))
                        
                    except Exception as e:
                        set_status(f"Ошибка при подготовке обновления: {str(e)}")
                        log(f"Ошибка при подготовке обновления: {str(e)}", level="ERROR")
                        # Если произошла ошибка при скачивании BAT-файла, создаем его локально
                        try:
                            # Создаем BAT-файл вручную
                            updater_bat = os.path.join(os.path.dirname(exe_path), "update_zapret.bat")
                            with open(updater_bat, 'w', encoding='utf-8') as f:
                                f.write(f"""@echo off
                                chcp 65001 > nul
                                echo UPDATE ZAPRET!
                                title Old v{APP_VERSION} to new v{latest_version}

                                echo Wait...
                                timeout /t 3 /nobreak > nul
                                del /f /q "{exe_path}" >nul 2>&1
                                echo  Download new version...
                                powershell -Command "[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12; (New-Object System.Net.WebClient).DownloadFile('{EXE_UPDATE_URL}', '%TEMP%\\zapret_new.exe')"

                                if %ERRORLEVEL% NEQ 0 (
                                    echo Error download update!
                                    pause
                                    exit /b 1
                                )

                                echo Replace old to new version
                                copy /Y "%TEMP%\\zapret_new.exe" "{exe_path}"

                                if %ERRORLEVEL% NEQ 0 (
                                    echo "Не удалось заменить файл. Проверьте права доступа."
                                    pause
                                    exit /b 1
                                )

                                set CURRENT_DIR=%CD%
                                cd /d "{os.path.dirname(exe_path)}"
                                cd /d %CURRENT_DIR%
                                echo Del temp file...
                                del "%TEMP%\\zapret_new.exe" >nul 2>&1
                                echo Update done success!
                                echo Please run Zapret (main.exe) again!
                                del "%~f0" >nul 2>&1
                                """)
                                                            
                            # Запускаем BAT-файл
                            subprocess.Popen(f'cmd /c start cmd /k "{updater_bat}"', shell=True)
                            
                            # Завершаем текущий процесс после небольшой задержки
                            set_status("Запущен процесс обновления. Приложение будет перезапущено.")
                            QTimer.singleShot(2000, lambda: sys.exit(0))
                        except Exception as inner_e:
                            log(f"Ошибка при создании BAT-файла: {str(inner_e)}", level="ERROR")
                            set_status(f"Критическая ошибка обновления: {str(inner_e)}")
                else:
                    log(f"Пользователь отказался от обновления {latest_version}", level="UPDATE")
                    set_status(f"У вас установлена последняя версия ({latest_version}).")
            else:
                log(f"У вас установлена последняя версия ({latest_version})", level="UPDATE")
                set_status(f"У вас установлена последняя версия ({latest_version}).")
        else:
            log(f"Ошибка при получении версии: {response.status_code}", level="ERROR")
            set_status(f"Не удалось проверить обновления.\nКод: {response.status_code}")

    except Exception as e:
        log(f"Ошибка при проверке обновлений: {str(e)}", level="ERROR")
        if status_callback:
            status_callback(f"Ошибка при проверке обновлений: {str(e)}")
# stop.py

import subprocess, time

def stop_dpi(self):
    """Останавливает процесс DPI, используя прямые команды остановки"""
    try:
        from log import log
        log("Остановка Zapret", level="INFO")
        
        # Используем прямые команды остановки вместо ненадежного stop.bat
        process_stopped = False
        
        # Метод 1: taskkill (наиболее надежный)
        log("Метод 1: Остановка через taskkill /F /IM winws.exe /T", level="INFO")
        try:
            subprocess.run(
                "taskkill /F /IM winws.exe /T", 
                shell=True, 
                check=False, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE
            )
            # Даем время системе на обработку команды
            time.sleep(1)
            if not self.dpi_starter.check_process_running():
                process_stopped = True
                log("Процесс успешно остановлен через taskkill", level="INFO")
        except Exception as e:
            log(f"Ошибка при использовании taskkill: {str(e)}", level="ERROR")
        
        # Если taskkill не помог, пробуем метод 2: PowerShell
        if not process_stopped:
            log("Метод 2: Остановка через PowerShell", level="INFO")
            try:
                subprocess.run(
                    'powershell -Command "Get-Process winws -ErrorAction SilentlyContinue | Stop-Process -Force"',
                    shell=True,
                    check=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                # Даем время системе на обработку команды
                time.sleep(1)
                if not self.dpi_starter.check_process_running():
                    process_stopped = True
                    log("Процесс успешно остановлен через PowerShell", level="INFO")
            except Exception as e:
                log(f"Ошибка при использовании PowerShell: {str(e)}", level="ERROR")
        
        # Метод 3: wmic
        if not process_stopped:
            log("Метод 3: Остановка через wmic", level="INFO")
            try:
                subprocess.run(
                    "wmic process where name='winws.exe' call terminate",
                    shell=True,
                    check=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                # Даем время системе на обработку команды
                time.sleep(1)
                if not self.dpi_starter.check_process_running():
                    process_stopped = True
                    log("Процесс успешно остановлен через wmic", level="INFO")
            except Exception as e:
                log(f"Ошибка при использовании wmic: {str(e)}", level="ERROR")
        
        # Дополнительно останавливаем службы
        try:
            log("Остановка служб WinDivert", level="INFO")
            subprocess.run("sc stop windivert", shell=True, check=False)
            subprocess.run("sc delete windivert", shell=True, check=False)
        except Exception as e:
            log(f"Ошибка при остановке служб: {str(e)}", level="ERROR")
        
        # Финальная проверка
        if self.dpi_starter.check_process_running():
            log("ВНИМАНИЕ: Не удалось остановить все процессы winws.exe", level="WARNING")
            self.set_status("Не удалось полностью остановить Zapret")
        else:
            # Обновляем UI
            self.update_ui(running=False)
            self.set_status("Zapret успешно остановлен")
            log("Запрет успешно остановлен", level="INFO")
        
        # Обновляем статус
        self.on_process_status_changed(self.dpi_starter.check_process_running(silent=True))
            
    except Exception as e:
        from log import log
        log(f"Ошибка при остановке DPI: {str(e)}", level="ERROR")
        self.set_status(f"Ошибка при остановке: {str(e)}")


##############################

import os, subprocess, time
from log import log

def stop_dpi(self):
    """
    Останавливает процесс DPI.
    
    Returns:
        bool: True при успешной остановке, False при ошибке
    """
    try:
        log("======================== Stop DPI ========================", level="START")
        
        # Проверяем наличие службы
        service_exists = False
        try:
            from service import ServiceManager
            service_manager = ServiceManager(
                winws_exe=self.winws_exe,
                bin_folder=self.bin_folder,
                lists_folder=self.lists_folder,
                status_callback=self.set_status
            )
            service_exists = service_manager.check_service_exists()
        except Exception as e:
            log(f"Ошибка при проверке службы: {str(e)}", level="ERROR")
            
        if service_exists:
            log("Обнаружена активная служба ZapretCensorliber", level="START")
            self.set_status("Невозможно остановить Zapret, пока установлена служба")
            return False
        else:
            log("Служба ZapretCensorliber не найдена, продолжаем остановку DPI.", level="START")
        
        # Проверяем, запущен ли процесс
        if not self.check_process_running():
            log("Процесс winws.exe не запущен, нет необходимости в остановке", level="START")
            self.set_status("Zapret уже остановлен")
            return True
        
        # Используем только stop.bat для остановки процесса
        stop_bat_path = os.path.join(self.bin_folder, "stop.bat")
        if os.path.exists(stop_bat_path):
            self.set_status("Останавливаю winws.exe через stop.bat...")
            log("Использую stop.bat для остановки процесса", level="START")
            
            # Создаем startupinfo для скрытия окна командной строки
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            # Запускаем stop.bat
            process = subprocess.Popen(
                stop_bat_path,
                startupinfo=startupinfo,
                cwd=self.bin_folder,
                shell=True
            )
            
            # Ждем завершения процесса с таймаутом 5 секунд
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                log("Таймаут ожидания stop.bat", level="WARNING")
                # Продолжаем выполнение, не ждем полного завершения
            
            # Даем время на завершение процессов
            time.sleep(1)
            
            # Проверяем, остановлен ли процесс
            if not self.check_process_running():
                self.set_status("Zapret успешно остановлен")
                return True
            else:
                log("Процесс winws.exe не был остановлен через stop.bat, но мы не будем использовать другие методы", level="WARNING")
                self.set_status("Zapret не удалось остановить через stop.bat")
                return False
        else:
            # Если stop.bat не найден, создаем его
            log("stop.bat не найден, создаем...", level="START")
            self.create_stop_bat()
            return self.stop_dpi()  # Рекурсивно вызываем метод после создания файла
            
        return True
    except Exception as e:
        error_msg = f"Ошибка при остановке DPI: {str(e)}"
        log(error_msg, level="ERROR")
        self.set_status(error_msg)
        return False
    

def create_stop_bat(self):
    """Создает файл stop.bat, если он не существует"""
    try:
        stop_bat_path = os.path.join(self.bin_folder, "stop.bat")
        
        # Содержимое stop.bat
        stop_bat_content = """@echo off
REM stop.bat - останавливает все экземпляры winws.exe
REM VERSION: 1.0
REM Дата обновления: 2025-04-22

echo Остановка всех процессов winws.exe...

REM Метод 1: taskkill
taskkill /F /IM winws.exe /T

REM Метод 2: через PowerShell
powershell -Command "Get-Process winws -ErrorAction SilentlyContinue | Stop-Process -Force"

REM Метод 3: через wmic
wmic process where name='winws.exe' call terminate

REM Добавляем паузу для стабильности
timeout /t 1 /nobreak >nul

echo Остановка процессов завершена.
exit /b 0
"""
        
        # Создаем директорию при необходимости
        os.makedirs(os.path.dirname(stop_bat_path), exist_ok=True)
        
        # Записываем файл
        with open(stop_bat_path, 'w', encoding='utf-8') as f:
            f.write(stop_bat_content)
            
        log(f"Файл stop.bat успешно создан: {stop_bat_path}", level="START")
        return True
    except Exception as e:
        log(f"Ошибка при создании stop.bat: {str(e)}", level="ERROR")
        return False
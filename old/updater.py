import os
import sys
import time
import shutil
import tempfile
import subprocess
from urllib.request import urlopen
import json
import threading
import tkinter as tk
from tkinter import ttk
from urls import *

class UpdaterUI:
    def __init__(self, title="Обновление Zapret"):
        self.root = tk.Tk()
        self.root.title(title)
        self.root.geometry("400x250")
        self.root.resizable(False, False)
        
        # Устанавливаем фокус на окно
        self.root.lift()
        self.root.attributes('-topmost', True)
        self.root.after_idle(self.root.attributes, '-topmost', False)
        
        # Центрируем окно на экране
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - 400) // 2
        y = (screen_height - 250) // 2
        self.root.geometry(f"400x250+{x}+{y}")
        
        # Заголовок
        header = tk.Label(self.root, text="Обновление программы", font=("Arial", 14, "bold"))
        header.pack(pady=10)
        
        # Рамка для статуса
        self.status_frame = tk.Frame(self.root)
        self.status_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Текущее действие
        self.status_label = tk.Label(self.status_frame, text="Инициализация...", font=("Arial", 10))
        self.status_label.pack(anchor=tk.W, pady=5)
        
        # Прогресс-бар
        self.progress = ttk.Progressbar(self.status_frame, orient="horizontal", length=360, mode="indeterminate")
        self.progress.pack(pady=10)
        
        # Лог обновления (последние действия)
        self.log_frame = tk.Frame(self.root)
        self.log_frame.pack(fill=tk.BOTH, expand=True, padx=20)
        
        self.log_label = tk.Label(self.log_frame, text="Лог:", font=("Arial", 9))
        self.log_label.pack(anchor=tk.W)
        
        self.log_text = tk.Text(self.log_frame, height=5, width=40, font=("Consolas", 8))
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.config(state=tk.DISABLED)
        
    def start_progress(self):
        """Запускает анимацию прогресс-бара"""
        self.progress.start(15)
    
    def stop_progress(self):
        """Останавливает анимацию прогресс-бара"""
        self.progress.stop()
    
    def set_determinate_progress(self, value=0, maximum=100):
        """Переключает прогресс-бар в режим с определенным значением"""
        self.progress.stop()
        self.progress["mode"] = "determinate"
        self.progress["maximum"] = maximum
        self.progress["value"] = value
    
    def update_progress(self, value):
        """Обновляет значение прогресс-бара"""
        self.progress["value"] = value
        self.root.update()
    
    def update_status(self, text):
        """Обновляет текст статуса"""
        self.status_label.config(text=text)
        self.root.update()
    
    def add_log(self, text):
        """Добавляет текст в лог"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, text + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.root.update()
    
    def close(self):
        """Закрывает окно"""
        self.root.destroy()

# Глобальная переменная для UI
ui = None

def log(message):
    """Выводит сообщение в консоль и записывает в лог-файл и в UI"""
    print(message)
    try:
        # Записываем в лог
        log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "updater_log.txt")
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")
    except:
        pass
    
    # Обновляем UI, если он инициализирован
    global ui
    if ui:
        ui.add_log(message)

def download_file(url, target_path):
    """Скачивает файл по URL"""
    try:
        log(f"Скачивание файла из {url}")
        if ui:
            ui.update_status("Скачивание обновления...")
            ui.start_progress()
        
        # Создаем временную директорию
        temp_dir = tempfile.mkdtemp()
        temp_file = os.path.join(temp_dir, "zapret_new.exe")
        
        # Скачиваем файл с отображением прогресса
        with urlopen(url, timeout=30) as response:
            file_size = int(response.info().get('Content-Length', -1))
            
            if file_size > 0 and ui:
                ui.set_determinate_progress(0, file_size)
                
            block_size = 8192
            downloaded = 0
            
            with open(temp_file, 'wb') as out_file:
                while True:
                    buffer = response.read(block_size)
                    if not buffer:
                        break
                    
                    out_file.write(buffer)
                    downloaded += len(buffer)
                    
                    if file_size > 0 and ui:
                        ui.update_progress(downloaded)
                        percentage = (downloaded / file_size) * 100
                        ui.update_status(f"Скачивание: {percentage:.1f}% ({downloaded} / {file_size} байт)")
        
        log(f"Файл скачан в {temp_file}")
        if ui:
            ui.update_status("Файл успешно скачан")
            ui.stop_progress()
            
        return temp_file
    except Exception as e:
        log(f"Ошибка при скачивании файла: {str(e)}")
        if ui:
            ui.update_status(f"Ошибка скачивания: {str(e)}")
            ui.stop_progress()
        return None

def update_exe_file(new_file, target_file):
    """Заменяет целевой файл новым"""
    try:
        if ui:
            ui.update_status("Обновление файлов...")
            ui.start_progress()
            
        # Создаем временное имя для оригинального файла
        target_dir = os.path.dirname(target_file)
        target_name = os.path.basename(target_file)
        backup_file = os.path.join(target_dir, f"{target_name}.old")
        
        # Ждем, пока целевой файл не будет доступен для переименования
        log("Ожидание доступа к файлу...")
        time.sleep(3)  # Даем время на завершение процесса
        
        # Сначала попытаемся сразу переименовать файл, чтобы его нельзя было запустить
        try:
            log(f"Переименование оригинального файла в {backup_file}...")
            os.rename(target_file, backup_file)
            log("Файл успешно переименован.")
        except Exception as e:
            log(f"Не удалось переименовать файл: {str(e)}")
            # Если не получилось переименовать, проверим доступность файла
            if not os.path.exists(target_file):
                log("Целевой файл не найден!")
                if ui:
                    ui.update_status("Ошибка: Целевой файл не найден")
                    ui.stop_progress()
                return False
            
            # Пробуем удалить файл напрямую
            try:
                os.remove(target_file)
                log("Оригинальный файл удален.")
            except Exception as e2:
                log(f"Не удалось удалить оригинальный файл: {str(e2)}")
                if ui:
                    ui.update_status("Ошибка доступа к файлу")
                    ui.stop_progress()
                return False
        
        # Копируем новый файл на место оригинального
        log(f"Копирование {new_file} на место {target_file}...")
        if ui:
            ui.update_status("Копирование новых файлов...")
        shutil.copy2(new_file, target_file)
        
        # Проверяем успешность копирования
        if os.path.exists(target_file):
            log("Новый файл успешно скопирован.")
        else:
            log("Не удалось скопировать новый файл!")
            # Пытаемся восстановить оригинал, если он был переименован
            if os.path.exists(backup_file):
                os.rename(backup_file, target_file)
            if ui:
                ui.update_status("Ошибка копирования файлов")
                ui.stop_progress()
            return False
        
        # Удаляем резервную копию, если она была создана
        if os.path.exists(backup_file):
            try:
                os.remove(backup_file)
                log("Резервная копия удалена.")
            except Exception as e:
                log(f"Не удалось удалить резервную копию: {str(e)}")
        
        # Удаляем временные файлы
        log("Очистка временных файлов...")
        if ui:
            ui.update_status("Очистка временных файлов...")
        try:
            shutil.rmtree(os.path.dirname(new_file), ignore_errors=True)
            log("Временные файлы удалены.")
        except Exception as e:
            log(f"Ошибка при удалении временных файлов: {str(e)}")
        
        # Запускаем обновленное приложение
        log("Запуск обновленной программы...")
        if ui:
            ui.update_status("Запуск обновленной программы...")
            ui.stop_progress()
        subprocess.Popen([target_file])
        
        log("Обновление успешно завершено!")
        if ui:
            ui.update_status("Обновление успешно завершено!")
            # Закрываем UI через 3 секунды
            ui.root.after(3000, ui.close)
        
        return True
    except Exception as e:
        log(f"Общая ошибка при обновлении: {str(e)}")
        if ui:
            ui.update_status(f"Ошибка: {str(e)}")
            ui.stop_progress()
        return False

def main():
    global ui
    
    try:
        # Инициализируем UI
        ui = UpdaterUI("Обновление Zapret")
        
        # Запускаем UI в отдельном потоке
        ui_thread = threading.Thread(target=ui.root.mainloop)
        ui_thread.daemon = True
        ui_thread.start()
        
        # Проверяем аргументы командной строки
        if len(sys.argv) < 2:
            log("Использование: updater.exe <путь_к_обновляемому_файлу> [новая_версия]")
            ui.update_status("Ошибка: Недостаточно аргументов")
            input("Нажмите Enter для выхода...")
            return 1
        
        # Получаем путь к обновляемому файлу
        target_file = sys.argv[1]
        log(f"Путь к обновляемому файлу: {target_file}")
        ui.update_status("Инициализация обновления...")
        
        # URL для скачивания обновления
        download_url = EXE_UPDATE_URL
        
        # Скачиваем новую версию
        new_file = download_file(download_url, target_file)
        if not new_file:
            log("Не удалось скачать обновление.")
            ui.update_status("Ошибка скачивания обновления")
            input("Нажмите Enter для выхода...")
            return 1
        
        # Обновляем файл
        if update_exe_file(new_file, target_file):
            # Ждем, пока UI закроется
            ui_thread.join(5)
            return 0
        else:
            ui.update_status("Обновление не удалось")
            input("Нажмите Enter для выхода...")
            return 1
            
    except Exception as e:
        log(f"Необработанная ошибка: {str(e)}")
        if ui:
            ui.update_status(f"Критическая ошибка: {str(e)}")
            ui.stop_progress()
        input("Нажмите Enter для выхода...")
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"Критическая ошибка: {str(e)}")
        input("Нажмите Enter для выхода...")
        sys.exit(1)
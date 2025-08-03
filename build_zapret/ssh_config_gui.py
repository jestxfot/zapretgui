"""
build_tools/ssh_config_gui.py - GUI для настройки SSH
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
import json
import threading

try:
    from ssh_deploy import (
        load_ssh_config, save_ssh_config, test_ssh_connection,
        ensure_paramiko
    )
except ImportError:
    # Если запускаем из другой папки
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from ssh_deploy import (
        load_ssh_config, save_ssh_config, test_ssh_connection,
        ensure_paramiko
    )

class SSHConfigDialog:
    def __init__(self, parent=None):
        self.result = None
        
        # Создаем окно
        self.window = tk.Toplevel(parent) if parent else tk.Tk()
        self.window.title("Настройка SSH деплоя")
        self.window.geometry("500x550")
        self.window.resizable(False, False)
        
        # Загружаем текущую конфигурацию
        self.config = load_ssh_config()
        
        # Переменные
        self.host_var = tk.StringVar(value=self.config.get('host', ''))
        self.port_var = tk.StringVar(value=str(self.config.get('port', 22)))
        self.username_var = tk.StringVar(value=self.config.get('username', 'root'))
        self.password_var = tk.StringVar(value=self.config.get('password', ''))
        self.key_path_var = tk.StringVar(value=self.config.get('key_path', ''))
        self.remote_path_var = tk.StringVar(value=self.config.get('remote_path', '/root/zapretgpt'))
        self.use_key_var = tk.BooleanVar(value=bool(self.config.get('key_path')))
        
        self.create_widgets()
        
        # Центрируем окно
        self.center_window()
        
    def create_widgets(self):
        """Создание интерфейса"""
        # Основной контейнер
        main_frame = ttk.Frame(self.window, padding=20)
        main_frame.pack(fill='both', expand=True)
        
        # Заголовок
        title_label = ttk.Label(main_frame, text="Настройка SSH подключения к VPS",
                               font=('Segoe UI', 12, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # Поля ввода
        fields_frame = ttk.Frame(main_frame)
        fields_frame.pack(fill='x', pady=(0, 20))
        
        # Host
        ttk.Label(fields_frame, text="Хост:", width=15).grid(row=0, column=0, sticky='w', pady=5)
        host_entry = ttk.Entry(fields_frame, textvariable=self.host_var, width=30)
        host_entry.grid(row=0, column=1, sticky='ew', pady=5)
        
        # Port
        ttk.Label(fields_frame, text="Порт:", width=15).grid(row=1, column=0, sticky='w', pady=5)
        port_entry = ttk.Entry(fields_frame, textvariable=self.port_var, width=30)
        port_entry.grid(row=1, column=1, sticky='ew', pady=5)
        
        # Username
        ttk.Label(fields_frame, text="Пользователь:", width=15).grid(row=2, column=0, sticky='w', pady=5)
        username_entry = ttk.Entry(fields_frame, textvariable=self.username_var, width=30)
        username_entry.grid(row=2, column=1, sticky='ew', pady=5)
        
        # Выбор метода аутентификации
        auth_frame = ttk.LabelFrame(main_frame, text="Метод аутентификации", padding=10)
        auth_frame.pack(fill='x', pady=(0, 20))
        
        # Радиокнопки
        password_radio = ttk.Radiobutton(auth_frame, text="Пароль", 
                                        variable=self.use_key_var, value=False,
                                        command=self.on_auth_method_change)
        password_radio.pack(anchor='w')
        
        # Поле пароля
        self.password_frame = ttk.Frame(auth_frame)
        self.password_frame.pack(fill='x', padx=(20, 0), pady=5)
        
        ttk.Label(self.password_frame, text="Пароль:", width=12).pack(side='left')
        self.password_entry = ttk.Entry(self.password_frame, textvariable=self.password_var, 
                                       show='*', width=25)
        self.password_entry.pack(side='left', padx=(5, 0))
        
        key_radio = ttk.Radiobutton(auth_frame, text="SSH ключ", 
                                   variable=self.use_key_var, value=True,
                                   command=self.on_auth_method_change)
        key_radio.pack(anchor='w', pady=(10, 0))
        
        # Поле ключа
        self.key_frame = ttk.Frame(auth_frame)
        self.key_frame.pack(fill='x', padx=(20, 0), pady=5)
        
        ttk.Label(self.key_frame, text="Путь к ключу:", width=12).pack(side='left')
        self.key_entry = ttk.Entry(self.key_frame, textvariable=self.key_path_var, width=20)
        self.key_entry.pack(side='left', padx=(5, 0))
        
        browse_button = ttk.Button(self.key_frame, text="Обзор", 
                                  command=self.browse_key)
        browse_button.pack(side='left', padx=(5, 0))
        
        # Remote path
        remote_frame = ttk.LabelFrame(main_frame, text="Путь на сервере", padding=10)
        remote_frame.pack(fill='x', pady=(0, 20))
        
        ttk.Label(remote_frame, text="Директория:").pack(side='left')
        remote_entry = ttk.Entry(remote_frame, textvariable=self.remote_path_var, width=30)
        remote_entry.pack(side='left', padx=(10, 0))
        
        # Кнопки
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill='x')
        
        test_button = ttk.Button(button_frame, text="Тест подключения", 
                                command=self.test_connection)
        test_button.pack(side='left')
        
        save_button = ttk.Button(button_frame, text="Сохранить", 
                                command=self.save_config)
        save_button.pack(side='right', padx=(10, 0))
        
        cancel_button = ttk.Button(button_frame, text="Отмена", 
                                  command=self.window.destroy)
        cancel_button.pack(side='right')
        
        # Применяем начальное состояние
        self.on_auth_method_change()
        
    def on_auth_method_change(self):
        """При изменении метода аутентификации"""
        if self.use_key_var.get():
            # SSH ключ
            for widget in self.password_frame.winfo_children():
                widget.configure(state='disabled')
            for widget in self.key_frame.winfo_children():
                widget.configure(state='normal')
        else:
            # Пароль
            for widget in self.password_frame.winfo_children():
                widget.configure(state='normal')
            for widget in self.key_frame.winfo_children():
                widget.configure(state='disabled')
                
    def browse_key(self):
        """Выбор SSH ключа"""
        filename = filedialog.askopenfilename(
            title="Выберите SSH ключ",
            initialdir=Path.home() / ".ssh",
            filetypes=[("Все файлы", "*.*")]
        )
        if filename:
            self.key_path_var.set(filename)
            
    def test_connection(self):
        """Тест SSH подключения"""
        # Проверяем paramiko
        if not ensure_paramiko():
            messagebox.showerror("Ошибка", 
                               "Не удалось установить paramiko.\n"
                               "Установите вручную: pip install paramiko")
            return
        
        # Валидация
        if not self.host_var.get():
            messagebox.showerror("Ошибка", "Укажите хост!")
            return
            
        try:
            port = int(self.port_var.get())
        except:
            messagebox.showerror("Ошибка", "Неверный порт!")
            return
            
        if not self.username_var.get():
            messagebox.showerror("Ошибка", "Укажите имя пользователя!")
            return
            
        # Показываем прогресс
        progress = tk.Toplevel(self.window)
        progress.title("Тестирование подключения")
        progress.geometry("300x100")
        progress.resizable(False, False)
        
        ttk.Label(progress, text="Подключение к серверу...", 
                 font=('Segoe UI', 10)).pack(pady=20)
        
        progress_bar = ttk.Progressbar(progress, mode='indeterminate')
        progress_bar.pack(padx=20, fill='x')
        progress_bar.start(10)
        
        # Центрируем окно прогресса
        progress.update_idletasks()
        x = (progress.winfo_screenwidth() - progress.winfo_width()) // 2
        y = (progress.winfo_screenheight() - progress.winfo_height()) // 2
        progress.geometry(f"+{x}+{y}")
        
        # Запускаем тест в отдельном потоке
        def test():
            password = self.password_var.get() if not self.use_key_var.get() else None
            key_path = self.key_path_var.get() if self.use_key_var.get() else None
            
            success, message = test_ssh_connection(
                self.host_var.get(),
                port,
                self.username_var.get(),
                password,
                key_path
            )
            
            # Закрываем прогресс и показываем результат
            progress.destroy()
            
            if success:
                messagebox.showinfo("Успех", message)
            else:
                messagebox.showerror("Ошибка", message)
                
        threading.Thread(target=test, daemon=True).start()
        
    def save_config(self):
        """Сохранение конфигурации"""
        # Валидация
        if not self.host_var.get():
            messagebox.showerror("Ошибка", "Укажите хост!")
            return
            
        try:
            port = int(self.port_var.get())
        except:
            messagebox.showerror("Ошибка", "Неверный порт!")
            return
            
        if not self.username_var.get():
            messagebox.showerror("Ошибка", "Укажите имя пользователя!")
            return
            
        # Формируем конфигурацию
        config = {
            'host': self.host_var.get(),
            'port': port,
            'username': self.username_var.get(),
            'remote_path': self.remote_path_var.get() or '/root/zapretgpt'
        }
        
        if self.use_key_var.get():
            if not self.key_path_var.get():
                messagebox.showerror("Ошибка", "Укажите путь к SSH ключу!")
                return
            config['key_path'] = self.key_path_var.get()
        else:
            if not self.password_var.get():
                messagebox.showerror("Ошибка", "Укажите пароль!")
                return
            config['password'] = self.password_var.get()
            
        # Сохраняем
        save_ssh_config(config)
        self.result = config
        
        messagebox.showinfo("Успех", "Конфигурация сохранена!")
        self.window.destroy()
        
    def center_window(self):
        """Центрирование окна"""
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() - self.window.winfo_width()) // 2
        y = (self.window.winfo_screenheight() - self.window.winfo_height()) // 2
        self.window.geometry(f"+{x}+{y}")
        
    def show(self):
        """Показать диалог и дождаться закрытия"""
        self.window.grab_set()
        self.window.wait_window()
        return self.result


if __name__ == "__main__":
    # Тест диалога
    dialog = SSHConfigDialog()
    result = dialog.show()
    print("Результат:", result)
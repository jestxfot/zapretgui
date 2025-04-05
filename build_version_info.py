import os
from config import APP_VERSION

# Разбиваем версию на компоненты
version_parts = APP_VERSION.split('.')
# Добавляем нули, если нужно, чтобы было 4 компонента
while len(version_parts) < 4:
    version_parts.append('0')
# Преобразуем в кортеж целых чисел
version_tuple = tuple(map(int, version_parts))

# Создаем содержимое файла version_info.txt
version_info = f'''# UTF-8
#
# For more details about fixed file info 'ffi' see:
# http://msdn.microsoft.com/en-us/library/ms646997.aspx
VSVersionInfo(
  ffi=FixedFileInfo(
    # filevers и prodvers должны быть всегда кортежами из 4 чисел: (1, 2, 3, 4)
    filevers={version_tuple},
    prodvers={version_tuple},
    # Contains a bitmask that specifies the valid bits 'flags'r
    mask=0x3f,
    # Contains a bitmask that specifies the Boolean attributes of the file.
    flags=0x0,
    # The operating system for which this file was designed.
    # 0x4 - NT и может содержать информацию, определенную в VarFileInfo
    OS=0x40004,
    # The general type of file.
    # 0x1 - приложение
    fileType=0x1,
    # The function of the file.
    # 0x0 - функция не определена
    subtype=0x0,
    # Creation date and time stamp.
    date=(0, 0)
    ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u't.me/bypassblock'),
        StringStruct(u'FileDescription', u'Zapret GUI'),
        StringStruct(u'FileVersion', u'{APP_VERSION}'),
        StringStruct(u'InternalName', u'zapret'),
        StringStruct(u'LegalCopyright', u'Copyright © 2025 t.me/bypassblock'),
        StringStruct(u'OriginalFilename', u'zapret.exe'),
        StringStruct(u'ProductName', u'Zapret'),
        StringStruct(u'ProductVersion', u'{APP_VERSION}')])
      ]), 
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
'''

# Записываем файл version_info.txt
with open('version_info.txt', 'w', encoding='utf-8') as f:
    f.write(version_info)

print(f"Файл version_info.txt создан с версией {APP_VERSION}")
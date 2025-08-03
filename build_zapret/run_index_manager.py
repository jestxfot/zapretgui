# build_zapret/run_index_manager.py
"""
Скрипт запуска менеджера index.json
"""

import sys
import os

# Добавляем текущую директорию в путь для импорта
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from index_json_manager import main

if __name__ == "__main__":
    main()
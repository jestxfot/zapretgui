Отлично, структура на сервере уже есть.

Сделай на сервере 3 шага (один раз), чтобы автопубликация из билдера заработала:

1) Создай venv именно `.venv` (у тебя сейчас `venvv`, а код ищет `/root/publisher/.venv/bin/python3`)
```bash
cd /root/publisher
apt update
apt install python3.13-venv
apt install -y build-essential python3.13-dev
pip install -U pip setuptools wheel
python3 -m venv .venv
. .venv/bin/activate
pip install -U pip
pip install pyrogram tgcrypto pysocks
```

2) Создай `/root/publisher/.env`:
```bash
nano /root/publisher/.env
chmod 600 /root/publisher/.env
```
и добавь:
```ini
TELEGRAM_API_ID=...
TELEGRAM_API_HASH=...
```

3) Создай Pyrogram-сессию (ввод телефона/кода):
```bash
set -a
. ./.env
set +a

python3 -c "import os; print(os.getenv('TELEGRAM_API_ID'), os.getenv('TELEGRAM_API_HASH'))"
python3 telegram_auth_pyrogram.py


cd /root/publisher
set -a && . /root/publisher/.env && set +a
/root/publisher/.venv/bin/python3 telegram_auth_pyrogram.py
```

После этого на ПК в `.env`:
```ini
ZAPRET_TG_SSH_HOST=185.71.196.92
ZAPRET_TG_SSH_PORT=10222
ZAPRET_TG_SSH_USER=root
ZAPRET_TG_SSH_SCRIPTS_DIR=/root/publisher
```

и билдер будет заливать exe и публиковать автоматически.
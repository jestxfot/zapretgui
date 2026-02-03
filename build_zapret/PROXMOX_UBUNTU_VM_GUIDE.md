# Proxmox + Ubuntu Desktop VM (Secure Publisher)

This guide sets up a reasonably hardened Ubuntu Desktop VM in Proxmox and prepares it to publish builds to Telegram from the VM.

Notes:
- This improves isolation and security, but it does NOT make network activity “invisible” to an ISP/provider.
- Prefer a dedicated VM (publisher-only), minimal installed apps, and least-privilege access.

## 0) Prereqs

- Proxmox VE host updated.
- Ubuntu Desktop ISO uploaded to Proxmox (`local -> ISO Images`).
- Decide network access model:
  - Recommended: VM accessible only from your LAN/VPN IPs; no public SSH.

## 1) Create VM in Proxmox

1. Upload ISO
- Download `ubuntu-24.04-desktop-amd64.iso`.
- Proxmox: `local (pve) -> ISO Images -> Upload`.

2. Create VM
- General:
  - Name: `publisher-ubuntu-desktop`
- OS:
  - Use ISO: `ubuntu-24.04-desktop-amd64.iso`
  - Type: Linux, Version: Ubuntu
- System:
  - Machine: `q35`
  - BIOS: `OVMF (UEFI)`
  - EFI Disk: enabled
  - TPM (optional): TPM 2.0
- Disks:
  - Bus/Device: `VirtIO SCSI`
  - SCSI Controller: `VirtIO SCSI single`
  - Size: 60GB+ (depending on artifact storage)
  - Options: enable `Discard`, enable `SSD emulation`, enable `IO thread`
- CPU:
  - Type: `host`
  - Cores: 2-4
- Memory:
  - 4-8GB
- Network:
  - Model: `VirtIO (paravirtualized)`
  - Bridge: `vmbr0`

3. VM Options
- Enable `QEMU Guest Agent` (after installing it inside the VM).
- Set Boot order to boot from ISO first, then disk.

## 2) Install Ubuntu Desktop (with disk encryption)

During Ubuntu install:
- Choose “Erase disk and install Ubuntu”.
- Enable “Encrypt the new Ubuntu installation for security” (LUKS).
- Choose a strong encryption passphrase.

After install:
- Remove ISO from VM (Proxmox -> Hardware -> CD/DVD -> Do not use any media).
- Reboot VM.

## 3) Post-install hardening (inside VM)

Open a terminal in Ubuntu.

1) Update system
```bash
sudo apt update && sudo apt -y upgrade
sudo reboot
```

2) Install QEMU guest agent
```bash
sudo apt -y install qemu-guest-agent
sudo systemctl enable --now qemu-guest-agent
```

3) Create a dedicated user
If you installed with a personal user, keep it for desktop use and create a dedicated publisher account:
```bash
sudo adduser publisher
sudo usermod -aG sudo publisher
```

4) SSH server (keys only)
```bash
sudo apt -y install openssh-server
sudo systemctl enable --now ssh
```

On your PC generate a key if needed:
```bash
ssh-keygen -t ed25519 -C "publisher"
```

Copy key to VM:
```bash
ssh-copy-id publisher@<vm_ip>
```

Harden SSH:
```bash
sudo nano /etc/ssh/sshd_config
```

Set/ensure:
- `PermitRootLogin no`
- `PasswordAuthentication no`
- `KbdInteractiveAuthentication no`
- `PubkeyAuthentication yes`

Restart:
```bash
sudo systemctl restart ssh
```

5) Firewall (UFW)
```bash
sudo apt -y install ufw
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow OpenSSH
sudo ufw enable
sudo ufw status verbose
```

If VM is LAN-only, also restrict OpenSSH to your LAN subnet:
```bash
sudo ufw delete allow OpenSSH
sudo ufw allow from <your_lan_cidr> to any port 22 proto tcp
```

6) Fail2ban
```bash
sudo apt -y install fail2ban
sudo systemctl enable --now fail2ban
```

7) Automatic security updates
```bash
sudo apt -y install unattended-upgrades
sudo dpkg-reconfigure unattended-upgrades
```

## 4) Proxmox host-side safety checklist

- Limit Proxmox Web UI to trusted IPs (firewall).
- Use strong passwords + 2FA.
- Do not expose SSH/Web UI publicly.
- Use snapshots before major changes.
- Backups: encrypted backups if possible, stored off-host.

## 5) Telegram publishing stack (Pyrogram) on the VM

Goal: VM has the Telegram session and sends files to the channel.

1) Install Python tooling
```bash
sudo apt -y install python3-venv python3-pip
```

2) Create venv under publisher user
```bash
su - publisher
mkdir -p ~/publisher
cd ~/publisher
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install pyrogram tgcrypto pysocks
```

3) Put uploader scripts on VM

Option A (recommended): copy only the needed scripts to VM
- From your PC copy:
  - `build_zapret/telegram_auth_pyrogram.py`
  - `build_zapret/telegram_uploader_pyrogram.py`

Example:
```bash
scp build_zapret/telegram_auth_pyrogram.py publisher@<vm_ip>:~/publisher/
scp build_zapret/telegram_uploader_pyrogram.py publisher@<vm_ip>:~/publisher/
```

Option B: clone the repo on VM
- Only if you want full toolchain on VM.

4) Configure secrets via env (do NOT commit)

Create `~/publisher/.env` on VM:
```bash
nano ~/publisher/.env
chmod 600 ~/publisher/.env
```

Put values:
- `TELEGRAM_API_ID=...`
- `TELEGRAM_API_HASH=...`

Optional proxy settings (if you need them on VM):
- `ZAPRET_PROXY_SCHEME=socks5`
- `ZAPRET_PROXY_HOST=...`
- `ZAPRET_PROXY_PORT=...`
- `ZAPRET_PROXY_USER=...`
- `ZAPRET_PROXY_PASS=...`
- `ZAPRET_PROXY_FORCE_SOCKS=1` (optional)

Load env in shell:
```bash
set -a
source ~/publisher/.env
set +a
```

5) Authorize Pyrogram session (one-time)
```bash
cd ~/publisher
source .venv/bin/activate
set -a && source .env && set +a
python3 telegram_auth_pyrogram.py
```

6) Test publish
Create inbox and upload a file from PC:
```bash
ssh publisher@<vm_ip> "mkdir -p ~/publisher/inbox"
scp Zapret2Setup_TEST.exe publisher@<vm_ip>:~/publisher/inbox/
```

Publish:
```bash
ssh publisher@<vm_ip> "cd ~/publisher && source .venv/bin/activate && set -a && source .env && set +a && python3 telegram_uploader_pyrogram.py ~/publisher/inbox/Zapret2Setup_TEST.exe test 1.2.3.4 'Release notes...'"
```

## 6) Make it convenient: publish over SSH command

On your PC you can wrap it in a script that:
1) scp installer to VM
2) ssh into VM and run the uploader

Keep session files on VM only.

## 7) Operational tips

- Snapshots: take a snapshot before changing Telegram auth or Python deps.
- Separate VM from web browsing: keep it “publisher-only”.
- Logs: store logs on VM, rotate them.

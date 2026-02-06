#!/usr/bin/env bash
set -euo pipefail

# setup_zapret_nginx.sh
# Idempotent Nginx setup for Zapret update server (HTTP 887 / HTTPS 888).
#
# Usage (on VPS as root):
#   curl -fsSL <URL> -o setup_zapret_nginx.sh
#   chmod +x setup_zapret_nginx.sh
#   sudo ./setup_zapret_nginx.sh
#
# Optional env overrides:
#   HTTP_PORT=887 HTTPS_PORT=888 SITE_NAME=zapret \
#   WEB_ROOT=/var/www/zapret CERT_DIR=/root/zapretgpt/certs \
#   ENABLE_UFW=0 ENABLE_SELF_SIGNED_CERT=1 \
#   API_CACHE_SECONDS=60 DOWNLOAD_CACHE_SECONDS=3600 \
#   API_RATE="120r/m" API_BURST=30 DOWNLOAD_RATE="30r/m" DOWNLOAD_BURST=10 HEALTH_RATE="60r/m" HEALTH_BURST=10 \
#   DOWNLOAD_CONN_PER_IP=2 DOWNLOAD_CONN_GLOBAL=40 DOWNLOAD_RATE_AFTER=10m DOWNLOAD_LIMIT_RATE=2m \
#   ACCESS_LOG_API=0 \
#   ./setup_zapret_nginx.sh

require_root() {
  if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
    echo "ERROR: run as root (use sudo)." >&2
    exit 1
  fi
}

ts() { date +"%Y%m%d_%H%M%S"; }

backup_file() {
  local path="$1"
  if [[ -f "$path" ]]; then
    cp -a "$path" "${path}.bak.$(ts)"
  fi
}

write_file() {
  local path="$1"
  local tmp
  tmp="$(mktemp)"
  cat >"$tmp"
  backup_file "$path"
  install -m 0644 "$tmp" "$path"
  rm -f "$tmp"
}

main() {
  require_root

  local http_port="${HTTP_PORT:-887}"
  local https_port="${HTTPS_PORT:-888}"
  local site_name="${SITE_NAME:-zapret}"
  local web_root="${WEB_ROOT:-/var/www/zapret}"
  local cert_dir="${CERT_DIR:-/root/zapretgpt/certs}"

  local enable_ufw="${ENABLE_UFW:-0}"
  local enable_self_signed="${ENABLE_SELF_SIGNED_CERT:-1}"

  local api_cache_seconds="${API_CACHE_SECONDS:-60}"
  local download_cache_seconds="${DOWNLOAD_CACHE_SECONDS:-3600}"

  # Defaults tuned for many users behind NAT + weak servers:
  # - API: higher rate but cached responses
  # - Download: protected mostly by conn+rate limits
  local api_rate="${API_RATE:-120r/m}"
  local api_burst="${API_BURST:-30}"
  local download_rate="${DOWNLOAD_RATE:-30r/m}"
  local download_burst="${DOWNLOAD_BURST:-10}"
  local health_rate="${HEALTH_RATE:-60r/m}"
  local health_burst="${HEALTH_BURST:-10}"

  local download_conn_per_ip="${DOWNLOAD_CONN_PER_IP:-2}"
  local download_conn_global="${DOWNLOAD_CONN_GLOBAL:-40}"
  local download_rate_after="${DOWNLOAD_RATE_AFTER:-10m}"
  local download_limit_rate="${DOWNLOAD_LIMIT_RATE:-2m}"

  local access_log_api="${ACCESS_LOG_API:-0}"

  echo "[1/7] Installing packages..."
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -y
  apt-get install -y nginx openssl curl

  echo "[2/7] Creating directories..."
  mkdir -p "${web_root}/api" "${web_root}/download"
  mkdir -p /var/log/nginx

  # Ensure minimal health.json exists (idempotent).
  if [[ ! -f "${web_root}/api/health.json" ]]; then
    echo '{"status":"ok"}' > "${web_root}/api/health.json"
  fi

  echo "[3/7] Creating rate-limit zones..."
  write_file "/etc/nginx/conf.d/${site_name}-limits.conf" <<EOF
# ${site_name} - rate limiting zones (generated)
limit_req_zone \$binary_remote_addr zone=${site_name}_api:10m rate=${api_rate};
limit_req_zone \$binary_remote_addr zone=${site_name}_download:10m rate=${download_rate};
limit_req_zone \$binary_remote_addr zone=${site_name}_health:1m rate=${health_rate};

# Connection limiting zones (downloads)
limit_conn_zone \$binary_remote_addr zone=${site_name}_dl_ip:10m;
limit_conn_zone \$server_name zone=${site_name}_dl_global:1m;
EOF

  echo "[4/7] Creating shared location snippet..."
  # Common security headers.
  local cache_api_header="public, max-age=${api_cache_seconds}"
  local cache_download_header="public, max-age=${download_cache_seconds}"

  # optional: disable access_log on API endpoints to reduce IO.
  local api_access_log_directive=""
  if [[ "${access_log_api}" == "1" ]]; then
    api_access_log_directive=""
  else
    api_access_log_directive="access_log off;"
  fi

  write_file "/etc/nginx/snippets/${site_name}_locations.conf" <<EOF
# ${site_name} - shared locations (generated)

# API HEALTH CHECK
location = /api/health {
    limit_req zone=${site_name}_health burst=${health_burst};
    ${api_access_log_directive}

    default_type application/json;
    alias ${web_root}/api/health.json;

    add_header Access-Control-Allow-Origin "*" always;
    add_header Cache-Control "no-cache" always;
    etag on;
}

# API VERSIONS (all versions)
location = /api/versions {
    limit_req zone=${site_name}_api burst=${api_burst};
    ${api_access_log_directive}

    default_type application/json;
    alias ${web_root}/api/all_versions.json;

    add_header Access-Control-Allow-Origin "*" always;
    add_header Cache-Control "${cache_api_header}" always;
    expires ${api_cache_seconds}s;
    etag on;
}

location = /api/all_versions.json {
    limit_req zone=${site_name}_api burst=${api_burst};
    ${api_access_log_directive}

    default_type application/json;
    alias ${web_root}/api/all_versions.json;

    add_header Access-Control-Allow-Origin "*" always;
    add_header Cache-Control "${cache_api_header}" always;
    expires ${api_cache_seconds}s;
    etag on;
}

# API VERSION/STABLE (static JSON)
location = /api/version/stable {
    limit_req zone=${site_name}_api burst=${api_burst};
    ${api_access_log_directive}

    default_type application/json;
    alias ${web_root}/api/version_stable.json;

    add_header Access-Control-Allow-Origin "*" always;
    add_header Cache-Control "${cache_api_header}" always;
    expires ${api_cache_seconds}s;
    etag on;
}

# API VERSION/TEST (static JSON)
location = /api/version/test {
    limit_req zone=${site_name}_api burst=${api_burst};
    ${api_access_log_directive}

    default_type application/json;
    alias ${web_root}/api/version_test.json;

    add_header Access-Control-Allow-Origin "*" always;
    add_header Cache-Control "${cache_api_header}" always;
    expires ${api_cache_seconds}s;
    etag on;
}

# DOWNLOADS (aliases)
location = /download/stable {
    limit_req zone=${site_name}_download burst=${download_burst};
    limit_conn ${site_name}_dl_ip ${download_conn_per_ip};
    limit_conn ${site_name}_dl_global ${download_conn_global};
    limit_rate_after ${download_rate_after};
    limit_rate ${download_limit_rate};

    alias ${web_root}/download/ZapretSetup.exe;

    add_header Content-Disposition 'attachment; filename="ZapretSetup.exe"' always;
    add_header Content-Type "application/vnd.microsoft.portable-executable" always;
    add_header Accept-Ranges "bytes" always;
    add_header Access-Control-Allow-Origin "*" always;
    add_header Cache-Control "${cache_download_header}" always;

    etag on;
    access_log /var/log/nginx/${site_name}_downloads.log main;
}

location = /download/test {
    limit_req zone=${site_name}_download burst=${download_burst};
    limit_conn ${site_name}_dl_ip ${download_conn_per_ip};
    limit_conn ${site_name}_dl_global ${download_conn_global};
    limit_rate_after ${download_rate_after};
    limit_rate ${download_limit_rate};

    alias ${web_root}/download/ZapretSetup_TEST.exe;

    add_header Content-Disposition 'attachment; filename="ZapretSetup_TEST.exe"' always;
    add_header Content-Type "application/vnd.microsoft.portable-executable" always;
    add_header Accept-Ranges "bytes" always;
    add_header Access-Control-Allow-Origin "*" always;
    add_header Cache-Control "${cache_download_header}" always;

    etag on;
    access_log /var/log/nginx/${site_name}_downloads.log main;
}

location ~ ^/download/ZapretSetup(_TEST)?\\.exe\$ {
    limit_req zone=${site_name}_download burst=${download_burst};
    limit_conn ${site_name}_dl_ip ${download_conn_per_ip};
    limit_conn ${site_name}_dl_global ${download_conn_global};
    limit_rate_after ${download_rate_after};
    limit_rate ${download_limit_rate};

    add_header Content-Disposition 'attachment' always;
    add_header Content-Type "application/vnd.microsoft.portable-executable" always;
    add_header Accept-Ranges "bytes" always;
    add_header Access-Control-Allow-Origin "*" always;
    add_header Cache-Control "${cache_download_header}" always;

    etag on;
    access_log /var/log/nginx/${site_name}_downloads.log main;
}

# MAIN PAGE
location = / {
    try_files /index.html =404;
    add_header Cache-Control "public, max-age=300" always;
    etag on;
}

# SECURITY: block dotfiles and editor backups
location ~ /\\. {
    deny all;
    access_log off;
    log_not_found off;
}
location ~ ~\$ {
    deny all;
    access_log off;
    log_not_found off;
}
EOF

  echo "[5/7] Creating nginx site config..."
  write_file "/etc/nginx/sites-available/${site_name}" <<EOF
# ${site_name} update server - nginx config (generated)

log_format main '\$remote_addr - \$remote_user [\$time_local] "\$request" '
                '\$status \$body_bytes_sent "\$http_referer" '
                '"\$http_user_agent" "\$http_x_forwarded_for"';

server {
    listen ${http_port} default_server;
    server_name _;

    root ${web_root};
    disable_symlinks off;

    access_log /var/log/nginx/${site_name}_access.log main;
    error_log /var/log/nginx/${site_name}_error.log warn;

    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;

    include /etc/nginx/snippets/${site_name}_locations.conf;
}

server {
    listen ${https_port} ssl default_server;
    server_name _;

    #http2 on;

    ssl_certificate ${cert_dir}/server.crt;
    ssl_certificate_key ${cert_dir}/server.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    root ${web_root};
    disable_symlinks off;

    access_log /var/log/nginx/${site_name}_access.log main;
    error_log /var/log/nginx/${site_name}_error.log warn;

    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;

    include /etc/nginx/snippets/${site_name}_locations.conf;
}
EOF

  echo "[6/7] Ensuring SSL certificate..."
  mkdir -p "${cert_dir}"
  chmod 700 "${cert_dir}"

  if [[ "${enable_self_signed}" == "1" ]]; then
    if [[ ! -f "${cert_dir}/server.crt" || ! -f "${cert_dir}/server.key" ]]; then
      openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
        -keyout "${cert_dir}/server.key" \
        -out "${cert_dir}/server.crt" \
        -subj "/C=RU/ST=Moscow/L=Moscow/O=Zapret/CN=localhost"
      chmod 600 "${cert_dir}/server.key"
      chmod 644 "${cert_dir}/server.crt"
    fi
  else
    if [[ ! -f "${cert_dir}/server.crt" || ! -f "${cert_dir}/server.key" ]]; then
      echo "ERROR: SSL files missing in ${cert_dir} and ENABLE_SELF_SIGNED_CERT=0" >&2
      exit 1
    fi
  fi

  echo "[7/7] Enabling site and restarting nginx..."
  rm -f /etc/nginx/sites-enabled/default || true
  ln -sf "/etc/nginx/sites-available/${site_name}" "/etc/nginx/sites-enabled/${site_name}"

  nginx -t
  systemctl enable nginx
  systemctl restart nginx

  if [[ "${enable_ufw}" == "1" ]]; then
    apt-get install -y ufw
    ufw allow 22/tcp || true
    ufw allow "${http_port}/tcp" comment 'Zapret HTTP API' || true
    ufw allow "${https_port}/tcp" comment 'Zapret HTTPS API' || true
    ufw --force enable || true
  fi

  echo "OK: nginx configured."
  echo "Endpoints:"
  local ip
  ip="$(curl -fsS ifconfig.me 2>/dev/null || echo "<server-ip>")"
  echo "  http://${ip}:${http_port}/api/health"
  echo "  http://${ip}:${http_port}/api/versions"
  echo "  http://${ip}:${http_port}/download/stable"
  echo "  https://${ip}:${https_port}/api/health (self-signed)"
}

main "$@"

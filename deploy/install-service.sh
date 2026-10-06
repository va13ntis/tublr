#!/usr/bin/env bash
# Installs Tublr as a systemd service running from this checkout.
# Usage: sudo deploy/install-service.sh [user]
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
    echo "Run as root: sudo $0 [user]" >&2
    exit 1
fi

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_USER="${1:-${SUDO_USER:-$(stat -c %U "$APP_DIR")}}"
RUN_GROUP="$(id -gn "$RUN_USER")"
ENV_FILE=/etc/tublr/tublr.env
UNIT_FILE=/etc/systemd/system/tublr.service

if [[ ! -x "$APP_DIR/.venv/bin/uvicorn" ]]; then
    echo "Missing $APP_DIR/.venv/bin/uvicorn. Create the venv and run: pip install -r requirements.txt" >&2
    exit 1
fi

mkdir -p /etc/tublr
if [[ ! -f "$ENV_FILE" ]]; then
    cat > "$ENV_FILE" <<EOF
TUBLR_HOST=0.0.0.0
TUBLR_PORT=8000
TUBLR_SECRET_KEY=$(head -c 32 /dev/urandom | base64 | tr -d '/+=')
# TUBLR_DOWNLOAD_DIR=$APP_DIR/downloads
# TUBLR_MAX_HEIGHT=1080
# TUBLR_MAX_JOBS=1
# TUBLR_JOB_TTL=1800
# DATABASE_URL=sqlite:///$APP_DIR/test.db
EOF
    chown root:"$RUN_GROUP" "$ENV_FILE"
    chmod 640 "$ENV_FILE"
    echo "Created $ENV_FILE"
fi

sed -e "s|@APP_DIR@|$APP_DIR|g" \
    -e "s|@USER@|$RUN_USER|g" \
    -e "s|@GROUP@|$RUN_GROUP|g" \
    "$APP_DIR/deploy/tublr.service" > "$UNIT_FILE"

systemctl daemon-reload
systemctl enable tublr.service
systemctl restart tublr.service
systemctl --no-pager status tublr.service

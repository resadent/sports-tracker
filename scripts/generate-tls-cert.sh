#!/usr/bin/env bash
# generate-tls-cert.sh — self-signed TLS certificate for the sports-tracker daemon.
#
# Writes key.pem + cert.pem into ~/.config/sports-tracker/certs/ (deliberately
# OUTSIDE the repo so it can never be committed). The certificate always covers
# the LAN IP and the public IP; pass your DDNS domain as the first argument to
# also cover it (the domain is what a browser will check first, so include it
# once you have one).
#
# Usage:
#   scripts/generate-tls-cert.sh                     # IPs only
#   scripts/generate-tls-cert.sh myname.duckdns.org  # include DDNS domain
#   PUBLIC_IP=1.2.3.4 scripts/generate-tls-cert.sh   # override auto-detected IPs
#
# Then restart the daemon so uvicorn reloads the files:
#   systemctl --user restart sports-tracker.service

set -euo pipefail

CERT_DIR="$HOME/.config/sports-tracker/certs"
DAYS=3650

# LAN IP: the interface holding the default route (enp1s0 here), not the
# docker bridges or the wg0 tunnel.
DEFAULT_IF="$(ip route show default | awk '{print $5; exit}')"
LAN_IP="$(ip -4 -o addr show dev "$DEFAULT_IF" scope global 2>/dev/null | awk '{print $4; exit}' | cut -d/ -f1)"

# Public IP: best effort, skipped silently when offline.
PUB_IP="${PUBLIC_IP:-$(curl -s --max-time 5 https://ifconfig.me 2>/dev/null || true)}"

DOMAIN="${1:-}"

SAN="DNS:localhost"
CN="sports-tracker"
if [[ -n "$DOMAIN" ]]; then
  SAN="DNS:$DOMAIN,$SAN"
  CN="$DOMAIN"
fi
[[ -n "$LAN_IP" ]] && SAN="IP:$LAN_IP,$SAN"
[[ -n "$PUB_IP" ]] && SAN="IP:$PUB_IP,$SAN"

mkdir -p "$CERT_DIR"
openssl req -x509 -newkey rsa:2048 -sha256 -days "$DAYS" -nodes \
  -keyout "$CERT_DIR/key.pem" -out "$CERT_DIR/cert.pem" \
  -subj "/CN=$CN" \
  -addext "subjectAltName=$SAN" \
  -addext "keyUsage=digitalSignature,keyEncipherment" \
  -addext "extendedKeyUsage=serverAuth"

chmod 600 "$CERT_DIR/key.pem"
chmod 644 "$CERT_DIR/cert.pem"

echo "Wrote $CERT_DIR/cert.pem and key.pem (valid $DAYS days, SAN: $SAN)"
echo "Restart the daemon: systemctl --user restart sports-tracker.service"

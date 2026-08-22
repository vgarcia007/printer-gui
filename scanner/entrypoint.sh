#!/bin/sh
set -eu

scanner_name="${SCANNER_NAME:-Brother}"
scanner_model="${SCANNER_MODEL:-MFC-L2710DW}"
scanner_ip="${SCANNER_IP:-192.0.2.30}"
run_uid="${APP_UID:-1000}"
run_gid="${APP_GID:-1000}"

brsaneconfig4 -r "$scanner_name" >/dev/null 2>&1 || true
brsaneconfig4 -a "name=$scanner_name" "model=$scanner_model" "ip=$scanner_ip"

install -d -o "$run_uid" -g "$run_gid" -m 0755 /state /scans
exec gosu "$run_uid:$run_gid" "$@"

#!/bin/sh
set -eu

run_uid="${APP_UID:-1000}"
run_gid="${APP_GID:-1000}"

install -d -o "$run_uid" -g "$run_gid" -m 0755 /data/jobs /data/labels /data/scans
exec gosu "$run_uid:$run_gid" "$@"

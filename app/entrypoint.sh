#!/bin/sh

set -eu

install -d -o printer-gui -g printer-gui -m 0755 /data/jobs
exec gosu printer-gui:printer-gui python3 /app/server.py "$@"

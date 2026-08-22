#!/bin/sh

set -eu

config_file=${PRINTER_CONFIG:-/config/printers.json}

if [ ! -f "$config_file" ]; then
    echo "Printer configuration not found: $config_file" >&2
    exit 1
fi

if [ ! -f /etc/cups/cupsd.conf ]; then
    cp -a /opt/cups-defaults/. /etc/cups/
fi

mkdir -p /var/spool/cups /var/log/cups /run/cups
chown -R root:lp /etc/cups /var/spool/cups /var/log/cups /run/cups

jq -e '
  .version == 1 and
  (.printers | type == "array" and length > 0) and
  (.defaultPrinter | type == "string") and
  (.defaultPrinter as $default | any(.printers[]; .name == $default)) and
  all(.printers[];
    (.name | type == "string" and length > 0) and
    (.label | type == "string" and length > 0) and
    (.uri | type == "string" and length > 0) and
    (.driver | type == "string" and length > 0) and
    ((.options // {}) | type == "object")
  )
' "$config_file" >/dev/null || {
    echo "Invalid printer configuration: $config_file" >&2
    exit 1
}

/usr/sbin/cupsd -f &
cups_pid=$!

stop_cups() {
    kill -TERM "$cups_pid" 2>/dev/null || true
}
trap stop_cups INT TERM

attempt=0
until lpstat -h localhost:631 -r >/dev/null 2>&1; do
    attempt=$((attempt + 1))
    if [ "$attempt" -ge 30 ]; then
        echo "CUPS did not become ready." >&2
        stop_cups
        wait "$cups_pid" || true
        exit 1
    fi
    sleep 1
done

# cupsd applies its restrictive RequestRoot mode during startup. Relax only the
# repository-backed directory afterwards so host-side Git and backup tools can
# traverse data/spool; CUPS still owns every spool file it creates.
chmod 0755 /var/spool/cups

configured_names=$(jq -r '.printers[].name' "$config_file")
lpstat -h localhost:631 -p 2>/dev/null | awk '{print $2}' | while IFS= read -r queue; do
    if ! printf '%s\n' "$configured_names" | grep -Fxq "$queue"; then
        lpadmin -h localhost:631 -x "$queue"
    fi
done

jq -c '.printers[]' "$config_file" | while IFS= read -r printer; do
    name=$(printf '%s' "$printer" | jq -r '.name')
    label=$(printf '%s' "$printer" | jq -r '.label')
    uri=$(printf '%s' "$printer" | jq -r '.uri')
    driver=$(printf '%s' "$printer" | jq -r '.driver')

    case "$name" in
        ''|*[!A-Za-z0-9_.-]*) echo "Invalid printer name: $name" >&2; exit 1 ;;
    esac

    # The web service is a remote CUPS client on the private Compose network.
    # Queues must therefore be shared by CUPS, while port 631 remains unpublished.
    lpadmin -h localhost:631 -p "$name" -E -v "$uri" -m "$driver" -D "$label" -o printer-is-shared=true

    printf '%s' "$printer" | jq -r '.options // {} | to_entries[] | [.key, (.value | tostring)] | @tsv' |
    while IFS='	' read -r option value; do
        [ -n "$option" ] || continue
        lpadmin -h localhost:631 -p "$name" -o "$option=$value"
    done
done

default_printer=$(jq -r '.defaultPrinter' "$config_file")
lpadmin -h localhost:631 -d "$default_printer"

echo "Configured printer queues:"
lpstat -h localhost:631 -p -d

wait "$cups_pid"

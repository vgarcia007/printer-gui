# Troubleshooting

## Basic checks

```bash
docker compose ps
docker compose logs --tail=100 cups
docker compose logs --tail=100 web
docker compose exec cups lpstat -p -d
```

Both containers should be healthy, both configured queues should appear, and `hp-color` should be the default destination.

## The page is unavailable

- Confirm that the containers are running with `docker compose ps`.
- Confirm that the selected host port is allowed by the Debian firewall.
- Open the Debian server address, not `localhost`, from another device.
- Check whether another service already uses port 8080; set `WEB_PORT` in `.env` if necessary.

## A printer is missing or unavailable

- Check its address in `config/printers.json`.
- Verify network reachability from the Debian host.
- Restart the stack after every configuration change.
- Inspect CUPS logs for an unknown driver model or rejected device URI.

For DHCP-managed printers, reserve their addresses in the router or use stable local DNS names.

## HP prints cryptic characters or blank pages

Stop the printer immediately and cancel its physical queue. Then verify:

```bash
docker compose exec cups lpstat -v hp-color
docker compose exec cups lpoptions -p hp-color
docker compose exec cups test -x /usr/lib/cups/filter/rastertospl
```

The queue must use the HP 17x PPD and the `rastertospl` filter must exist. Rebuild the CUPS image if the filter is missing:

```bash
docker compose build --no-cache cups
docker compose up -d
```

Do not change this queue to `raw`, `everywhere`, or a generic PostScript driver. The HP 178nw expects SPL-C output.

## A PDF remains in `data/jobs`

This is intentional after a failed CUPS submission. Fix the printer or queue, refresh the page, and use **Alle drucken**. A successfully submitted file is removed automatically.

## Resetting generated CUPS state

Normally the entrypoint reconciles queues without a reset. If generated state is corrupt, stop the stack, move `data/cups` and `data/spool` to a backup location, recreate the empty directories, and start again. This loses current CUPS jobs but not files in `data/jobs`.

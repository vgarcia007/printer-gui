# Printer configuration

Printers are declared in `config/printers.json`. Both containers read the same file: CUPS creates the queues, and the web service builds the dropdown from it.

## Schema

```json
{
  "version": 1,
  "defaultPrinter": "office-color",
  "printers": [
    {
      "name": "office-color",
      "label": "Office color printer",
      "uri": "socket://192.168.1.40",
      "driver": "everywhere",
      "options": {
        "PageSize": "A4"
      }
    }
  ]
}
```

- `name` is the CUPS queue name and may contain letters, numbers, `_`, `-`, and `.`.
- `label` is shown in the browser.
- `uri` is the CUPS device URI. Common forms are `ipp://HOST/ipp/print`, `ipps://...`, `socket://HOST`, and `lpd://HOST/queue`.
- `driver` is a CUPS model identifier as shown by `lpinfo -m` inside the CUPS container.
- `options` contains optional CUPS defaults.
- `defaultPrinter` must match one configured `name`; it controls both CUPS and the initial dropdown selection.

Restart after changing the file:

```bash
docker compose restart cups web
```

The CUPS entrypoint updates configured queues and removes stale queues that are no longer present in the JSON file.

## Included HP printer

The HP Color Laser MFP 178nw is configured with:

```text
socket://192.168.188.71
uld-hp/HP_Color_Laser_MFP_17x_Series.ppd
```

The image build downloads HP Unified Linux Driver 1.00.39.12, verifies the archive checksum, and installs only the SPL-C raster filter, its library, PPD, and color profile. This conversion step prevents PDFs or PostScript from reaching a printer that expects SPL-C.

The driver binaries are architecture-specific. The Dockerfile maps Docker's `amd64` platform to HP's `x86_64` files and `arm64` to `aarch64`.

## Included Brother printer

The Brother MFC-L2710DW uses the `brlaser` driver already provided by the base CUPS image:

```text
http://192.168.188.133
drv:///brlaser.drv/brl2710w.ppd
```

If the printer changes address, edit only the `uri` value and restart the services.

## Adding another printer

1. Determine its stable IP address or hostname and supported protocol.
2. Find an installed model with `docker compose exec cups lpinfo -m`, or use `everywhere` for a printer that properly supports driverless IPP Everywhere.
3. Add a unique object to `printers`.
4. Optionally change `defaultPrinter`.
5. Restart both services and inspect `docker compose logs cups`.

Do not assume that every network printer accepts PDF or driverless jobs. Use the manufacturer's Linux driver or a compatible CUPS driver when the device language requires it.
